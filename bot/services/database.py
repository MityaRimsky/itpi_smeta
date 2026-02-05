"""
Сервис для работы с базой данных Supabase
Предоставляет методы для поиска расценок, коэффициентов и надбавок
"""

from typing import List, Dict, Optional, Any
from supabase import create_client, Client
from loguru import logger


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
    
    async def search_works(
        self, 
        query: str, 
        scale: Optional[str] = None,
        category: Optional[str] = None,
        territory: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Поиск работ по запросу с фильтрами
        
        Args:
            query: Поисковый запрос (например, "топографическая съемка")
            scale: Масштаб (например, "1:500")
            category: Категория сложности (I, II, III, IV)
            territory: Тип территории (застроенная, незастроенная, промпредприятие)
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных работ с ценами
        """
        try:
            # Базовый запрос - используем RPC функцию для семантического поиска
            response = self.client.rpc(
                'semantic_search_norm_items',
                {
                    'search_query': query,
                    'limit_count': limit * 3  # Берем больше для фильтрации
                }
            ).execute()
            
            # Преобразуем результаты в нужный формат и применяем фильтры
            results = []
            for item in response.data:
                # Получаем полную информацию о работе
                work_data = self.client.table("norm_items").select("*").eq("id", item['id']).execute()
                if not work_data.data:
                    continue
                    
                work = work_data.data[0]
                params = work.get('params', {})
                
                # Применяем фильтры если указаны
                if scale and params.get('scale') != scale:
                    continue
                if category and params.get('category') != category:
                    continue
                if territory and params.get('territory') != territory:
                    continue
                
                results.append({
                    'id': work['id'],
                    'name': work['work_title'],
                    'work_title': work['work_title'],
                    'code': work.get('section', ''),
                    'unit': work.get('unit', ''),
                    'price': work.get('price_field', 0),
                    'price_field': work.get('price_field', 0),
                    'price_office': work.get('price_office', 0),
                    'table_no': work.get('table_no'),
                    'table_ref': f"т. {work.get('table_no')}, {work.get('section', '')}",
                    'section': work.get('section', ''),
                    'params': params,
                    'relevance_score': item.get('relevance_score', 0),
                    'match_type': item.get('match_type', 'unknown')
                })
                
                if len(results) >= limit:
                    break
            
            logger.info(f"Найдено работ: {len(results)} по запросу '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска работ: {e}")
            # Fallback на простой поиск если RPC не работает
            return await self._fallback_search(query, scale, category, territory, limit)
    
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
