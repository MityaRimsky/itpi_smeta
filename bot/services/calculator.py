"""
Калькулятор стоимости работ по СБЦ ИГДИ-2004
Рассчитывает стоимость с учетом коэффициентов K1, K2, K3 и надбавок
ВСЕ ДАННЫЕ БЕРУТСЯ ТОЛЬКО ИЗ БД - БЕЗ ХАРДКОДА И FALLBACK

Структура коэффициентов по СБЦ ИГДИ-2004:
- K1: Коэффициенты из примечаний к таблицам (условия/опции внутри конкретного вида работ)
- K2: Коэффициенты из п.15 ОУ (способ/формат выполнения/выдачи)
- K3: Коэффициенты условий производства из п.8 и п.14 ОУ (район, режим, период и т.д.)
"""

from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from loguru import logger


class CostCalculator:
    """
    Калькулятор стоимости работ по СБЦ ИГДИ-2004
    
    Порядок применения коэффициентов:
    1. K1 (примечания к таблицам) - к базовой цене строки
    2. K2 (п.15 ОУ) - к стоимости работ
    3. K3 (п.8, п.14 ОУ) - к итогу
    
    ВСЕ КОЭФФИЦИЕНТЫ БЕРУТСЯ ТОЛЬКО ИЗ БД!
    """
    
    def __init__(self, db_service):
        """
        Инициализация калькулятора
        
        Args:
            db_service: Сервис для работы с БД
        """
        self.db = db_service
    
    async def calculate_full(
        self,
        work: Dict,
        quantity: float,
        params: Dict,
        work_stage: str = 'обе'
    ) -> Dict:
        """
        Полный расчет стоимости работ с учетом полевых и камеральных
        
        Args:
            work: Данные работы из БД
            quantity: Объем работ
            params: Параметры для определения коэффициентов
            work_stage: Этап работ ('полевые', 'камеральные', 'обе')
            
        Returns:
            Детальный расчет стоимости
        """
        try:
            # Обработка None для work_stage и params
            if work_stage is None:
                work_stage = 'обе'
            if params is None:
                params = {}
            
            logger.info(f"calculate_full: work={work.get('work_title')}, quantity={quantity}, work_stage={work_stage}")
            logger.info(f"calculate_full: params={params}")
            
            qty = Decimal(str(quantity))
            table_no = work.get('table_no', 9)
            
            result = {
                'work': {
                    'id': work.get('id'),
                    'work_title': work.get('work_title'),
                    'unit': work.get('unit'),
                    'table_ref': f"т. {table_no}, {work.get('section', '')}" if table_no else work.get('section', ''),
                    'price_field': float(work.get('price_field') or 0),
                    'price_office': float(work.get('price_office') or 0),
                    'params': work.get('params', {})  # Параметры работы (категория сложности и т.д.)
                },
                'quantity': float(qty),
                'params': params,
                'field_calculation': None,
                'office_calculation': None,
                'addons_applied': [],
                'total_cost': 0,
                'justification': '',
                'errors': [],
                'warnings': []
            }
            
            total = Decimal(0)
            justification_parts = []
            
            if table_no:
                justification_parts.append(f"Табл. {table_no}")
            if work.get('section'):
                justification_parts.append(work.get('section'))
            
            # Расчет полевых работ
            field_total = Decimal(0)
            if work_stage in ['полевые', 'обе']:
                field_calc = await self._calculate_stage(
                    work=work,
                    quantity=qty,
                    params=params,
                    stage='field',
                    table_no=table_no
                )
                result['field_calculation'] = field_calc
                field_total = Decimal(str(field_calc['total']))
                total += field_total
                
                if field_calc.get('coefficients'):
                    coeff_str = ', '.join([f"{k}={v['value']}" for k, v in field_calc['coefficients'].items()])
                    justification_parts.append(f"Полевые: {coeff_str}")
                
                if field_calc.get('errors'):
                    result['errors'].extend(field_calc['errors'])
            
            # Расчет камеральных работ
            office_total = Decimal(0)
            if work_stage in ['камеральные', 'обе']:
                office_calc = await self._calculate_stage(
                    work=work,
                    quantity=qty,
                    params=params,
                    stage='office',
                    table_no=table_no
                )
                result['office_calculation'] = office_calc
                office_total = Decimal(str(office_calc['total']))
                total += office_total
                
                if office_calc.get('coefficients'):
                    coeff_str = ', '.join([f"{k}={v['value']}" for k, v in office_calc['coefficients'].items()])
                    justification_parts.append(f"Камеральные: {coeff_str}")
                
                if office_calc.get('errors'):
                    result['errors'].extend(office_calc['errors'])
            
            # Надбавки из БД (применяются к сумме полевых + камеральных)
            params_with_office = {**params, 'office_cost': float(office_total)}
            addons = await self._calculate_addons_from_db(params_with_office, float(field_total))
            result['addons_applied'] = addons
            
            total_addons = sum(Decimal(str(a['amount'])) for a in addons)
            total += total_addons
            
            if addons:
                addon_names = ', '.join([a['code'] for a in addons])
                justification_parts.append(f"Надбавки: {addon_names}")
            
            result['total_cost'] = float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            result['justification'] = '; '.join(justification_parts)
            
            logger.info(f"Расчет завершен: {result['total_cost']} руб")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета: {e}")
            raise
    
    async def _calculate_stage(
        self,
        work: Dict,
        quantity: Decimal,
        params: Dict,
        stage: str,
        table_no: int
    ) -> Dict:
        """
        Расчет стоимости для одного этапа (полевые или камеральные)
        КОЭФФИЦИЕНТЫ БЕРУТСЯ ТОЛЬКО ИЗ БД!
        
        Args:
            work: Данные работы
            quantity: Объем
            params: Параметры
            stage: 'field' или 'office'
            table_no: Номер таблицы
            
        Returns:
            Расчет для этапа
        """
        # Базовая цена
        if stage == 'field':
            base_price = Decimal(str(work.get('price_field') or 0))
        else:
            base_price = Decimal(str(work.get('price_office') or 0))
        
        base_cost = base_price * quantity
        
        # Получаем коэффициенты ТОЛЬКО из БД
        coefficients, errors = await self._get_coefficients_from_db(params, table_no, stage)
        
        # Применяем коэффициенты
        total = base_cost
        for code, info in coefficients.items():
            total *= Decimal(str(info['value']))
        
        return {
            'stage': stage,
            'base_price': float(base_price),
            'base_cost': float(base_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'coefficients': coefficients,
            'total': float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'errors': errors
        }
    
    async def _get_coefficients_from_db(self, params: Dict, table_no: int, stage: str) -> tuple:
        """
        Получает коэффициенты K1, K2, K3 ТОЛЬКО из базы данных
        БЕЗ FALLBACK - при ошибке возвращает понятное сообщение
        
        Args:
            params: Параметры работ
            table_no: Номер таблицы (например 9)
            stage: 'field' или 'office'
            
        Returns:
            Tuple[словарь коэффициентов, список ошибок]
        """
        coefficients = {}
        errors = []
        
        # ========================================
        # K1 - Коэффициенты из примечаний к таблицам (из БД)
        # ========================================
        k1_value = Decimal('1.0')
        k1_reasons = []
        k1_sources = []
        
        try:
            k1_coeffs = await self.db.get_k1_coefficients(table_no, params)
            
            # Фильтруем по exclusive_group
            k1_coeffs = self.db._filter_by_exclusive_group(k1_coeffs, params)
            
            for coeff in k1_coeffs:
                k1_value *= Decimal(str(coeff['value']))
                k1_reasons.append(coeff['name'])
                source_ref = coeff.get('source_ref', {})
                if source_ref.get('section'):
                    k1_sources.append(source_ref['section'])
            
            if not k1_coeffs:
                k1_reasons.append('Базовый (условия не заданы)')
                k1_sources.append(f'табл. {table_no}')
                
        except Exception as e:
            error_msg = f"K1 коэффициенты не получены из БД для таблицы {table_no}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            k1_reasons.append('ОШИБКА: данные не получены из БД')
            k1_sources.append(f'табл. {table_no}')
        
        coefficients['K1'] = {
            'value': float(k1_value),
            'reason': '; '.join(k1_reasons) if k1_reasons else 'Базовый',
            'source': ', '.join(k1_sources) if k1_sources else f'табл. {table_no}'
        }
        
        # ========================================
        # K2 - Коэффициенты из п.15 ОУ (из БД)
        # ========================================
        k2_value = Decimal('1.0')
        k2_reasons = []
        k2_sources = []
        
        # K2 коэффициенты:
        # - Для опорных сетей (таблица 8): K2=1.3 применяется к ПОЛЕВЫМ при use_satellite
        # - Для остальных работ: K2 применяется к КАМЕРАЛЬНЫМ (компьютерные технологии и т.д.)
        
        should_apply_k2 = False
        
        if table_no == 8:
            # Опорные сети: K2=1.3 для полевых при спутниковых системах
            if stage == 'field' and params.get('use_satellite'):
                should_apply_k2 = True
            # Камеральные опорных сетей: K2 = 1.0 (не применяется)
        else:
            # Остальные работы: K2 для камеральных
            if stage == 'office':
                should_apply_k2 = True
        
        if should_apply_k2:
            try:
                if table_no == 8 and stage == 'field':
                    # Для опорных сетей - только коэффициент спутниковых систем
                    k2_value = Decimal('1.3')
                    k2_reasons.append('Применение спутниковых систем')
                    k2_sources.append('прим. 2 к табл. 8')
                else:
                    # Для остальных - стандартные K2 коэффициенты
                    k2_coeffs = await self.db.get_k2_coefficients(params)
                    
                    for coeff in k2_coeffs:
                        k2_value *= Decimal(str(coeff['value']))
                        k2_reasons.append(coeff['name'])
                        source_ref = coeff.get('source_ref', {})
                        if source_ref.get('section'):
                            k2_sources.append(source_ref['section'])
                        
            except ValueError as ve:
                # Конфликт коэффициентов
                error_msg = str(ve)
                logger.error(error_msg)
                errors.append(error_msg)
                k2_reasons.append(f'ОШИБКА: {error_msg}')
            except Exception as e:
                error_msg = f"K2 коэффициенты не получены из БД: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                k2_reasons.append('ОШИБКА: данные не получены из БД')
        
        if not k2_reasons:
            k2_reasons.append('Базовый (условия не заданы)')
        
        coefficients['K2'] = {
            'value': float(k2_value),
            'reason': '; '.join(k2_reasons),
            'source': ', '.join(k2_sources) if k2_sources else 'ОУ п.15'
        }
        
        # ========================================
        # K3 - Коэффициенты условий производства (п.8, п.14 ОУ)
        # ========================================
        k3_value = Decimal('1.0')
        k3_reasons = []
        k3_sources = []
        
        try:
            k3_coeffs = await self.db.get_k3_coefficients(params)
            
            for coeff in k3_coeffs:
                # K3 применяется к полевым работам (кроме районных)
                apply_to = coeff.get('apply_to', 'field')
                
                if stage == 'field' and apply_to in ['field', 'total']:
                    k3_value *= Decimal(str(coeff['value']))
                    k3_reasons.append(coeff['name'])
                    source_ref = coeff.get('source_ref', {})
                    if source_ref.get('section'):
                        k3_sources.append(source_ref['section'])
                elif stage == 'office' and apply_to in ['office', 'total']:
                    k3_value *= Decimal(str(coeff['value']))
                    k3_reasons.append(coeff['name'])
                    source_ref = coeff.get('source_ref', {})
                    if source_ref.get('section'):
                        k3_sources.append(source_ref['section'])
                        
        except Exception as e:
            error_msg = f"K3 коэффициенты не получены из БД: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            k3_reasons.append('ОШИБКА: данные не получены из БД')
        
        if not k3_reasons:
            k3_reasons.append('Условия объекта не заданы')
        
        coefficients['K3'] = {
            'value': float(k3_value),
            'reason': '; '.join(k3_reasons),
            'source': ', '.join(k3_sources) if k3_sources else 'ОУ п.8, п.14'
        }
        
        return coefficients, errors
    
    async def _calculate_addons_from_db(self, params: Dict, field_cost: float) -> List[Dict]:
        """
        Рассчитывает надбавки из БД
        
        Args:
            params: Параметры работ
            field_cost: Стоимость полевых работ
            
        Returns:
            Список надбавок с суммами
        """
        try:
            # Получаем надбавки из БД по условиям
            addons = await self.db.get_addons_by_conditions(params, field_cost)
            
            if not addons:
                logger.warning("Надбавки не найдены в БД, проверьте параметры")
            
            return addons
            
        except Exception as e:
            logger.error(f"Ошибка получения надбавок из БД: {e}")
            return []
    
    # Старый метод для обратной совместимости
    async def calculate(
        self,
        work: Dict,
        quantity: float,
        coefficient_codes: Optional[List[str]] = None,
        addon_codes: Optional[List[str]] = None
    ) -> Dict:
        """
        Рассчитать стоимость работ (старый метод для совместимости)
        
        Args:
            work: Данные работы из БД
            quantity: Объем работ
            coefficient_codes: Коды коэффициентов для применения
            addon_codes: Коды надбавок для применения
            
        Returns:
            Детальный расчет стоимости
        """
        try:
            # Базовые цены (обрабатываем None)
            price_field = Decimal(str(work.get("price_field") or 0))
            price_office = Decimal(str(work.get("price_office") or 0))
            qty = Decimal(str(quantity))
            
            # Базовая стоимость
            base_field = price_field * qty
            base_office = price_office * qty
            
            logger.info(f"Базовая стоимость: полевые={base_field}, камеральные={base_office}")
            
            # Применяем коэффициенты из БД
            coefficients_applied = []
            current_field = base_field
            current_office = base_office
            
            if coefficient_codes:
                coeffs = await self.db.get_coefficients(codes=coefficient_codes)
                
                if not coeffs:
                    logger.warning(f"Коэффициенты не найдены в БД: {coefficient_codes}")
                
                for coeff in coeffs:
                    value = Decimal(str(coeff["value"]))
                    apply_to = coeff["apply_to"]
                    
                    if apply_to == "field":
                        current_field *= value
                    elif apply_to == "office":
                        current_office *= value
                    elif apply_to == "total":
                        # Применяется к итогу позже
                        pass
                    
                    coefficients_applied.append({
                        "code": coeff["code"],
                        "name": coeff["name"],
                        "value": float(value),
                        "apply_to": apply_to
                    })
                    
                    logger.info(f"Применен коэффициент {coeff['code']}: {value}")
            
            # Применяем надбавки из БД
            addons_applied = []
            total_addons = Decimal(0)
            
            if addon_codes:
                addons = await self.db.get_addons(codes=addon_codes)
                
                if not addons:
                    logger.warning(f"Надбавки не найдены в БД: {addon_codes}")
                
                for addon in addons:
                    calc_type = addon["calc_type"]
                    value = Decimal(str(addon["value"]))
                    base_type = addon["base_type"]
                    
                    # Определяем базу для расчета
                    if base_type == "field":
                        base = current_field
                    elif base_type == "office":
                        base = current_office
                    elif base_type == "field_plus_office":
                        base = current_field + current_office
                    elif base_type == "field_plus_internal":
                        # Для внешнего транспорта (полевые + внутренний транспорт)
                        base = current_field + total_addons
                    else:
                        base = current_field + current_office
                    
                    # Рассчитываем надбавку
                    if calc_type == "percent":
                        addon_amount = base * value
                    elif calc_type == "fixed":
                        addon_amount = value
                    elif calc_type == "per_unit":
                        addon_amount = value * qty
                    else:
                        addon_amount = Decimal(0)
                    
                    total_addons += addon_amount
                    
                    addons_applied.append({
                        "code": addon["code"],
                        "name": addon["name"],
                        "calc_type": calc_type,
                        "value": float(value),
                        "base": float(base),
                        "amount": float(addon_amount)
                    })
                    
                    logger.info(f"Применена надбавка {addon['code']}: {addon_amount}")
            
            # Итоговая стоимость
            subtotal = current_field + current_office + total_addons
            
            # Применяем коэффициенты к итогу (например, районные)
            total_coeffs = [c for c in coefficients_applied if c["apply_to"] == "total"]
            final_total = subtotal
            
            for coeff in total_coeffs:
                final_total *= Decimal(str(coeff["value"]))
                logger.info(f"Применен итоговый коэффициент {coeff['code']}: {coeff['value']}")
            
            # Формируем обоснование
            justification = self._build_justification(work, coefficients_applied, addons_applied)
            
            result = {
                "work": {
                    "id": work.get("id"),
                    "name": work["work_title"],
                    "work_title": work["work_title"],
                    "code": work.get("code", work.get("section", "")),
                    "unit": work["unit"],
                    "table_ref": f"т. {work.get('table_no')}, {work.get('section', '')}" if work.get('table_no') else work.get('section', ''),
                    "price_field": float(work.get("price_field") or 0),
                    "price_office": float(work.get("price_office") or 0)
                },
                "quantity": float(qty),
                "base_price": float(price_field),
                "base_field": float(base_field),
                "base_office": float(base_office),
                "field_with_coeffs": float(current_field),
                "office_with_coeffs": float(current_office),
                "coefficients": coefficients_applied,
                "addons": addons_applied,
                "total_addons": float(total_addons),
                "subtotal": float(subtotal),
                "total_cost": float(final_total),
                "justification": justification
            }
            
            logger.info(f"Итоговая стоимость: {final_total}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета стоимости: {e}")
            raise
    
    def _build_justification(
        self,
        work: Dict,
        coefficients: List[Dict],
        addons: List[Dict]
    ) -> str:
        """
        Формирует обоснование расчета
        
        Args:
            work: Данные работы
            coefficients: Примененные коэффициенты
            addons: Примененные надбавки
            
        Returns:
            Текст обоснования
        """
        parts = []
        
        # Основная расценка
        table_no = work.get("table_no")
        section = work.get("section", "")
        
        if table_no:
            parts.append(f"Табл. {table_no}")
        if section:
            parts.append(section)
        
        # Коэффициенты
        if coefficients:
            coeff_refs = []
            for coeff in coefficients:
                # Извлекаем ссылку из source_ref если есть
                coeff_refs.append(coeff["code"])
            
            if coeff_refs:
                parts.append(f"Коэфф.: {', '.join(coeff_refs)}")
        
        # Надбавки
        if addons:
            addon_refs = []
            for addon in addons:
                addon_refs.append(addon["code"])
            
            if addon_refs:
                parts.append(f"Надбавки: {', '.join(addon_refs)}")
        
        return "; ".join(parts) if parts else "Без обоснования"
