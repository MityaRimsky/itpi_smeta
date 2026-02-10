"""
AI-агент для обработки запросов пользователей через OpenRouter
Извлекает параметры для расчета коэффициентов из БД
"""

from typing import Dict, List, Optional, Tuple
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError, RateLimitError
from loguru import logger
import asyncio
import json
import re
import httpx


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
            base_url="https://openrouter.ai/api/v1",
            timeout=45.0,
            max_retries=1,
        )
        self.model = model
        logger.info(f"AI-агент инициализирован: {model}")

    async def _chat_json(self, prompt: str, op_name: str) -> Dict:
        """Устойчивый вызов OpenRouter с ретраями на сетевые/временные сбои."""
        last_error = None
        retry_delays = [1, 2, 4]

        for attempt, delay in enumerate(retry_delays, start=1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    timeout=45.0,
                )
                return json.loads(response.choices[0].message.content)
            except (
                APITimeoutError,
                APIConnectionError,
                RateLimitError,
                httpx.TimeoutException,
                httpx.NetworkError,
                TimeoutError,
            ) as e:
                last_error = e
                logger.warning(
                    f"{op_name}: временный сбой AI ({attempt}/{len(retry_delays)}): {e}. "
                    f"Повтор через {delay} сек."
                )
                await asyncio.sleep(delay)
            except Exception as e:
                last_error = e
                break

        raise last_error if last_error else RuntimeError(f"{op_name}: неизвестная ошибка AI")
    
    async def extract_parameters(self, user_message: str) -> Dict:
        """
        Извлекает параметры работ из сообщения пользователя
        Включает ВСЕ параметры для коэффициентов K1, K2, K3
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            Словарь с параметрами
        """
        prompt = f"""Извлеки параметры из запроса пользователя о геодезических/топографических работах.

Запрос: "{user_message}"

Верни JSON с полями:

=== ОСНОВНЫЕ ПАРАМЕТРЫ ===
- work_type: тип работ - используй СТАНДАРТНЫЕ термины:
  * "топографическая съемка" - для топопланов, инженерно-топографических планов
  * "нивелирование" - для высотных работ
  * "трассирование" - для изысканий трасс
  * "изыскания трасс" - для ж/д, автодорог, ЛЭП
  * "бурение" - для буровых работ
  * "опорная сеть" - для геодезических сетей (плановая, высотная)
  * "привязка скважин" - для планово-высотной привязки геологических скважин
  * "привязка выработок" - для привязки горных выработок
  * "выдача координат" - для выдачи координат и высот исходных пунктов
- quantity: объем работ (число) или null
- unit: единица измерения (га, км, пункт, м) или null
- scale: масштаб (1:500, 1:1000, 1:2000) или null
- height_section: сечение рельефа (например 0.5, 1.0, 2.0) или null
- work_stage: этап работ ("полевые", "камеральные", "обе") или null

=== ПАРАМЕТРЫ ДЛЯ K1 (примечания к таблицам) ===
- territory_type: тип территории - "застроенная", "незастроенная", "промпредприятие" или null
- has_underground_comms: съемка подземных коммуникаций (true/false/null)
- has_detailed_wells_sketches: детальные эскизы колодцев и опор (true/false/null)
- measurement_drawings: обмерные чертежи зданий и сооружений (true/false/null)
- special_object: крупные ж/д станции/аэропорты и др. спецобъекты (string/null)
- update_mode: обновление существующего плана (true/false/null)
- category: категория СЛОЖНОСТИ работ (I, II, III, IV) или null
  * ВАЖНО: НЕ ПУТАТЬ с категорией дороги!
  * "II кат.сложности", "2 категория сложности", "II категория" (в скобках) → category: "II"
  * "III-IV категории дороги" → это road_category, НЕ category!
- use_satellite: применение спутниковых систем/GPS/GNSS (true/false/null) - K1=1.3 ТОЛЬКО для ПЛАНОВЫХ опорных сетей!
  * ВАЖНО: для ВЫСОТНЫХ сетей (нивелирование, IV класс) use_satellite = false!
  * "плановая опорная сеть спутниковым методом" → use_satellite: true
  * "высотная опорная сеть IV класс" → use_satellite: false (это нивелирование!)

=== ПАРАМЕТРЫ ДЛЯ K2 (п.15 ОУ) ===
- use_computer: компьютерные технологии для камеральных (true/false/null)
- dual_format: два носителя - магнитный + бумажный (true/false/null)
- color_plan: план в цвете (true/false/null)
- intermediate_materials: выдача промежуточных материалов (true/false/null)
- classified_materials: материалы ограниченного пользования (true/false/null)
- artificial_lighting: искусственное освещение (true/false/null)

=== ПАРАМЕТРЫ ДЛЯ K3 (п.8, п.14 ОУ - условия производства) ===
- altitude: высота над уровнем моря в метрах (для горных районов) или null
- unfavorable_months: месяцы неблагоприятного периода (4-5.5, 6-7.5, 8-9.5) или null
- salary_coeff: районный коэффициент к зарплате (1.15, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 1.80, 2.00) или null
- region_type: тип региона ("far_north", "far_north_equivalent", "south_regions") или null
- special_regime: спецрежим территории - погранзона, полигон, аэродром (true/false/null)
- night_time: работы в ночное время (true/false/null)
- no_field_allowance: без полевого довольствия (true/false/null)

=== ПАРАМЕТРЫ ДЛЯ НАДБАВОК ===
- distance_to_base: расстояние от базы до объекта в км (для внутреннего транспорта) или null
- external_distance: расстояние внешнего транспорта в км или null
- expedition_duration: длительность экспедиции в месяцах или null
- include_org_liq: включать организацию/ликвидацию полевых работ (true/false/null)
- apply_conditions_as_addons: применять сезонность/районность/горные как отдельные надбавки (true/false/null)

ВАЖНО: 
1. Для work_type используй СТАНДАРТНЫЕ термины!
2. "инженерно-топографический план" = "топографическая съемка"
3. Если параметр явно не указан - верни null
4. Если параметр явно не указан - верни null (без автоматических true)
5. Не придумывай параметры, которых нет в тексте.
6. Для слов «эстакад», «колодцев», «подробное обследование» — has_detailed_wells_sketches=true.
5. ВНИМАТЕЛЬНО извлекай quantity! "пункт 15" = quantity: 15, "15 пунктов" = quantity: 15
6. "км 2,00" = quantity: 2.0, unit: "км"

Примеры:
- "топоплан 92 га промпредприятие" → quantity: 92, unit: "га", territory_type: "промпредприятие"
- "сечение рельефа 2,0" → height_section: 2.0
- "съемка с подземными коммуникациями" → has_underground_comms: true
- "детальное обследование эстакад/колодцев" → has_detailed_wells_sketches: true
- "работы в Магадане" → region_type: "far_north" (Магадан - Крайний Север)
- "горный район 2500м" → altitude: 2500
- "неблагоприятный период 6 месяцев" → unfavorable_months: 6
- "пункт 15 категория 2" → quantity: 15, unit: "пункт", category: "II"
- "1 разряд пункт 15" → quantity: 15, unit: "пункт" (разряд - это характеристика работы, не количество!)
- "км 2,00" → quantity: 2.0, unit: "км"
- "2 км" → quantity: 2, unit: "км"
- "15 пунктов" → quantity: 15, unit: "пункт"
- "IV класс пункт 15" → quantity: 15, unit: "пункт" (класс - характеристика работы)
- "с применением спутниковых систем" → use_satellite: true (K1=1.3 для полевых!)
- "спутниковым методом" → use_satellite: true
- "GPS/GNSS" → use_satellite: true
- "железных дорог III-IV категории (II кат.сложности)" → category: "II" (НЕ "III"! "III-IV" - это категория дороги)
- "автодорог I-II категории, III категория сложности" → category: "III" (категория сложности в конце)
- "ЛЭП 110 кВ, II категория" → category: "II" (категория сложности)"""

        try:
            result = await self._chat_json(prompt, "extract_parameters")
            
            # Если AI вернул вложенные словари - разворачиваем в плоский
            flat_result = self._flatten_params(result)
            flat_result = self._sanitize_params(user_message, flat_result)
            
            logger.info(f"Извлечены параметры: {flat_result}")
            return flat_result
            
        except Exception as e:
            logger.error(f"Ошибка извлечения параметров: {e}")
            return {}
    
    def _flatten_params(self, params: Dict) -> Dict:
        """Разворачивает вложенные словари в плоский"""
        flat = {}
        
        for key, value in params.items():
            if isinstance(value, dict):
                # Рекурсивно разворачиваем вложенные словари
                for k, v in value.items():
                    flat[k] = v
            else:
                flat[key] = value
        
        return flat

    def _sanitize_params(self, user_message: str, params: Dict) -> Dict:
        """Обнуляет булевы флаги, если в тексте нет явных триггеров."""
        text = user_message.lower()

        def has_any(keywords: List[str]) -> bool:
            return any(k in text for k in keywords)

        rules = {
            "use_computer": ["компьютер", "компьютерн", "cad", "гис", "gis", "цифров"],
            "dual_format": ["два носителя", "двух видах", "магнитн", "бумажн", "цифровой и бумажный"],
            "color_plan": ["в цвете", "цветной", "цвета", "цвет"],
            "intermediate_materials": ["промежуточ"],
            "classified_materials": ["ограниченного", "секрет", "дсп", "служебн"],
            "artificial_lighting": ["искусственн", "освещ"],
            "special_regime": ["погран", "полигон", "аэродром", "спецрежим", "режим"],
            "night_time": ["ноч", "ночное", "ночью"],
            "no_field_allowance": ["без полевого", "без командировочных", "без полевого довольствия"],
            "office_in_field_camp": ["экспедицион", "в экспедиционных условиях"],
            "use_satellite": ["спутник", "gps", "gnss", "глонасс"],
            "no_center": ["без закладки центра", "без закладки центров"],
        }

        sanitized = dict(params)
        if "height_section" in sanitized and sanitized["height_section"] is not None:
            try:
                sanitized["height_section"] = float(str(sanitized["height_section"]).replace(",", "."))
            except Exception:
                pass
        if not sanitized.get("work_stage"):
            sanitized["work_stage"] = "обе"
        if sanitized.get("has_detailed_wells_sketches") is None and any(k in text for k in ["эстакад", "колодц"]):
            sanitized["has_detailed_wells_sketches"] = True
        if sanitized.get("no_center") is None and any(k in text for k in ["без закладки центра", "без закладки центров"]):
            sanitized["no_center"] = True

        # Проверка полноты планов (табл. 75, прим. 3) — отдельная работа из БД
        if "проверки полноты планов" in text:
            sanitized["work_type"] = "проверка полноты планов"
            sanitized["unit"] = "организация"
            sanitized["work_stage"] = "камеральные"
            m = re.search(r"(\\d+[\\.,]?\\d*)\\s*(служб|организац)", text)
            if m:
                try:
                    sanitized["quantity"] = float(m.group(1).replace(",", "."))
                except Exception:
                    pass

        # Продольные профили — единица измерения "дм профиля"
        if "профил" in text and "дм" in text:
            if not sanitized.get("work_type") or "профил" not in sanitized.get("work_type", ""):
                sanitized["work_type"] = "продольных профилей трассы"
            if not sanitized.get("unit") or sanitized.get("unit") in ["м", "км"]:
                sanitized["unit"] = "дм профиля"
            if "св.20 до 40" in text or "св. 20 до 40" in text or "св 20 до 40" in text:
                sanitized["column"] = "св. 20 до 40"
            elif "до 20" in text:
                sanitized["column"] = "до 20"
            elif "свыше 40" in text or "св. 40" in text:
                sanitized["column"] = "свыше 40"
            # Ищем количество дм профиля (берем последнее значение, отличное от "1 дм")
            matches = []
            for m in re.finditer(r"(\d+(?:[\.,]\d+)?)\s*дм", text):
                matches.append(m.group(1))
            for m in re.finditer(r"дм\s*(\d+(?:[\.,]\d+)?)", text):
                matches.append(m.group(1))
            if matches:
                values = []
                for raw in matches:
                    try:
                        values.append(float(raw.replace(",", ".")))
                    except Exception:
                        pass
                if values:
                    preferred = [v for v in values if v > 1.5]
                    chosen = preferred[-1] if preferred else values[-1]
                    sanitized["quantity"] = chosen
        for key, keywords in rules.items():
            if sanitized.get(key) is True and not has_any(keywords):
                sanitized[key] = None

        return sanitized
    
    def get_missing_parameters(self, params: Dict, work_type: str) -> List[Dict]:
        """
        Определяет какие параметры нужно уточнить у пользователя
        Спрашивает параметры необходимые для коэффициентов из БД
        
        Args:
            params: Извлеченные параметры
            work_type: Тип работ
            
        Returns:
            Список недостающих параметров с вариантами ответов
        """
        missing = []

        # Специальные работы без уточнений
        if work_type and "проверка полноты планов" in work_type.lower():
            return missing
        
        # Для топографической съемки нужны дополнительные параметры
        if any(kw in work_type.lower() for kw in ['топо', 'съемка', 'план']):
            
            # === K1 ПАРАМЕТРЫ ===
            
            # Тип территории - критически важен для коэффициента К1
            if not params.get('territory_type'):
                missing.append({
                    'param': 'territory_type',
                    'question': '🏗 Укажите тип территории:',
                    'options': [
                        ('1', 'Застроенная территория', 'застроенная'),
                        ('2', 'Незастроенная территория', 'незастроенная'),
                        ('3', 'Территория промпредприятия', 'промпредприятие')
                    ],
                    'required': True,
                    'affects': 'K1 (прим. 4 к табл. 9)'
                })
            
            # Съемка подземных коммуникаций - коэффициент К1
            if params.get('has_underground_comms') is None:
                missing.append({
                    'param': 'has_underground_comms',
                    'question': '🔌 Нужна съемка подземных коммуникаций?',
                    'options': [
                        ('1', 'Да, со съемкой подземных коммуникаций', True),
                        ('2', 'Нет, без подземных коммуникаций', False)
                    ],
                    'required': True,
                    'affects': 'K1 (прим. 4 к табл. 9)'
                })
            
            # Детальные эскизы колодцев и опор
            if params.get('has_detailed_wells_sketches') is None and params.get('has_underground_comms'):
                missing.append({
                    'param': 'has_detailed_wells_sketches',
                    'question': '📐 Нужны детальные эскизы колодцев и опор?',
                    'options': [
                        ('1', 'Да, с эскизами и разрезами', True),
                        ('2', 'Нет, без детальных эскизов', False)
                    ],
                    'required': False,
                    'affects': 'K1 (прим. 5 к табл. 9)'
                })
            
            # Этап работ - полевые/камеральные
            if not params.get('work_stage'):
                missing.append({
                    'param': 'work_stage',
                    'question': '📋 Какие работы рассчитать?',
                    'options': [
                        ('1', 'Полевые и камеральные (полный цикл)', 'обе'),
                        ('2', 'Только полевые работы', 'полевые'),
                        ('3', 'Только камеральные работы', 'камеральные')
                    ],
                    'required': True,
                    'affects': 'Расчет'
                })

            # Внутренний транспорт (только если есть полевые работы)
            work_stage = params.get('work_stage')
            if work_stage in ['полевые', 'обе'] and params.get('distance_to_base_km') is None and params.get('distance_to_base') is None:
                missing.append({
                    'param': 'distance_to_base_km',
                    'question': '🚚 Внутренний транспорт: расстояние от базы до участка (км)?',
                    'options': [
                        ('1', 'Не применять', None),
                        ('2', 'До 5 км', 5),
                        ('3', '5–10 км', 7.5),
                        ('4', '10–15 км', 12.5),
                        ('5', '15–20 км', 17.5)
                    ],
                    'required': False,
                    'affects': 'Надбавка внутреннего транспорта (табл. 4)'
                })

            # Внешний транспорт (только если есть полевые работы)
            if work_stage in ['полевые', 'обе'] and params.get('external_distance_km') is None and params.get('external_distance') is None:
                missing.append({
                    'param': 'external_distance_km',
                    'question': '✈️ Внешний транспорт: расстояние проезда в одну сторону (км)?',
                    'options': [
                        ('1', 'Не применять', None),
                        ('2', '100–300 км', 200),
                        ('3', '1000–2000 км', 1500),
                        ('4', 'Свыше 2000 км', 2500),
                        ('5', 'Свыше 4000 км', 4500)
                    ],
                    'required': False,
                    'affects': 'Надбавка внешнего транспорта (табл. 5)'
                })
            if work_stage in ['полевые', 'обе'] and params.get('expedition_duration_months') is None and params.get('expedition_duration') is None:
                missing.append({
                    'param': 'expedition_duration_months',
                    'question': '🧭 Внешний транспорт: длительность экспедиции (мес.)?',
                    'options': [
                        ('1', 'Не применять', None),
                        ('2', 'До 1 мес', 1),
                        ('3', 'До 2 мес', 2),
                        ('4', 'До 3 мес', 3),
                        ('5', 'Свыше 3 мес', 4)
                    ],
                    'required': False,
                    'affects': 'Надбавка внешнего транспорта (табл. 5)'
                })

            # K3 и надбавки пользователь задаёт отдельно — не спрашиваем автоматически.
        
        return missing
    
    def get_optional_parameters(self, params: Dict) -> List[Dict]:
        """
        Возвращает список опциональных параметров которые можно уточнить
        
        Args:
            params: Текущие параметры
            
        Returns:
            Список опциональных параметров
        """
        optional = []
        
        # Горные районы
        if params.get('altitude') is None:
            optional.append({
                'param': 'altitude',
                'question': '⛰️ Работы в горном районе?',
                'options': [
                    ('1', 'Нет, равнинная местность', None),
                    ('2', '1500-1700 м над уровнем моря (+10%)', 1600),
                    ('3', '1700-2000 м над уровнем моря (+15%)', 1850),
                    ('4', '2000-3000 м над уровнем моря (+20%)', 2500),
                    ('5', 'Свыше 3000 м над уровнем моря (+25%)', 3500)
                ],
                'affects': 'K3 (табл. 1, п.8а)'
            })
        
        # Спецрежим территории
        if params.get('special_regime') is None:
            optional.append({
                'param': 'special_regime',
                'question': '🔒 Территория со специальным режимом?',
                'options': [
                    ('1', 'Нет', False),
                    ('2', 'Да (погранзона, полигон, аэродром, стройплощадка)', True)
                ],
                'affects': 'K3 (п.8в) +25%'
            })
        
        # Промежуточные материалы
        if params.get('intermediate_materials') is None:
            optional.append({
                'param': 'intermediate_materials',
                'question': '📄 Нужна выдача промежуточных материалов?',
                'options': [
                    ('1', 'Нет', False),
                    ('2', 'Да (+10%)', True)
                ],
                'affects': 'Надбавка (п.15а)'
            })
        
        # Внешний транспорт
        if params.get('external_distance') is None:
            optional.append({
                'param': 'external_distance',
                'question': '✈️ Расстояние внешнего транспорта (от города до базы)?',
                'options': [
                    ('1', 'Не требуется (местные работы)', None),
                    ('2', '25-100 км', 75),
                    ('3', '100-300 км', 200),
                    ('4', '1000-2000 км', 1500)
                ],
                'affects': 'Внешний транспорт (табл. 5, п.10)'
            })
        
        return optional
    
    def determine_coefficients(self, params: Dict, work_stage: str = 'field') -> Tuple[List[str], Dict]:
        """
        Определяет какие коэффициенты применить на основе параметров
        УСТАРЕВШИЙ МЕТОД - коэффициенты теперь берутся из БД
        
        Args:
            params: Параметры работ
            work_stage: Этап работ ('field' или 'office')
            
        Returns:
            Tuple[список кодов коэффициентов, словарь с описанием]
        """
        logger.warning("determine_coefficients() устарел - коэффициенты берутся из БД")
        return [], {}
    
    def determine_addons(self, params: Dict, base_cost: float) -> List[str]:
        """
        Определяет какие надбавки применить
        УСТАРЕВШИЙ МЕТОД - надбавки теперь берутся из БД
        
        Args:
            params: Параметры работ
            base_cost: Базовая стоимость
            
        Returns:
            Список кодов надбавок
        """
        logger.warning("determine_addons() устарел - надбавки берутся из БД")
        return []
    
    async def select_best_work(self, user_request: str, found_works: List[Dict], params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Выбирает наиболее подходящую работу из найденных
        
        Args:
            user_request: Запрос пользователя
            found_works: Список найденных работ
            params: Извлеченные параметры (для фильтрации по категории)
            
        Returns:
            Выбранная работа или None
        """
        if not found_works:
            return None
        
        if len(found_works) == 1:
            return found_works[0]
        
        # Если указана категория сложности - фильтруем по ней
        if params and params.get('category'):
            requested_category = params['category']
            matching_works = [w for w in found_works if w.get('params', {}).get('category') == requested_category]
            if matching_works:
                if len(matching_works) == 1:
                    return matching_works[0]
                found_works = matching_works  # Продолжаем выбор среди отфильтрованных

        # Формируем список для AI с параметрами
        works_list = []
        for i, w in enumerate(found_works):
            params = w.get('params', {})
            params_str = ""
            if params.get('road_category'):
                params_str += f", категория дороги: {params['road_category']}"
            if params.get('category'):
                params_str += f", кат.сложности: {params['category']}"
            if params.get('voltage'):
                params_str += f", напряжение: {params['voltage']} кВ"
            
            works_list.append(
                f"{i+1}. {w['work_title']} (§{w.get('section', '?')}{params_str}, полевые: {w.get('price_field', 0)}, камеральные: {w.get('price_office', 0)} руб)"
            )
        
        works_str = "\n".join(works_list)
        
        prompt = f"""Выбери наиболее подходящую работу для запроса пользователя.

Запрос: "{user_request}"

Доступные работы:
{works_str}

ВАЖНО:
- "III-IV категории" дороги = road_category "III-IV" (§2)
- "I-II категории" дороги = road_category "I-II" (§1)
- "V категории" дороги = road_category "V" (§3)
- Категория сложности (I, II, III) - это отдельный параметр!

Верни JSON с полем "index" (номер выбранной работы, начиная с 1)."""

        try:
            result = await self._chat_json(prompt, "select_best_work")
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
        # Используем простое форматирование для надежности
        return self._simple_format(calculation)
    
    def _simple_format(self, calc: Dict) -> str:
        """Простое форматирование без AI"""
        work = calc.get('work', {})
        params = work.get('params', {})
        calc_params = calc.get('params', {})
        
        text = f"""📊 *Расчет стоимости работ*

*Работа:* {work.get('work_title', calc.get('work_title', 'Не указано'))}
"""
        
        # Выводим параметры работы (категория сложности, категория дороги и т.д.)
        category = params.get('category') or calc_params.get('category')
        if category:
            text += f"*Категория сложности:* {category}\n"
        if params.get('road_category'):
            text += f"*Категория дороги:* {params['road_category']}\n"
        if params.get('voltage'):
            text += f"*Напряжение:* {params['voltage']} кВ\n"
        if params.get('scale'):
            text += f"*Масштаб:* {params['scale']}\n"
        if params.get('distance'):
            text += f"*Расстояние:* {params['distance']}\n"
        
        quantity = calc.get('quantity', 0)
        try:
            quantity_val = int(quantity) if float(quantity).is_integer() else quantity
        except Exception:
            quantity_val = quantity

        unit_raw = work.get('unit', calc.get('unit', '')) or ''
        unit = unit_raw.strip()
        if unit.lower().startswith('1 '):
            unit = unit[2:].strip()

        table_no = work.get('table_no')
        section = work.get('section')
        k1_notes = []
        field_calc = calc.get('field_calculation') or {}
        office_calc = calc.get('office_calculation') or {}
        if field_calc.get('coefficients', {}).get('K1', {}).get('notes'):
            k1_notes = field_calc['coefficients']['K1']['notes']
        elif office_calc.get('coefficients', {}).get('K1', {}).get('notes'):
            k1_notes = office_calc['coefficients']['K1']['notes']

        if table_no and section:
            sec = str(section).strip()
            if sec and sec.lower().startswith('прим'):
                sec = sec
            elif sec and not sec.lower().startswith('п.'):
                sec = f"п. {sec}"
            justification = f"т. {table_no}, {sec}"
            if k1_notes:
                justification += ", " + ", ".join([f"прим. {n}" for n in k1_notes])
        else:
            justification = work.get('table_ref', calc.get('justification', ''))

        text += f"""*Объем:* {quantity_val} {unit}
*Обоснование:* {justification}

"""
        
        # Полевые работы
        if calc.get('field_calculation'):
            fc = calc['field_calculation']
            text += f"""🏕 *ПОЛЕВЫЕ РАБОТЫ*
• Базовая цена: {fc['base_price']:,.2f} руб/{work.get('unit', '')}
• Базовая стоимость: {fc['base_cost']:,.2f} руб
"""
            if fc.get('coefficients'):
                def _fmt_coeff_value(value):
                    try:
                        return f"{float(value):.2f}"
                    except (TypeError, ValueError):
                        return str(value)

                text += "• Коэффициенты:\n"
                for code, info in fc['coefficients'].items():
                    text += f"  - {code}: {_fmt_coeff_value(info.get('value'))} ({info['reason']})\n"
            text += f"• *Итого полевые: {fc['total']:,.2f} руб*\n\n"
        
        # Камеральные работы
        if calc.get('office_calculation'):
            oc = calc['office_calculation']
            text += f"""🖥 *КАМЕРАЛЬНЫЕ РАБОТЫ*
• Базовая цена: {oc['base_price']:,.2f} руб/{work.get('unit', '')}
• Базовая стоимость: {oc['base_cost']:,.2f} руб
"""
            if oc.get('coefficients'):
                def _fmt_coeff_value(value):
                    try:
                        return f"{float(value):.2f}"
                    except (TypeError, ValueError):
                        return str(value)

                text += "• Коэффициенты:\n"
                for code, info in oc['coefficients'].items():
                    text += f"  - {code}: {_fmt_coeff_value(info.get('value'))} ({info['reason']})\n"
            text += f"• *Итого камеральные: {oc['total']:,.2f} руб*\n\n"
        
        # Надбавки (отдельными строками)
        if calc.get('addons_applied'):
            text += "➕ *НАДБАВКИ:*\n"
            for addon in calc['addons_applied']:
                rate_pct = addon.get('rate', 0) * 100
                source = addon.get('source_ref', {}).get('section', '')
                text += f"• {addon['name']}\n"
                text += f"  База: {addon.get('base', 0):,.2f} руб × {rate_pct:.2f}% = {addon['amount']:,.2f} руб"
                if source:
                    text += f" ({source})"
                text += "\n"
            text += "\n"
        
        # Ошибки и предупреждения
        if calc.get('errors'):
            text += "⚠️ *ОШИБКИ:*\n"
            for error in calc['errors']:
                text += f"• {error}\n"
            text += "\n"
        
        if calc.get('warnings'):
            text += "⚡ *ПРЕДУПРЕЖДЕНИЯ:*\n"
            for warning in calc['warnings']:
                text += f"• {warning}\n"
            text += "\n"
        
        # Итого
        text += f"""━━━━━━━━━━━━━━━━━━━━━
✅ *ИТОГО: {calc['total_cost']:,.2f} руб*
"""
        
        # Если есть индекс пересчета
        if calc.get('price_index'):
            text += f"""
📈 *С учетом индекса {calc['price_index']['year']}:*
• Индекс: {calc['price_index']['value']}
• *ИТОГО в текущих ценах: {calc['total_with_index']:,.2f} руб*
"""
        
        return text
    
    def format_clarification_question(self, missing_params: List[Dict]) -> str:
        """
        Форматирует вопрос для уточнения параметров
        
        Args:
            missing_params: Список недостающих параметров
            
        Returns:
            Отформатированный текст вопроса
        """
        if not missing_params:
            return ""
        
        param = missing_params[0]  # Спрашиваем по одному параметру
        
        text = f"❓ *{param['question']}*\n\n"
        
        for num, label, _ in param['options']:
            text += f"{num}️⃣ {label}\n"
        
        # Показываем на что влияет параметр
        if param.get('affects'):
            text += f"\n_Влияет на: {param['affects']}_"
        
        if param.get('required'):
            text += "\n\n⚠️ _Обязательный параметр_"
        
        text += "\n\n_Напишите номер или ответьте текстом_"
        
        return text
    
    def format_optional_parameters_menu(self, optional_params: List[Dict]) -> str:
        """
        Форматирует меню опциональных параметров
        
        Args:
            optional_params: Список опциональных параметров
            
        Returns:
            Отформатированный текст меню
        """
        if not optional_params:
            return ""
        
        text = "📝 *Дополнительные параметры (опционально):*\n\n"
        
        for i, param in enumerate(optional_params, 1):
            text += f"{i}. {param['question'].replace('?', '')} - _{param.get('affects', '')}_\n"
        
        text += "\n_Напишите номер параметра для уточнения или 'готово' для расчета_"
        
        return text
