"""
Telegram бот для расчета смет
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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
        
        # Создаем приложение
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        
        # Регистрируем обработчики
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Бот инициализирован")
    
    def check_auth(self, user_id: int) -> bool:
        """Проверка авторизации пользователя"""
        return user_id in settings.allowed_ids
    
    async def check_and_clarify_duplicates(self, update: Update, works: list, params: dict) -> list:
        """
        Проверяет наличие дубликатов работ с разными параметрами
        и запрашивает уточнение у пользователя если нужно
        
        Args:
            update: Telegram Update объект
            works: Список найденных работ
            params: Извлеченные параметры запроса
            
        Returns:
            Отфильтрованный список работ или None если нужно уточнение
        """
        # Группируем работы по названию
        works_by_title = {}
        for work in works:
            title = work['work_title']
            if title not in works_by_title:
                works_by_title[title] = []
            works_by_title[title].append(work)
        
        # Проверяем каждую группу на дубликаты
        for title, variants in works_by_title.items():
            if len(variants) <= 1:
                continue
            
            # Есть дубликаты - проверяем по каким параметрам они различаются
            categories = set()
            scales = set()
            territories = set()
            
            for work in variants:
                work_params = work.get('params', {})
                if work_params.get('category'):
                    categories.add(work_params['category'])
                if work_params.get('scale'):
                    scales.add(work_params['scale'])
                if work_params.get('territory'):
                    territories.add(work_params['territory'])
            
            # Если параметр не указан пользователем, но есть варианты - запрашиваем
            missing_params = []
            
            if len(categories) > 1 and not params.get('category'):
                missing_params.append('category')
            
            if len(scales) > 1 and not params.get('scale'):
                missing_params.append('scale')
            
            if len(territories) > 1 and not params.get('territory'):
                missing_params.append('territory')
            
            # Если есть недостающие параметры - запрашиваем
            if missing_params:
                message = f"❓ Найдено несколько вариантов работы **{title}**\n\n"
                message += "Уточните параметры:\n\n"
                
                for i, work in enumerate(variants, 1):
                    work_params = work.get('params', {})
                    price = work.get('price_field', 0)
                    unit = work.get('unit', '')
                    
                    param_str = []
                    if 'category' in missing_params and work_params.get('category'):
                        param_str.append(f"Категория {work_params['category']}")
                    if 'scale' in missing_params and work_params.get('scale'):
                        param_str.append(f"М {work_params['scale']}")
                    if 'territory' in missing_params and work_params.get('territory'):
                        param_str.append(work_params['territory'])
                    
                    message += f"{i}️⃣ {' • '.join(param_str)}\n"
                    message += f"   💰 {price:,.0f} руб/{unit}\n\n"
                
                message += "Напишите номер нужного варианта или уточните запрос с параметрами."
                
                await update.message.reply_text(message, parse_mode="Markdown")
                
                # Сохраняем варианты в контексте для следующего сообщения
                # TODO: реализовать обработку ответа пользователя
                
                return None  # Возвращаем None чтобы остановить обработку
        
        # Если дубликатов нет или все параметры указаны - возвращаем работы
        return works
    
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
            "• Топографическая съемка 92 га, масштаб 1:500\n"
            "• ЛЭП 110 кВ, 15 км, II категория\n"
            "• Трассирование автодороги 25 км\n\n"
            "Используйте /help для справки."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        await update.message.reply_text(
            "📖 **Справка по использованию бота**\n\n"
            "**Как пользоваться:**\n"
            "1. Напишите название работ\n"
            "2. Укажите объем и единицы измерения\n"
            "3. Добавьте параметры (масштаб, категорию и т.д.)\n\n"
            "**Примеры запросов:**\n"
            "• Топосъемка 50 га М 1:500 II категория\n"
            "• Нивелирование IV класс 10 пунктов\n"
            "• ЛЭП 35-110 кВ 8 км III категория\n\n"
            "**Команды:**\n"
            "/start - Начать работу\n"
            "/help - Эта справка",
            parse_mode="Markdown"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_id = update.effective_user.id
        
        if not self.check_auth(user_id):
            await update.message.reply_text("❌ У вас нет доступа к боту.")
            return
        
        user_message = update.message.text
        logger.info(f"Получено сообщение от {user_id}: {user_message}")
        
        try:
            # Показываем, что бот работает
            await update.message.reply_text("⏳ Обрабатываю запрос...")
            
            # 1. Извлекаем параметры через AI
            params = await self.ai.extract_parameters(user_message)
            
            if not params.get("work_type"):
                await update.message.reply_text(
                    "❌ Не удалось понять запрос.\n"
                    "Попробуйте указать тип работ и объем.\n\n"
                    "Например: Топосъемка 50 га М 1:500"
                )
                return
            
            # 2. Ищем работы в БД
            works = await self.db.search_works(
                query=params["work_type"],
                scale=params.get("scale"),
                category=params.get("category"),
                territory=params.get("territory")
            )
            
            if not works:
                await update.message.reply_text(
                    f"❌ Не найдено работ по запросу: {params['work_type']}\n"
                    "Попробуйте изменить формулировку."
                )
                return
            
            # 2.5. Проверяем дубликаты и запрашиваем уточнение если нужно
            works = await self.check_and_clarify_duplicates(update, works, params)
            if not works:
                return  # Пользователь должен уточнить
            
            # 3. Выбираем лучшую работу
            selected_work = await self.ai.select_best_work(user_message, works)
            
            if not selected_work:
                await update.message.reply_text("❌ Не удалось выбрать подходящую работу.")
                return
            
            # 4. Рассчитываем стоимость
            quantity = params.get("quantity", 1)
            
            calculation = await self.calculator.calculate(
                work=selected_work,
                quantity=quantity,
                coefficient_codes=None,  # TODO: определять из запроса
                addon_codes=["INTERNAL_TRANSPORT_T4_1_1"]  # Базовая надбавка
            )
            
            # 5. Форматируем ответ
            response = await self.ai.format_response(calculation)
            
            await update.message.reply_text(response, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке запроса.\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота...")
        self.app.run_polling()
