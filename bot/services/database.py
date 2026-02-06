"""
Сервис для работы с базой данных Supabase
Предоставляет методы для поиска расценок, коэффициентов и надбавок
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from supabase import create_client, Client
from loguru import logger


@dataclass
class SearchResult:
    """Результат поиска работ с детальной информацией"""
    works: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    search_terms_used: List[str] = field(default_factory=list)
    
    @property
    def found(self) -> bool:
        return len(self.works) > 0
    
    def to_error_message(self) -> str:
        """Формирует сообщение об ошибке для пользователя"""
        if self.found:
            return ""
        
        msg = "❌ Работы не найдены.\n\n"
        
        if self.errors:
            msg += "🔍 *Проблемы:*\n"
            for err in self.errors:
                msg += f"• {err}\n"
            msg += "\n"
        
        if self.suggestions:
            msg += "💡 *Попробуйте:*\n"
            for sug in self.suggestions:
                msg += f"• {sug}\n"
        
        if self.search_terms_used:
            msg += f"\n_Искали по: {', '.join(self.search_terms_used)}_"
        
        return msg


class DatabaseService:
    """Сервис для работы с Supabase"""
    
    def __init__(self, url: str, key: str):
        """
        Инициализация подключения к Supabase
        
        Args:
            url: URL Supabase проекта
            key: Service role key для полного доступа
        """
        self.client: Client = create_client(url, key)
        logger.info(f"Подключение к Supabase: {url}")
    
    async def search_works_v2(
        self, 
        query: str, 
        scale: Optional[str] = None,
        category: Optional[str] = None,
        territory: Optional[str] = None,
        limit: int = 10
    ) -> SearchResult:
        """
        Улучшенный поиск работ с детальной информацией об ошибках
        
        Args:
            query: Поисковый запрос
            scale: Масштаб
            category: Категория сложности
            territory: Тип территории
            limit: Максимальное количество результатов
            
        Returns:
            SearchResult с работами или детальными ошибками
        """
        result = SearchResult()
        
        # 1. Расширяем запрос синонимами
        search_terms = await self._expand_query_with_synonyms(query)
        result.search_terms_used = search_terms[:5]  # Показываем первые 5
        
        # 2. Добавляем масштаб в поиск если указан
        if scale:
            search_terms.append(scale)
        
        # 3. Ищем работы по всем терминам
        all_works = []
        seen_ids = set()
        
        for term in search_terms:
            try:
                response = self.client.table("norm_items").select(
                    "id, work_title, unit, price_field, price_office, table_no, section, params"
                ).ilike("work_title", f"%{term}%").limit(limit * 2).execute()
                
                for item in response.data:
                    if item['id'] not in seen_ids:
                        seen_ids.add(item['id'])
                        all_works.append(item)
                        
            except Exception as e:
                logger.error(f"Ошибка поиска по термину '{term}': {e}")
        
        if not all_works:
            result.errors.append(f"Не найдены работы по запросу '{query}'")
            result.suggestions.append("Попробуйте: 'инженерно-топографический план'")
            result.suggestions.append("Или укажите масштаб: '1:500', '1:2000'")
            
            # Показываем доступные типы работ
            available = await self._get_available_work_types()
            if available:
                result.suggestions.append(f"Доступные типы: {', '.join(available[:5])}")
            
            return result
        
        # 4. Фильтруем по параметрам
        filtered_works = []
        filter_errors = []
        
        for work in all_works:
            params = work.get('params', {})
            work_title = work.get('work_title', '').lower()
            
            # Проверяем масштаб
            if scale:
                work_scale = params.get('scale', '')
                if scale not in work_title and work_scale != scale:
                    continue
            
            # Проверяем категорию сложности
            if category:
                work_category = params.get('category', '')
                # Если у работы есть категория - она должна совпадать
                if work_category:
                    if work_category != category:
                        continue
                # Если у работы нет категории - она подходит для любой категории
            
            # Проверяем территорию
            if territory:
                work_territory = params.get('territory', '')
                territory_lower = territory.lower()
                if work_territory and work_territory.lower() != territory_lower:
                    # Проверяем в названии
                    if territory_lower not in work_title:
                        continue
            
            filtered_works.append(work)
        
        if not filtered_works and all_works:
            # Работы найдены, но не прошли фильтры
            if scale:
                available_scales = set()
                for w in all_works:
                    p = w.get('params', {})
                    if p.get('scale'):
                        available_scales.add(p['scale'])
                    # Извлекаем масштаб из названия
                    title = w.get('work_title', '')
                    for s in ['1:500', '1:1000', '1:2000', '1:5000']:
                        if s in title:
                            available_scales.add(s)
                
                if available_scales:
                    result.errors.append(f"Масштаб {scale} не найден для данного типа работ")
                    result.suggestions.append(f"Доступные масштабы: {', '.join(sorted(available_scales))}")
            
            if category:
                available_cats = set()
                for w in all_works:
                    p = w.get('params', {})
                    if p.get('category'):
                        available_cats.add(p['category'])
                
                if available_cats:
                    result.errors.append(f"Категория {category} не найдена")
                    result.suggestions.append(f"Доступные категории: {', '.join(sorted(available_cats))}")
            
            if territory:
                result.errors.append(f"Тип территории '{territory}' не найден")
                result.suggestions.append("Доступные: застроенная, незастроенная, промпредприятие")
            
            return result
        
        # 5. Преобразуем в нужный формат
        for item in filtered_works[:limit]:
            result.works.append({
                'id': item['id'],
                'name': item['work_title'],
                'work_title': item['work_title'],
                'code': item.get('section', ''),
                'unit': item.get('unit', ''),
                'price': item.get('price_field', 0),
                'price_field': item.get('price_field', 0),
                'price_office': item.get('price_office', 0),
                'table_no': item.get('table_no'),
                'table_ref': f"т. {item.get('table_no')}, {item.get('section', '')}",
                'section': item.get('section', ''),
                'params': item.get('params', {})
            })
        
        logger.info(f"Найдено работ (v2): {len(result.works)} по запросу '{query}'")
        return result
    
    async def _expand_query_with_synonyms(self, query: str) -> List[str]:
        """Расширяет запрос синонимами из БД"""
        terms = [query]
        query_lower = query.lower()
        
        # Добавляем стандартные варианты
        if any(kw in query_lower for kw in ['топо', 'съемка', 'съёмка']):
            terms.extend(['инженерно-топографическ', 'план', 'топографическ'])
        
        if any(kw in query_lower for kw in ['опорн', 'сет', 'геодезическ']):
            terms.extend(['опорн', 'сет', 'разряд', 'класс'])
        
        if any(kw in query_lower for kw in ['трасс', 'дорог', 'линейн']):
            terms.extend(['трасс', 'изыскан', 'дорог'])
        
        # Ищем синонимы в БД
        try:
            response = self.client.table("work_synonyms").select("main_term, synonyms").execute()
            
            for row in response.data:
                main_term = row.get('main_term', '').lower()
                synonyms = row.get('synonyms', [])
                
                # Если запрос содержит main_term или синоним
                if main_term in query_lower:
                    terms.extend(synonyms)
                else:
                    for syn in synonyms:
                        if syn.lower() in query_lower:
                            terms.append(main_term)
                            terms.extend(synonyms)
                            break
                            
        except Exception as e:
            logger.error(f"Ошибка получения синонимов: {e}")
        
        # Убираем дубликаты, сохраняя порядок
        seen = set()
        unique_terms = []
        for t in terms:
            t_lower = t.lower()
            if t_lower not in seen:
                seen.add(t_lower)
                unique_terms.append(t)
        
        return unique_terms
    
    async def _get_available_work_types(self) -> List[str]:
        """Получает список доступных типов работ"""
        try:
            response = self.client.table("norm_items").select("work_title").limit(100).execute()
            
            # Извлекаем уникальные типы
            types = set()
            for item in response.data:
                title = item.get('work_title', '')
                # Берем первые 3-4 слова
                words = title.split()[:4]
                types.add(' '.join(words))
            
            return sorted(list(types))[:10]
            
        except Exception as e:
            logger.error(f"Ошибка получения типов работ: {e}")
            return []

    async def search_works(
        self, 
        query: str, 
        scale: Optional[str] = None,
        category: Optional[str] = None,
        territory: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Поиск работ по запросу с фильтрами (обратная совместимость)
        
        Args:
            query: Поисковый запрос (например, "топографическая съемка")
            scale: Масштаб (например, "1:500")
            category: Категория сложности (I, II, III, IV)
            territory: Тип территории (застроенная, незастроенная, промпредприятие)
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных работ с ценами
        """
        # Используем новый метод
        result = await self.search_works_v2(query, scale, category, territory, limit)
        
        if result.found:
            return result.works
        
        # Если не нашли - логируем ошибки и возвращаем пустой список
        if result.errors:
            logger.warning(f"Поиск не дал результатов: {'; '.join(result.errors)}")
        
        return []
    
    async def _fallback_search(
        self,
        query: str,
        scale: Optional[str] = None,
        category: Optional[str] = None,
        territory: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fallback поиск с альтернативными вариантами запроса"""
        # Список вариантов поиска
        search_variants = [query]
        
        # Добавляем альтернативные варианты для топографии
        query_lower = query.lower()
        if any(kw in query_lower for kw in ['топо', 'план', 'съемка', 'инженерно']):
            search_variants.extend([
                'топографическ',
                'инженерно-топографическ',
                'план',
                '1:500'
            ])
        
        results = []
        seen_ids = set()
        
        for search_term in search_variants:
            try:
                query_builder = self.client.table("norm_items").select(
                    "id, work_title, unit, price_field, price_office, table_no, section, params"
                )
                
                # Поиск по названию работы
                query_builder = query_builder.ilike("work_title", f"%{search_term}%")
                
                # Выполняем запрос
                response = query_builder.limit(limit).execute()
                
                # Преобразуем результаты
                for item in response.data:
                    if item['id'] in seen_ids:
                        continue
                    seen_ids.add(item['id'])
                    
                    results.append({
                        'id': item['id'],
                        'name': item['work_title'],
                        'work_title': item['work_title'],
                        'code': item.get('section', ''),
                        'unit': item.get('unit', ''),
                        'price': item.get('price_field', 0),
                        'price_field': item.get('price_field', 0),
                        'price_office': item.get('price_office', 0),
                        'table_no': item.get('table_no'),
                        'table_ref': f"т. {item.get('table_no')}, {item.get('section', '')}",
                        'section': item.get('section', ''),
                        'params': item.get('params', {})
                    })
                
                if len(results) >= limit:
                    break
                    
            except Exception as e2:
                logger.error(f"Ошибка fallback поиска для '{search_term}': {e2}")
                continue
        
        logger.info(f"Найдено работ (fallback): {len(results)} по запросу '{query}'")
        return results[:limit]
    
    async def get_work_by_id(self, work_id: str) -> Optional[Dict]:
        """
        Получить работу по ID
        
        Args:
            work_id: UUID работы
            
        Returns:
            Данные работы или None
        """
        try:
            response = self.client.table("norm_items").select("*").eq("id", work_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения работы {work_id}: {e}")
            return None
    
    async def get_coefficients(
        self,
        apply_to: Optional[str] = None,
        codes: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Получить коэффициенты
        
        Args:
            apply_to: К чему применяется (field, office, total, price)
            codes: Список кодов коэффициентов
            
        Returns:
            Список коэффициентов
        """
        try:
            query_builder = self.client.table("norm_coeffs").select("*")
            
            if apply_to:
                query_builder = query_builder.eq("apply_to", apply_to)
            
            if codes:
                query_builder = query_builder.in_("code", codes)
            
            response = query_builder.execute()
            
            logger.info(f"Получено коэффициентов: {len(response.data)}")
            return response.data
            
        except Exception as e:
            logger.error(f"Ошибка получения коэффициентов: {e}")
            return []
    
    async def get_addons(
        self,
        base_type: Optional[str] = None,
        codes: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Получить добавочные начисления
        
        Args:
            base_type: Тип базы (field, office, field_plus_office, field_plus_internal, subtotal)
            codes: Список кодов надбавок
            
        Returns:
            Список надбавок
        """
        try:
            query_builder = self.client.table("norm_addons").select("*")
            
            if base_type:
                query_builder = query_builder.eq("base_type", base_type)
            
            if codes:
                query_builder = query_builder.in_("code", codes)
            
            response = query_builder.execute()
            
            logger.info(f"Получено надбавок: {len(response.data)}")
            return response.data
            
        except Exception as e:
            logger.error(f"Ошибка получения надбавок: {e}")
            return []
    
    async def search_synonyms(self, term: str) -> List[Dict]:
        """
        Поиск синонимов для термина
        
        Args:
            term: Поисковый термин
            
        Returns:
            Список синонимов
        """
        try:
            response = self.client.table("work_synonyms").select("*").or_(
                f"main_term.ilike.%{term}%,synonyms.cs.{{{term}}}"
            ).execute()
            
            logger.info(f"Найдено синонимов: {len(response.data)} для '{term}'")
            return response.data
            
        except Exception as e:
            logger.error(f"Ошибка поиска синонимов: {e}")
            return []
    
    async def get_k1_coefficients(
        self,
        table_no: int,
        params: Dict
    ) -> List[Dict]:
        """
        Получить K1 коэффициенты из примечаний к таблице
        
        Args:
            table_no: Номер таблицы (например 9)
            params: Параметры работ (territory_type, has_underground_comms и т.д.)
            
        Returns:
            Список подходящих коэффициентов K1
        """
        try:
            # Получаем все K1 коэффициенты для данной таблицы
            response = self.client.table("norm_coeffs").select("*").like(
                "code", f"K1_T{table_no}_%"
            ).execute()
            
            if not response.data:
                logger.info(f"K1 коэффициенты для таблицы {table_no} не найдены")
                return []
            
            # Фильтруем по условиям
            matching = []
            for coeff in response.data:
                conditions = coeff.get('conditions', {})
                
                # Проверяем соответствие условий параметрам
                match = True
                
                # Проверка territory_type
                if 'territory_type' in conditions:
                    if params.get('territory_type') != conditions['territory_type']:
                        match = False
                
                # Проверка has_underground_comms
                if 'has_underground_comms' in conditions:
                    if params.get('has_underground_comms') != conditions['has_underground_comms']:
                        match = False
                
                # Проверка has_detailed_wells_sketches
                if 'has_detailed_wells_sketches' in conditions:
                    if params.get('has_detailed_wells_sketches') != conditions['has_detailed_wells_sketches']:
                        match = False
                
                # Проверка update_mode
                if 'update_mode' in conditions:
                    if params.get('update_mode') != conditions['update_mode']:
                        match = False
                
                # Проверка use_satellite (для таблицы 8 - опорные сети)
                if 'use_satellite' in conditions:
                    if params.get('use_satellite') != conditions['use_satellite']:
                        match = False
                
                if match:
                    matching.append(coeff)
            
            logger.info(f"Найдено K1 коэффициентов для таблицы {table_no}: {len(matching)}")
            return matching
            
        except Exception as e:
            logger.error(f"Ошибка получения K1 коэффициентов: {e}")
            return []
    
    async def get_k2_coefficients(
        self,
        params: Dict
    ) -> List[Dict]:
        """
        Получить K2 коэффициенты из п.15 ОУ
        
        Args:
            params: Параметры работ (use_computer, dual_format, color_plan и т.д.)
            
        Returns:
            Список подходящих коэффициентов K2
        """
        try:
            # Коды K2 коэффициентов из п.15
            k2_codes = []
            
            # п.15а - Промежуточные материалы
            if params.get('intermediate_materials'):
                k2_codes.append('INTERMEDIATE_MATERIALS_1_10')
            
            # п.15б - Материалы ограниченного пользования
            if params.get('classified_materials'):
                k2_codes.append('CLASSIFIED_MATERIALS_1_10')
            
            # п.15в - Искусственное освещение
            if params.get('artificial_lighting'):
                k2_codes.append('ARTIFICIAL_LIGHTING_1_15')
            
            # п.15г - План в цвете
            if params.get('color_plan'):
                k2_codes.append('COLOR_PLAN_1_10')
            
            # п.15д и п.15е - проверка конфликта
            use_computer = params.get('use_computer', True)
            dual_format = params.get('dual_format', False)
            
            if use_computer and dual_format:
                # Конфликт! Нельзя применять оба коэффициента
                logger.warning("Конфликт: п.15д и п.15е нельзя применять одновременно!")
                raise ValueError("Конфликт коэффициентов: п.15д (компьютерные технологии) и п.15е (2 носителя) нельзя применять одновременно")
            
            # п.15д - Компьютерные технологии
            if use_computer:
                k2_codes.append('COMPUTER_TECH_1_20')
            
            # п.15е - Два носителя (магнитный + бумажный)
            if dual_format:
                k2_codes.append('DUAL_FORMAT_1_75')
            
            if not k2_codes:
                return []
            
            # Получаем коэффициенты из БД
            response = self.client.table("norm_coeffs").select("*").in_(
                "code", k2_codes
            ).execute()
            
            logger.info(f"Найдено K2 коэффициентов: {len(response.data)}")
            return response.data
            
        except ValueError:
            raise  # Пробрасываем ошибку конфликта
        except Exception as e:
            logger.error(f"Ошибка получения K2 коэффициентов: {e}")
            return []
    
    async def get_k3_coefficients(
        self,
        params: Dict
    ) -> List[Dict]:
        """
        Получить K3 коэффициенты условий производства (п.8, п.14 ОУ)
        
        Args:
            params: Параметры работ (altitude, unfavorable_months, region_type, salary_coeff и т.д.)
            
        Returns:
            Список подходящих коэффициентов K3
        """
        try:
            matching = []
            
            # Горные районы (табл.1, п.8а)
            altitude = params.get('altitude')
            if altitude:
                response = self.client.table("norm_coeffs").select("*").like(
                    "code", "MOUNTAIN_%"
                ).execute()
                
                for coeff in response.data:
                    conditions = coeff.get('conditions', {})
                    alt_min = conditions.get('altitude_min', 0)
                    alt_max = conditions.get('altitude_max', 999999)
                    
                    if alt_min <= altitude < alt_max:
                        matching.append(coeff)
                        break  # Только один коэффициент горных районов
            
            # Неблагоприятный период (табл.2, п.8г)
            unfavorable_months = params.get('unfavorable_months')
            if unfavorable_months:
                response = self.client.table("norm_coeffs").select("*").like(
                    "code", "UNFAVORABLE_%"
                ).execute()
                
                for coeff in response.data:
                    conditions = coeff.get('conditions', {})
                    months_min = conditions.get('unfavorable_months_min', 0)
                    months_max = conditions.get('unfavorable_months_max', 12)
                    
                    if months_min <= unfavorable_months <= months_max:
                        matching.append(coeff)
                        break  # Только один коэффициент сезонности
            
            # Районный коэффициент (табл.3, п.8д)
            salary_coeff = params.get('salary_coeff')
            if salary_coeff and salary_coeff > 1.0:
                response = self.client.table("norm_coeffs").select("*").like(
                    "code", "REGION_K_%"
                ).execute()
                
                # Находим ближайший коэффициент
                best_match = None
                best_diff = float('inf')
                
                for coeff in response.data:
                    conditions = coeff.get('conditions', {})
                    coeff_salary = conditions.get('salary_coeff', 1.0)
                    diff = abs(coeff_salary - salary_coeff)
                    
                    if diff < best_diff:
                        best_diff = diff
                        best_match = coeff
                
                if best_match:
                    matching.append(best_match)
            
            # Крайний Север (п.8е)
            region_type = params.get('region_type')
            if region_type:
                code_map = {
                    'far_north': 'FAR_NORTH_1_50',
                    'far_north_equivalent': 'FAR_NORTH_EQUIV_1_25',
                    'south_regions': 'SOUTH_REGIONS_1_15'
                }
                if region_type in code_map:
                    response = self.client.table("norm_coeffs").select("*").eq(
                        "code", code_map[region_type]
                    ).execute()
                    if response.data:
                        matching.append(response.data[0])
            
            # Спецрежим территории (п.8в)
            if params.get('special_regime'):
                response = self.client.table("norm_coeffs").select("*").eq(
                    "code", "SPECIAL_REGIME_1_25"
                ).execute()
                if response.data:
                    matching.append(response.data[0])
            
            # Ночные работы (п.8в)
            if params.get('night_time'):
                response = self.client.table("norm_coeffs").select("*").eq(
                    "code", "NIGHT_TIME_1_35"
                ).execute()
                if response.data:
                    matching.append(response.data[0])
            
            # Полевое довольствие (п.14)
            if params.get('no_field_allowance'):
                response = self.client.table("norm_coeffs").select("*").eq(
                    "code", "NO_FIELD_ALLOWANCE_0_85"
                ).execute()
                if response.data:
                    matching.append(response.data[0])
            
            logger.info(f"Найдено K3 коэффициентов: {len(matching)}")
            return matching
            
        except Exception as e:
            logger.error(f"Ошибка получения K3 коэффициентов: {e}")
            return []
    
    async def get_addons_by_conditions(
        self,
        params: Dict,
        field_cost: float,
        internal_transport_cost: float = 0
    ) -> List[Dict]:
        """
        Получить надбавки по условиям из БД
        
        Args:
            params: Параметры работ
            field_cost: Стоимость полевых работ
            internal_transport_cost: Стоимость внутреннего транспорта (для внешнего)
            
        Returns:
            Список надбавок с рассчитанными суммами
        """
        try:
            addons = []
            base_field_plus_internal = field_cost + internal_transport_cost
            
            # 1. Внутренний транспорт (табл.4, п.9)
            distance_to_base = params.get('distance_to_base', 5)  # По умолчанию до 5 км
            
            response = self.client.table("norm_addons").select("*").like(
                "code", "INTERNAL_TRANSPORT_T4_%"
            ).execute()
            
            for addon in response.data:
                conditions = addon.get('conditions', {})
                dist_min = conditions.get('distance_min') or 0
                dist_max = conditions.get('distance_max') or 999
                cost_min = conditions.get('cost_min') or 0
                cost_max = conditions.get('cost_max') or float('inf')
                
                # Безопасное сравнение с None
                if dist_min is None:
                    dist_min = 0
                if dist_max is None:
                    dist_max = 999
                if cost_min is None:
                    cost_min = 0
                if cost_max is None:
                    cost_max = float('inf')
                
                if dist_min <= distance_to_base <= dist_max:
                    if cost_min <= field_cost <= cost_max:
                        addon_amount = field_cost * addon['value']
                        addons.append({
                            'code': addon['code'],
                            'name': addon['name'],
                            'calc_type': addon['calc_type'],
                            'rate': addon['value'],
                            'base': field_cost,
                            'amount': round(addon_amount, 2),
                            'source_ref': addon.get('source_ref', {})
                        })
                        break  # Только одна надбавка внутреннего транспорта
            
            # 2. Внешний транспорт (табл.5, п.10)
            external_distance = params.get('external_distance')
            expedition_duration = params.get('expedition_duration')
            
            if external_distance and expedition_duration:
                response = self.client.table("norm_addons").select("*").like(
                    "code", "EXTERNAL_TRANSPORT_T5_%"
                ).execute()
                
                for addon in response.data:
                    conditions = addon.get('conditions', {})
                    dist_min = conditions.get('distance_min', 0)
                    dist_max = conditions.get('distance_max', 999999)
                    dur = conditions.get('duration')
                    dur_min = conditions.get('duration_min')
                    dur_max = conditions.get('duration_max')
                    
                    if dist_min <= external_distance <= dist_max:
                        duration_match = False
                        if dur and expedition_duration == dur:
                            duration_match = True
                        elif dur_max and expedition_duration <= dur_max:
                            duration_match = True
                        elif dur_min and expedition_duration >= dur_min:
                            duration_match = True
                        
                        if duration_match:
                            addon_amount = base_field_plus_internal * addon['value']
                            addons.append({
                                'code': addon['code'],
                                'name': addon['name'],
                                'calc_type': addon['calc_type'],
                                'rate': addon['value'],
                                'base': base_field_plus_internal,
                                'amount': round(addon_amount, 2),
                                'source_ref': addon.get('source_ref', {})
                            })
                            break
            
            # 3. Организация и ликвидация (п.13)
            response = self.client.table("norm_addons").select("*").eq(
                "code", "ORG_LIQ_6PCT"
            ).execute()
            
            if response.data:
                addon = response.data[0]
                # Проверяем коэффициенты к орг.ликвидации
                org_liq_rate = addon['value']
                
                # Коэффициенты в зависимости от стоимости
                if field_cost <= 30000 or params.get('region_type') == 'far_north':
                    org_liq_rate = 0.15  # K=2.5
                elif field_cost <= 75000:
                    org_liq_rate = 0.12  # K=2.0
                elif field_cost <= 150000:
                    org_liq_rate = 0.09  # K=1.5
                
                addon_amount = base_field_plus_internal * org_liq_rate
                addons.append({
                    'code': addon['code'],
                    'name': addon['name'],
                    'calc_type': addon['calc_type'],
                    'rate': org_liq_rate,
                    'base': base_field_plus_internal,
                    'amount': round(addon_amount, 2),
                    'source_ref': addon.get('source_ref', {})
                })
            
            # 4. Удорожания (как отдельные строки)
            # Сезонное удорожание
            unfavorable_months = params.get('unfavorable_months')
            if unfavorable_months:
                response = self.client.table("norm_addons").select("*").like(
                    "code", "SEASONAL_ADDON_%"
                ).execute()
                
                for addon in response.data:
                    conditions = addon.get('conditions', {})
                    months_min = conditions.get('unfavorable_months_min', 0)
                    months_max = conditions.get('unfavorable_months_max', 12)
                    
                    if months_min <= unfavorable_months <= months_max:
                        addon_amount = field_cost * addon['value']
                        addons.append({
                            'code': addon['code'],
                            'name': addon['name'],
                            'calc_type': addon['calc_type'],
                            'rate': addon['value'],
                            'base': field_cost,
                            'amount': round(addon_amount, 2),
                            'source_ref': addon.get('source_ref', {})
                        })
                        break
            
            # Региональное удорожание
            salary_coeff = params.get('salary_coeff')
            if salary_coeff and salary_coeff > 1.0:
                response = self.client.table("norm_addons").select("*").like(
                    "code", "REGIONAL_ADDON_%"
                ).execute()
                
                best_match = None
                best_diff = float('inf')
                
                for addon in response.data:
                    conditions = addon.get('conditions', {})
                    addon_salary = conditions.get('salary_coeff', 1.0)
                    diff = abs(addon_salary - salary_coeff)
                    
                    if diff < best_diff:
                        best_diff = diff
                        best_match = addon
                
                if best_match:
                    # subtotal = полевые + камеральные + предыдущие надбавки
                    subtotal = field_cost + params.get('office_cost', 0) + sum(a['amount'] for a in addons)
                    addon_amount = subtotal * best_match['value']
                    addons.append({
                        'code': best_match['code'],
                        'name': best_match['name'],
                        'calc_type': best_match['calc_type'],
                        'rate': best_match['value'],
                        'base': subtotal,
                        'amount': round(addon_amount, 2),
                        'source_ref': best_match.get('source_ref', {})
                    })
            
            # Горное удорожание
            altitude = params.get('altitude')
            if altitude and altitude >= 1500:
                response = self.client.table("norm_addons").select("*").like(
                    "code", "MOUNTAIN_ADDON_%"
                ).execute()
                
                for addon in response.data:
                    conditions = addon.get('conditions', {})
                    alt_min = conditions.get('altitude_min', 0)
                    alt_max = conditions.get('altitude_max', 999999)
                    
                    if alt_min <= altitude < alt_max:
                        addon_amount = field_cost * addon['value']
                        addons.append({
                            'code': addon['code'],
                            'name': addon['name'],
                            'calc_type': addon['calc_type'],
                            'rate': addon['value'],
                            'base': field_cost,
                            'amount': round(addon_amount, 2),
                            'source_ref': addon.get('source_ref', {})
                        })
                        break
            
            # Спецрежим удорожание
            if params.get('special_regime'):
                response = self.client.table("norm_addons").select("*").eq(
                    "code", "SPECIAL_REGIME_ADDON"
                ).execute()
                
                if response.data:
                    addon = response.data[0]
                    addon_amount = field_cost * addon['value']
                    addons.append({
                        'code': addon['code'],
                        'name': addon['name'],
                        'calc_type': addon['calc_type'],
                        'rate': addon['value'],
                        'base': field_cost,
                        'amount': round(addon_amount, 2),
                        'source_ref': addon.get('source_ref', {})
                    })
            
            # Промежуточные материалы
            if params.get('intermediate_materials'):
                response = self.client.table("norm_addons").select("*").eq(
                    "code", "INTERMEDIATE_MATERIALS_ADDON"
                ).execute()
                
                if response.data:
                    addon = response.data[0]
                    total_work_cost = field_cost + params.get('office_cost', 0)
                    addon_amount = total_work_cost * addon['value']
                    addons.append({
                        'code': addon['code'],
                        'name': addon['name'],
                        'calc_type': addon['calc_type'],
                        'rate': addon['value'],
                        'base': total_work_cost,
                        'amount': round(addon_amount, 2),
                        'source_ref': addon.get('source_ref', {})
                    })
            
            logger.info(f"Найдено надбавок по условиям: {len(addons)}")
            return addons
            
        except Exception as e:
            logger.error(f"Ошибка получения надбавок: {e}")
            return []
    
    def _filter_by_exclusive_group(self, coefficients: List[Dict], params: Dict) -> List[Dict]:
        """
        Фильтрует коэффициенты по exclusive_group - из одной группы выбирается только один
        
        Args:
            coefficients: Список коэффициентов
            params: Параметры для выбора
            
        Returns:
            Отфильтрованный список
        """
        result = []
        seen_groups = set()
        
        for coeff in coefficients:
            group = coeff.get('exclusive_group')
            
            if group:
                if group in seen_groups:
                    continue  # Уже есть коэффициент из этой группы
                seen_groups.add(group)
            
            result.append(coeff)
        
        return result
