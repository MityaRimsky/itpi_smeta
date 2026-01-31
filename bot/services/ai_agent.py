"""
AI-агент для обработки запросов пользователей через OpenRouter
"""

from typing import Dict, List, Optional
from openai import AsyncOpenAI
from loguru import logger


class AIAgent:
    """AI-агент на базе OpenRouter"""
    
    def __init__(self, api_key: str, model: str):
        """
        Инициализация AI-агента
        
        Args:
            api_key: API ключ OpenRouter
            model: Модель для использования
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model
        logger.info(f"AI-агент инициализирован: {model}")
    
    async def extract_parameters(self, user_message: str) -> Dict:
        """
        Извлекает параметры работ из сообщения пользователя
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            Словарь с параметрами: work_type, quantity, unit, scale, category, territory
        """
        prompt = f"""Извлеки параметры из запроса пользователя о геодезических работах.

Запрос: "{user_message}"

Верни JSON с полями:
- work_type: тип работ (топографическая съемка, нивелирование, трассирование и т.д.)
- quantity: объем работ (число)
- unit: единица измерения (га, км, пункт, м)
- scale: масштаб (1:500, 1:1000, 1:2000 и т.д.) или null
- category: категория сложности (I, II, III, IV) или null
- territory: тип территории (застроенная, незастроенная, промпредприятие) или null

Если параметр не указан, верни null."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Извлечены параметры: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка извлечения параметров: {e}")
            return {}
    
    async def select_best_work(self, user_request: str, found_works: List[Dict]) -> Optional[Dict]:
        """
        Выбирает наиболее подходящую работу из найденных
        
        Args:
            user_request: Запрос пользователя
            found_works: Список найденных работ
            
        Returns:
            Выбранная работа или None
        """
        if not found_works:
            return None
        
        if len(found_works) == 1:
            return found_works[0]
        
        # Формируем список для AI
        works_list = "\n".join([
            f"{i+1}. {w['work_title']} ({w['unit']}, {w['price_field']}+{w['price_office']} руб)"
            for i, w in enumerate(found_works)
        ])
        
        prompt = f"""Выбери наиболее подходящую работу для запроса пользователя.

Запрос: "{user_request}"

Доступные работы:
{works_list}

Верни JSON с полем "index" (номер выбранной работы, начиная с 1)."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            index = result.get("index", 1) - 1
            
            if 0 <= index < len(found_works):
                return found_works[index]
            return found_works[0]
            
        except Exception as e:
            logger.error(f"Ошибка выбора работы: {e}")
            return found_works[0]
    
    async def format_response(self, calculation: Dict) -> str:
        """
        Форматирует результат расчета в понятный текст
        
        Args:
            calculation: Результат расчета
            
        Returns:
            Отформатированный текст
        """
        prompt = f"""Сформируй понятный ответ пользователю о расчете стоимости работ.

Данные расчета:
{calculation}

Сделай ответ структурированным, включи:
- Название работы
- Объем и единицы
- Базовую стоимость
- Примененные коэффициенты (если есть)
- Надбавки (если есть)
- Итоговую стоимость
- Обоснование

Используй форматирование Telegram (жирный текст, списки)."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка форматирования ответа: {e}")
            # Fallback форматирование
            return self._simple_format(calculation)
    
    def _simple_format(self, calc: Dict) -> str:
        """Простое форматирование без AI"""
        text = f"""📊 **Расчет стоимости работ**

**Работа:** {calc['work_title']}
**Объем:** {calc['quantity']} {calc['unit']}

💰 **Стоимость:**
• Полевые работы: {calc['base_field']:,.2f} руб
• Камеральные работы: {calc['base_office']:,.2f} руб
"""
        
        if calc.get('coefficients_applied'):
            text += "\n🔢 **Коэффициенты:**\n"
            for coeff in calc['coefficients_applied']:
                text += f"• {coeff['name']}: {coeff['value']}\n"
        
        if calc.get('addons_applied'):
            text += "\n➕ **Надбавки:**\n"
            for addon in calc['addons_applied']:
                text += f"• {addon['name']}: {addon['amount']:,.2f} руб\n"
        
        text += f"\n✅ **ИТОГО: {calc['final_total']:,.2f} руб**\n"
        text += f"\n📋 **Обоснование:** {calc['justification']}"
        
        return text
