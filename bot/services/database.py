"""
Сервис для работы с базой данных Supabase
Предоставляет методы для поиска расценок, коэффициентов и надбавок
"""

from typing import List, Dict, Optional, Any, Tuple
import re
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

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            try:
                return float(str(value).replace(",", "."))
            except Exception:
                return None

    @staticmethod
    def _normalize_scale(scale: Optional[str]) -> Optional[str]:
        if not scale:
            return None
        text = str(scale).strip().replace(" ", "")
        m = re.search(r"1:(\d+)", text)
        if m:
            return f"1:{m.group(1)}"
        if text.isdigit():
            return f"1:{text}"
        return text

    @staticmethod
    def _scale_to_int(scale: Optional[str]) -> Optional[int]:
        if not scale:
            return None
        m = re.search(r"1:(\d+)", str(scale))
        if m:
            return int(m.group(1))
        if str(scale).isdigit():
            return int(scale)
        return None

    @staticmethod
    def _match_range(value: Optional[float], min_val: Optional[float], max_val: Optional[float]) -> bool:
        if value is None:
            return False
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True

    @staticmethod
    def _match_bool(param_val: Any, condition_val: Any) -> bool:
        # Если условие в коэффициенте не задано — параметр не ограничивает выбор
        if condition_val is None:
            return True
        # Если условие задано, а параметр не передан пользователем — НЕ матчим.
        # Иначе None превращается в False и приводит к ложному выбору коэффициентов.
        if param_val is None:
            return False
        return bool(param_val) == bool(condition_val)

    @staticmethod
    def _normalize_territory(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).lower().strip()
        if "пром" in text:
            return "промпредприятие"
        if "застро" in text:
            return "застроенная"
        if "незастро" in text:
            return "незастроенная"
        return text

    @staticmethod
    def _piecewise_amount(base_thousand: float, fixed_amount: Optional[float], percent_over: Optional[float], threshold_thousand: Optional[float]) -> float:
        fixed = fixed_amount or 0.0
        if percent_over is None:
            return fixed
        threshold = threshold_thousand or 0.0
        over = max(base_thousand - threshold, 0.0) * 1000.0
        return fixed + (over * percent_over)

    async def enrich_params_with_region(self, params: Dict) -> Dict:
        """
        Дополняет params региональными коэффициентами и периодами из приложений.
        Приоритет: заданные params > данные из БД.
        """
        if not params:
            params = {}
        enriched = dict(params)
        region_code = enriched.get("region_code")
        region_name = enriched.get("region_name")

        try:
            if region_code and not enriched.get("salary_coeff"):
                resp = self.client.table("regional_coeffs").select("*").eq("region_code", region_code).execute()
                if resp.data:
                    enriched["salary_coeff"] = resp.data[0].get("salary_coeff")

            if region_name:
                if not enriched.get("salary_coeff"):
                    resp = self.client.table("regional_coeffs").select("*").ilike("region_name", f"%{region_name}%").execute()
                    if resp.data:
                        enriched["salary_coeff"] = resp.data[0].get("salary_coeff")

                if not enriched.get("unfavorable_months"):
                    resp = self.client.table("regional_unfavorable_periods").select("*").ilike("region_name", f"%{region_name}%").execute()
                    if resp.data:
                        enriched["unfavorable_months"] = resp.data[0].get("duration_months")

                if not enriched.get("desert_coeff"):
                    resp = self.client.table("regional_desert_coeffs").select("*").ilike("region_name", f"%{region_name}%").execute()
                    if resp.data:
                        enriched["desert_coeff"] = resp.data[0].get("coeff")

                if not enriched.get("region_type"):
                    resp = self.client.table("regional_zone_lists").select("*").ilike("region_name", f"%{region_name}%").execute()
                    if resp.data:
                        zone_types = {r.get("zone_type") for r in resp.data}
                        if "far_north" in zone_types:
                            enriched["region_type"] = "far_north"
                        elif "far_north_equivalent" in zone_types:
                            enriched["region_type"] = "far_north_equivalent"
                        elif "south_regions" in zone_types:
                            enriched["region_type"] = "south_regions"

        except Exception as e:
            logger.error(f"Ошибка обогащения параметров региона: {e}")

        return enriched
    
    async def search_works_v2(
        self, 
        query: str, 
        scale: Optional[str] = None,
        category: Optional[str] = None,
        territory: Optional[str] = None,
        height_section: Optional[float] = None,
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
            table_no = work.get('table_no')

            # Для инженерно-топографических планов используем таблицу 9
            if query and any(k in query.lower() for k in ['топограф', 'инженерно-топограф', 'топоплан']):
                if table_no is not None and int(table_no) != 9:
                    continue
            
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

            # Проверяем сечение рельефа (высоту сечения)
            if height_section is not None:
                try:
                    hs = float(height_section)
                except Exception:
                    hs = None
                if hs is not None:
                    work_hs = params.get('height_section')
                    if work_hs is None:
                        # Пытаемся извлечь из названия
                        m = re.search(r"(\\d+[\\.,]?\\d*)", work_title)
                        if m:
                            try:
                                work_hs = float(m.group(1).replace(',', '.'))
                            except Exception:
                                work_hs = None
                    if work_hs is not None:
                        try:
                            work_hs_val = float(str(work_hs).replace(',', '.'))
                            if abs(work_hs_val - hs) > 1e-6:
                                continue
                        except Exception:
                            pass
            
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
        params: Dict,
        stage: str = "field",
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
            if table_no is None:
                logger.info("K1 коэффициенты не запрошены: table_no не указан")
                return []
            doc_resp = self.client.table("norm_docs").select("id").eq("code", "SBC_IGDI_2004").execute()
            if not doc_resp.data:
                logger.warning("Документ SBC_IGDI_2004 не найден для K1")
                return []
            doc_id = doc_resp.data[0]["id"]
            scale = self._normalize_scale(params.get("scale") or params.get("work_scale"))
            height_section = self._to_float(params.get("height_section") or params.get("relief_section"))
            # territory_type (из параметров пользователя) имеет приоритет над territory (из строки работы)
            territory = self._normalize_territory(params.get("territory_type") or params.get("territory"))
            area_ha = self._to_float(params.get("area_ha"))
            strip_width_m = self._to_float(params.get("strip_width_m"))

            # Получаем табличные коэффициенты (apply_to=price/field/office) и фильтруем по table_no
            response = (
                self.client.table("norm_coeffs")
                .select("*")
                .eq("doc_id", doc_id)
                .in_("apply_to", ["price", "field", "office"])
                .execute()
            )

            if not response.data:
                logger.info(f"K1 коэффициенты (apply_to=price) не найдены для doc_id={doc_id}")
                return []

            matching = []
            for coeff in response.data:
                conditions = coeff.get("conditions", {})
                source_ref = coeff.get("source_ref", {})
                apply_to = coeff.get("apply_to", "price")

                coeff_table_no = conditions.get("table_no") or source_ref.get("table")
                # K1 всегда должен быть привязан к конкретной таблице.
                # Коэффициенты без явной привязки к таблице не применяем,
                # чтобы не «подмешивать» нерелевантные правила.
                if coeff_table_no is None:
                    continue
                if int(coeff_table_no) != int(table_no):
                    continue

                match = True
                reasons = []

                if apply_to == "field" and stage != "field":
                    match = False
                    reasons.append("apply_to_stage")
                if apply_to == "office" and stage != "office":
                    match = False
                    reasons.append("apply_to_stage")

                if "territory_type" in conditions:
                    cond_territory = self._normalize_territory(conditions.get("territory_type"))
                    if self._normalize_territory(params.get("territory_type") or params.get("territory")) != cond_territory:
                        match = False
                        reasons.append("territory_type")
                if "territory" in conditions:
                    cond_territory = self._normalize_territory(conditions.get("territory"))
                    if self._normalize_territory(territory) != cond_territory:
                        match = False
                        reasons.append("territory")

                if "has_underground_comms" in conditions:
                    if not self._match_bool(params.get("has_underground_comms"), conditions.get("has_underground_comms")):
                        match = False
                        reasons.append("has_underground_comms")

                if "has_detailed_wells_sketches" in conditions:
                    if not self._match_bool(params.get("has_detailed_wells_sketches"), conditions.get("has_detailed_wells_sketches")):
                        match = False
                        reasons.append("has_detailed_wells_sketches")

                if "update_mode" in conditions:
                    if not self._match_bool(params.get("update_mode"), conditions.get("update_mode")):
                        match = False
                        reasons.append("update_mode")

                if "use_satellite" in conditions:
                    if not self._match_bool(params.get("use_satellite"), conditions.get("use_satellite")):
                        match = False
                        reasons.append("use_satellite")

                if "no_center" in conditions:
                    if not self._match_bool(params.get("no_center"), conditions.get("no_center")):
                        match = False
                        reasons.append("no_center")

                if "section" in conditions:
                    try:
                        if int(params.get("section")) != int(conditions.get("section")):
                            match = False
                            reasons.append("section")
                    except Exception:
                        match = False
                        reasons.append("section")
                if "section_min" in conditions or "section_max" in conditions:
                    try:
                        section_val = int(params.get("section")) if params.get("section") is not None else None
                    except Exception:
                        section_val = None
                    if not self._match_range(section_val, conditions.get("section_min"), conditions.get("section_max")):
                        match = False
                        reasons.append("section_range")

                if "special_object" in conditions:
                    if params.get("special_object") != conditions["special_object"]:
                        match = False
                        reasons.append("special_object")

                if "measurement_drawings" in conditions:
                    if not self._match_bool(params.get("measurement_drawings"), conditions.get("measurement_drawings")):
                        match = False
                        reasons.append("measurement_drawings")

                if "red_lines" in conditions:
                    if not self._match_bool(params.get("red_lines"), conditions.get("red_lines")):
                        match = False
                        reasons.append("red_lines")

                if "analytic_coords" in conditions:
                    if not self._match_bool(params.get("analytic_coords"), conditions.get("analytic_coords")):
                        match = False
                        reasons.append("analytic_coords")

                if "scale" in conditions:
                    if self._normalize_scale(conditions.get("scale")) != scale:
                        match = False
                        reasons.append("scale")
                if "scale_min" in conditions or "scale_max" in conditions:
                    scale_val = self._scale_to_int(scale)
                    min_scale = self._scale_to_int(conditions.get("scale_min"))
                    max_scale = self._scale_to_int(conditions.get("scale_max"))
                    if not self._match_range(scale_val, min_scale, max_scale):
                        match = False
                        reasons.append("scale_range")

                if "height_section" in conditions:
                    cond_hs = self._to_float(conditions.get("height_section"))
                    if cond_hs is not None and height_section is not None:
                        if abs(cond_hs - height_section) > 1e-6:
                            match = False
                            reasons.append("height_section")
                    elif cond_hs is not None and height_section is None:
                        match = False
                        reasons.append("height_section")

                if "area_min" in conditions or "area_max" in conditions:
                    if not self._match_range(area_ha, conditions.get("area_min"), conditions.get("area_max")):
                        match = False
                        reasons.append("area_range")

                if "strip_width_min" in conditions or "strip_width_max" in conditions:
                    if not self._match_range(strip_width_m, conditions.get("strip_width_min"), conditions.get("strip_width_max")):
                        match = False
                        reasons.append("strip_width_range")

                if "vertical_survey" in conditions:
                    if not self._match_bool(params.get("vertical_survey"), conditions.get("vertical_survey")):
                        match = False
                        reasons.append("vertical_survey")

                if "tree_survey" in conditions:
                    if not self._match_bool(params.get("tree_survey"), conditions.get("tree_survey")):
                        match = False
                        reasons.append("tree_survey")

                if match:
                    matching.append(coeff)
                # no match, skip
            
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
            # K2 применяем только если есть хотя бы один явный признак из п.15 ОУ
            if not any([
                params.get("intermediate_materials"),
                params.get("classified_materials") or params.get("restricted_materials"),
                params.get("artificial_lighting") or params.get("artificial_light"),
                params.get("color_plan"),
                params.get("use_computer") or params.get("computer_tech"),
                params.get("dual_format") or params.get("dual_media"),
            ]):
                return []

            doc_resp = self.client.table("norm_docs").select("id").eq("code", "SBC_IGDI_2004").execute()
            if not doc_resp.data:
                logger.warning("Документ SBC_IGDI_2004 не найден для K2")
                return []
            doc_id = doc_resp.data[0]["id"]

            response = self.client.table("norm_coeffs").select("*").eq("doc_id", doc_id).eq("apply_to", "office").execute()
            if not response.data:
                return []

            matching = []
            for coeff in response.data:
                conditions = coeff.get("conditions", {})
                source_ref = coeff.get("source_ref", {}) or {}
                if source_ref.get("source") != "rtf_2004":
                    # Игнорируем записи из "note"/не-RTF, у них другая схема условий
                    continue

                # K2 — это только коэффициенты по п.15 ОУ.
                # Исключаем офисные коэффициенты из других разделов (например, п.14).
                section = str(source_ref.get("section", ""))
                if not section.startswith("п.15"):
                    continue

                match = True

                if "intermediate_materials" in conditions:
                    if not self._match_bool(params.get("intermediate_materials"), conditions.get("intermediate_materials")):
                        match = False
                if "restricted_materials" in conditions:
                    if not self._match_bool(params.get("classified_materials") or params.get("restricted_materials"), conditions.get("restricted_materials")):
                        match = False
                if "artificial_light" in conditions:
                    if not self._match_bool(params.get("artificial_lighting") or params.get("artificial_light"), conditions.get("artificial_light")):
                        match = False
                if "color_plan" in conditions:
                    if not self._match_bool(params.get("color_plan"), conditions.get("color_plan")):
                        match = False
                if "computer_tech" in conditions:
                    if not self._match_bool(params.get("use_computer") or params.get("computer_tech"), conditions.get("computer_tech")):
                        match = False
                if "dual_media" in conditions:
                    if not self._match_bool(params.get("dual_format") or params.get("dual_media"), conditions.get("dual_media")):
                        match = False

                if match:
                    matching.append(coeff)

            # Фильтруем по exclusive_group
            matching = self._filter_by_exclusive_group(matching, params)

            logger.info(f"Найдено K2 коэффициентов: {len(matching)}")
            return matching
            
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
            if params.get('apply_conditions_as_addons'):
                logger.info("K3 коэффициенты пропущены: условия будут учтены как надбавки")
                return []
            matching = []

            doc_resp = self.client.table("norm_docs").select("id").eq("code", "SBC_IGDI_2004").execute()
            if not doc_resp.data:
                logger.warning("Документ SBC_IGDI_2004 не найден для K3")
                return []
            doc_id = doc_resp.data[0]["id"]

            altitude = self._to_float(params.get("altitude_m") or params.get("altitude"))
            unfavorable_months = self._to_float(params.get("unfavorable_months"))
            salary_coeff = self._to_float(params.get("salary_coeff"))
            region_type = params.get("region_type")
            radioactivity = self._to_float(params.get("radioactivity_msv_per_year"))

            response = self.client.table("norm_coeffs").select("*").eq("doc_id", doc_id).in_("apply_to", ["field", "office", "total"]).execute()
            for coeff in response.data:
                conditions = coeff.get("conditions", {})
                source_ref = coeff.get("source_ref", {}) or {}
                if source_ref.get("source") != "rtf_2004":
                    # Игнорируем записи из "note"/не-RTF, у них другая схема условий
                    continue
                section = str(source_ref.get("section", ""))

                # K3 относится только к п.8 и п.14 ОУ.
                # Исключаем коэффициенты из таблиц и примечаний (например, табл.9).
                if section and not (section.startswith("п.8") or section.startswith("п.14")):
                    continue
                if not section:
                    # Без явного раздела - пропускаем, чтобы не подмешивать нерелевантные правила
                    continue
                if not conditions:
                    # Без условий коэффициент не должен применяться автоматически
                    continue
                # Если в условиях есть неподдерживаемые ключи — пропускаем,
                # чтобы не применять "чужие" коэффициенты.
                allowed_keys = {
                    "altitude_min",
                    "altitude_max",
                    "unfavorable_months_min",
                    "unfavorable_months_max",
                    "salary_coeff",
                    "region_type",
                    "special_regime",
                    "night_work",
                    "no_field_allowance",
                    "office_in_field_camp",
                    "radioactivity_msv_per_year_min",
                    "radioactivity_coeff_range",
                }
                if any(k not in allowed_keys for k in conditions.keys()):
                    continue
                match = True

                if "altitude_min" in conditions or "altitude_max" in conditions:
                    if not self._match_range(altitude, conditions.get("altitude_min"), conditions.get("altitude_max")):
                        match = False

                if "unfavorable_months_min" in conditions or "unfavorable_months_max" in conditions:
                    if not self._match_range(unfavorable_months, conditions.get("unfavorable_months_min"), conditions.get("unfavorable_months_max")):
                        match = False

                if "salary_coeff" in conditions:
                    cond_salary = self._to_float(conditions.get("salary_coeff"))
                    if cond_salary is not None and salary_coeff is not None:
                        if abs(cond_salary - salary_coeff) > 1e-6:
                            match = False
                    elif cond_salary is not None and salary_coeff is None:
                        match = False

                if "region_type" in conditions:
                    if (region_type or "").lower() != str(conditions.get("region_type")).lower():
                        match = False

                if "special_regime" in conditions:
                    if not self._match_bool(params.get("special_regime"), conditions.get("special_regime")):
                        match = False

                if "night_work" in conditions:
                    if not self._match_bool(params.get("night_time") or params.get("night_work"), conditions.get("night_work")):
                        match = False

                if "no_field_allowance" in conditions:
                    if not self._match_bool(params.get("no_field_allowance"), conditions.get("no_field_allowance")):
                        match = False

                if "office_in_field_camp" in conditions:
                    if not self._match_bool(params.get("office_in_field_camp"), conditions.get("office_in_field_camp")):
                        match = False

                if "radioactivity_msv_per_year_min" in conditions:
                    if radioactivity is None or radioactivity < self._to_float(conditions.get("radioactivity_msv_per_year_min")):
                        match = False

                if match:
                    matching.append(coeff)

            # Пустынные и безводные районы (Приложение 1)
            desert_coeff = self._to_float(params.get("desert_coeff"))
            if desert_coeff:
                matching.append({
                    "code": "DESERT_COEFF",
                    "name": "Пустынные и безводные районы",
                    "value": desert_coeff,
                    "apply_to": "field",
                    "source_ref": {"appendix": 1}
                })
                matching.append({
                    "code": "DESERT_COEFF_OFFICE",
                    "name": "Пустынные и безводные районы (кам.)",
                    "value": desert_coeff,
                    "apply_to": "office",
                    "source_ref": {"appendix": 1}
                })

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
            apply_conditions_as_addons = params.get('apply_conditions_as_addons', False)
            office_cost = params.get('office_cost', 0) or 0
            base_cost_thousand = params.get('base_cost_thousand')
            if base_cost_thousand is None:
                base_cost_thousand = (field_cost + office_cost) / 1000.0
            
            # 1. Внутренний транспорт (табл.4, п.9)
            distance_to_base = self._to_float(params.get('distance_to_base_km') or params.get('distance_to_base'))
            
            if distance_to_base is not None:
                response = self.client.table("norm_addons").select("*").like(
                    "code", "INTERNAL_T4_%"
                ).execute()
                
                for addon in response.data:
                    conditions = addon.get('conditions', {})
                    dist_min = conditions.get('distance_from_base_km_min')
                    dist_max = conditions.get('distance_from_base_km_max')
                    cost_min = conditions.get('field_cost_thousand_min')
                    cost_max = conditions.get('field_cost_thousand_max')
                    field_cost_thousand = field_cost / 1000.0
                    
                    if self._match_range(distance_to_base, dist_min, dist_max):
                        if self._match_range(field_cost_thousand, cost_min, cost_max):
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
            external_distance = self._to_float(params.get('external_distance_km') or params.get('external_distance'))
            expedition_duration = self._to_float(params.get('expedition_duration_months') or params.get('expedition_duration'))
            
            if external_distance and expedition_duration:
                response = self.client.table("norm_addons").select("*").like(
                    "code", "EXTERNAL_T5_%"
                ).execute()
                
                for addon in response.data:
                    conditions = addon.get('conditions', {})
                    dist_min = conditions.get('distance_oneway_km_min')
                    dist_max = conditions.get('distance_oneway_km_max')
                    dur_min = conditions.get('duration_months_min')
                    dur_max = conditions.get('duration_months_max')
                    
                    if self._match_range(external_distance, dist_min, dist_max):
                        if self._match_range(expedition_duration, dur_min, dur_max):
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
            if params.get('include_org_liq'):
                response = self.client.table("norm_addons").select("*").eq(
                    "code", "ORG_LIQ_6PCT"
                ).execute()
                
                if response.data:
                    addon = response.data[0]
                    # Проверяем коэффициенты к орг.ликвидации
                    org_liq_rate = addon['value']

                    # Коэффициенты в зависимости от стоимости (п.13)
                    cost_coeff = 1.0
                    if field_cost <= 30000 or params.get('region_type') == 'far_north':
                        cost_coeff = 2.5
                    elif field_cost <= 75000:
                        cost_coeff = 2.0
                    elif field_cost <= 150000:
                        cost_coeff = 1.5

                    # Коэффициенты по длительности (табл.6)
                    duration_coeff = 1.0
                    if expedition_duration:
                        resp = self.client.table("norm_coeffs").select("*").like(
                            "code", "ORG_LIQ_DURATION_%"
                        ).execute()
                        for coeff in resp.data:
                            conditions = coeff.get('conditions', {})
                            if conditions.get('applies_to_addon') != 'ORG_LIQ_6PCT':
                                continue
                            if self._match_range(expedition_duration, conditions.get('duration_months_min'), conditions.get('duration_months_max')):
                                duration_coeff = coeff.get('value', 1.0)
                                break

                    org_liq_rate = org_liq_rate * cost_coeff * duration_coeff
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
            if apply_conditions_as_addons:
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

            # 5. Формульные надбавки (табл.78-80)
            response = self.client.table("norm_addons").select("*").like(
                "code", "PROGRAM_T78_%"
            ).execute()
            response2 = self.client.table("norm_addons").select("*").like(
                "code", "REPORT_T79_%"
            ).execute()
            response3 = self.client.table("norm_addons").select("*").like(
                "code", "REGISTRATION_T80_%"
            ).execute()
            piecewise = (response.data or []) + (response2.data or []) + (response3.data or [])
            for addon in piecewise:
                conditions = addon.get('conditions', {})
                min_th = conditions.get('base_cost_thousand_min')
                max_th = conditions.get('base_cost_thousand_max')
                if not self._match_range(base_cost_thousand, min_th, max_th):
                    continue
                fixed = conditions.get('fixed_amount')
                percent_over = conditions.get('percent_over')
                amount = self._piecewise_amount(base_cost_thousand, fixed, percent_over, min_th)
                addons.append({
                    'code': addon['code'],
                    'name': addon['name'],
                    'calc_type': addon['calc_type'],
                    'rate': addon['value'],
                    'base': base_cost_thousand * 1000.0,
                    'amount': round(amount, 2),
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
        grouped = {}
        nongrouped = []

        for coeff in coefficients:
            group = coeff.get('exclusive_group')
            if not group:
                nongrouped.append(coeff)
                continue
            grouped.setdefault(group, []).append(coeff)

        for group, items in grouped.items():
            # Выбираем максимальный коэффициент в группе
            best = max(items, key=lambda c: float(c.get('value') or 0))
            result.append(best)

        result.extend(nongrouped)
        return result
