"""
Telegram бот для расчета смет
С поддержкой уточняющих вопросов и раздельного расчета полевых/камеральных работ
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from loguru import logger

from config import settings
from services.database import DatabaseService
from services.calculator import CostCalculator
from services.ai_agent import AIAgent


class SmetaBot:
    """Telegram бот для расчета смет"""
    
    def __init__(self):
        """Инициализация бота"""
        self.db = DatabaseService(settings.supabase_url, settings.supabase_service_role_key)
        self.calculator = CostCalculator(self.db)
        self.ai = AIAgent(settings.openrouter_api_key, settings.openrouter_model)
        
        # Хранилище контекста пользователей (для уточняющих вопросов)
        self.user_context = {}
        
        # Создаем приложение
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        
        # Регистрируем обработчики
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Бот инициализирован")
    
    def check_auth(self, user_id: int) -> bool:
        """Проверка авторизации пользователя"""
        return user_id in settings.allowed_ids
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        
        if not self.check_auth(user_id):
            await update.message.reply_text(
                "❌ У вас нет доступа к боту.\n"
                f"Ваш ID: {user_id}\n"
                "Обратитесь к администратору."
            )
            return
        
        await update.message.reply_text(
            "👋 Привет! Я бот для расчета стоимости геодезических работ.\n\n"
            "📝 Просто напишите мне, какие работы нужно рассчитать.\n\n"
            "Например:\n"
            "• Топографическая съемка 92 га, масштаб 1:500, промпредприятие\n"
            "• ЛЭП 110 кВ, 15 км, II категория\n"
            "• Трассирование автодороги 25 км\n\n"
            "Я задам уточняющие вопросы если нужно.\n"
            "Используйте /help для справки."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        await update.message.reply_text(
            "📖 *Справка по использованию бота*\n\n"
            "*Как пользоваться:*\n"
            "1. Напишите название работ\n"
            "2. Укажите объем и единицы измерения\n"
            "3. Добавьте параметры (масштаб, категорию и т.д.)\n\n"
            "*Примеры запросов:*\n"
            "• Топосъемка 50 га М 1:500 промпредприятие\n"
            "• Нивелирование IV класс 10 пунктов\n"
            "• ЛЭП 35-110 кВ 8 км III категория\n\n"
            "*Важные параметры для топосъемки:*\n"
            "• Тип территории: застроенная, незастроенная, промпредприятие\n"
            "• Съемка подземных коммуникаций: да/нет\n"
            "• Эскизы опор: да/нет\n\n"
            "*Команды:*\n"
            "/start - Начать работу\n"
            "/help - Эта справка",
            parse_mode="Markdown"
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline-кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if user_id not in self.user_context:
            await query.edit_message_text("❌ Сессия истекла. Начните новый запрос.")
            return
        
        ctx = self.user_context[user_id]
        
        # Парсим callback data: param_name:value
        if ':' in data:
            param_name, value = data.split(':', 1)
            
            # Преобразуем значение
            if value == 'True':
                value = True
            elif value == 'False':
                value = False
            
            # Сохраняем параметр
            ctx['params'][param_name] = value
            logger.info(f"Пользователь {user_id} выбрал {param_name}={value}")
            
            # Проверяем, есть ли еще недостающие параметры
            missing = self.ai.get_missing_parameters(ctx['params'], ctx['params'].get('work_type', ''))
            
            if missing:
                # Задаем следующий вопрос
                await self._ask_clarification(query.message, user_id, missing[0])
            else:
                # Все параметры получены - выполняем расчет
                await query.edit_message_text("⏳ Выполняю расчет...")
                await self._perform_calculation(query.message, user_id)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_id = update.effective_user.id
        
        if not self.check_auth(user_id):
            await update.message.reply_text("❌ У вас нет доступа к боту.")
            return
        
        user_message = update.message.text
        logger.info(f"Получено сообщение от {user_id}: {user_message}")
        
        try:
            # Проверяем, ожидаем ли ответ на уточняющий вопрос
            if user_id in self.user_context and self.user_context[user_id].get('waiting_for'):
                await self._handle_clarification_response(update, user_message)
                return
            
            # Показываем, что бот работает
            await update.message.reply_text("⏳ Анализирую запрос...")
            
            # 1. Извлекаем параметры через AI
            params = await self.ai.extract_parameters(user_message)
            
            if not params.get("work_type"):
                await update.message.reply_text(
                    "❌ Не удалось понять запрос.\n"
                    "Попробуйте указать тип работ и объем.\n\n"
                    "Например: Топосъемка 50 га М 1:500 промпредприятие"
                )
                return
            
            # 2. Ищем работы в БД
            works = await self.db.search_works(
                query=params["work_type"],
                scale=params.get("scale"),
                category=params.get("category"),
                territory=params.get("territory_type")
            )
            
            if not works:
                await update.message.reply_text(
                    f"❌ Не найдено работ по запросу: {params['work_type']}\n"
                    "Попробуйте изменить формулировку."
                )
                return
            
            # 3. Выбираем лучшую работу
            selected_work = await self.ai.select_best_work(user_message, works)
            
            if not selected_work:
                await update.message.reply_text("❌ Не удалось выбрать подходящую работу.")
                return
            
            # 4. Сохраняем контекст
            self.user_context[user_id] = {
                'params': params,
                'work': selected_work,
                'original_message': user_message,
                'waiting_for': None
            }
            
            # 5. Проверяем, нужны ли уточнения
            missing = self.ai.get_missing_parameters(params, params.get('work_type', ''))
            
            if missing:
                # Задаем уточняющий вопрос
                await self._ask_clarification(update.message, user_id, missing[0])
            else:
                # Все параметры есть - выполняем расчет
                await self._perform_calculation(update.message, user_id)
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке запроса.\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
    
    async def _ask_clarification(self, message, user_id: int, param_info: dict):
        """Задает уточняющий вопрос с inline-кнопками"""
        ctx = self.user_context[user_id]
        ctx['waiting_for'] = param_info['param']
        
        # Создаем inline-кнопки
        keyboard = []
        for num, label, value in param_info['options']:
            callback_data = f"{param_info['param']}:{value}"
            keyboard.append([InlineKeyboardButton(f"{num}️⃣ {label}", callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Формируем текст вопроса
        work = ctx['work']
        text = f"📋 *Работа:* {work['work_title']}\n"
        text += f"📏 *Объем:* {ctx['params'].get('quantity', '?')} {work.get('unit', '')}\n\n"
        text += f"❓ *{param_info['question']}*"
        
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    async def _handle_clarification_response(self, update: Update, user_message: str):
        """Обрабатывает текстовый ответ на уточняющий вопрос"""
        user_id = update.effective_user.id
        ctx = self.user_context[user_id]
        param_name = ctx['waiting_for']
        
        # Пытаемся распознать ответ
        value = None
        msg_lower = user_message.lower().strip()
        
        if param_name == 'territory_type':
            if any(kw in msg_lower for kw in ['1', 'застро', 'город']):
                value = 'застроенная'
            elif any(kw in msg_lower for kw in ['2', 'незастро', 'поле']):
                value = 'незастроенная'
            elif any(kw in msg_lower for kw in ['3', 'пром', 'завод', 'предприят']):
                value = 'промпредприятие'
        
        elif param_name == 'has_underground_comms':
            if any(kw in msg_lower for kw in ['1', 'да', 'нужн', 'с подзем']):
                value = True
            elif any(kw in msg_lower for kw in ['2', 'нет', 'без']):
                value = False
        
        elif param_name == 'work_stage':
            if any(kw in msg_lower for kw in ['1', 'обе', 'полн', 'все']):
                value = 'обе'
            elif any(kw in msg_lower for kw in ['2', 'полев']):
                value = 'полевые'
            elif any(kw in msg_lower for kw in ['3', 'камер']):
                value = 'камеральные'
        
        if value is None:
            await update.message.reply_text(
                "❌ Не понял ответ. Пожалуйста, выберите один из вариантов кнопками выше\n"
                "или напишите номер варианта (1, 2, 3...)"
            )
            return
        
        # Сохраняем параметр
        ctx['params'][param_name] = value
        ctx['waiting_for'] = None
        logger.info(f"Пользователь {user_id} ответил {param_name}={value}")
        
        # Проверяем, есть ли еще недостающие параметры
        missing = self.ai.get_missing_parameters(ctx['params'], ctx['params'].get('work_type', ''))
        
        if missing:
            # Задаем следующий вопрос
            await self._ask_clarification(update.message, user_id, missing[0])
        else:
            # Все параметры получены - выполняем расчет
            await update.message.reply_text("⏳ Выполняю расчет...")
            await self._perform_calculation(update.message, user_id)
    
    async def _perform_calculation(self, message, user_id: int):
        """Выполняет расчет и отправляет результат"""
        ctx = self.user_context[user_id]
        params = ctx['params']
        work = ctx['work']
        
        try:
            # Определяем объем
            quantity = params.get('quantity', 1)
            if quantity is None:
                quantity = 1
            
            # Определяем этап работ
            work_stage = params.get('work_stage', 'обе')
            
            # Проверяем, есть ли нужные цены в выбранной работе
            # Если нет - ищем дополнительную работу с нужной ценой
            if work_stage in ['полевые', 'обе'] and not work.get('price_field'):
                # Ищем работу с полевой ценой
                logger.warning(f"Работа {work.get('work_title')} не имеет полевой цены, ищем...")
                works = await self.db.search_works(
                    query=params.get('work_type', ''),
                    scale=params.get('scale'),
                    category=params.get('category'),
                    territory=params.get('territory_type')
                )
                for w in works:
                    if w.get('price_field'):
                        work['price_field'] = w['price_field']
                        logger.info(f"Найдена полевая цена: {w['price_field']}")
                        break
            
            if work_stage in ['камеральные', 'обе'] and not work.get('price_office'):
                # Ищем работу с камеральной ценой
                logger.warning(f"Работа {work.get('work_title')} не имеет камеральной цены, ищем...")
                works = await self.db.search_works(
                    query=params.get('work_type', ''),
                    scale=params.get('scale'),
                    category=params.get('category'),
                    territory=params.get('territory_type')
                )
                for w in works:
                    if w.get('price_office'):
                        work['price_office'] = w['price_office']
                        logger.info(f"Найдена камеральная цена: {w['price_office']}")
                        break
            
            # Выполняем расчет
            calculation = await self.calculator.calculate_full(
                work=work,
                quantity=quantity,
                params=params,
                work_stage=work_stage
            )
            
            # Форматируем ответ
            response = await self.ai.format_response(calculation)
            
            await message.reply_text(response, parse_mode="Markdown")
            
            # Очищаем контекст
            del self.user_context[user_id]
            
        except Exception as e:
            logger.error(f"Ошибка расчета: {e}")
            await message.reply_text(
                "❌ Произошла ошибка при расчете.\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота...")
        self.app.run_polling()
