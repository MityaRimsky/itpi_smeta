"""
Калькулятор стоимости работ по СБЦ ИГДИ-2004
Рассчитывает стоимость с учетом коэффициентов K1, K2, K3 и надбавок
Поддерживает раздельный расчет полевых и камеральных работ

Структура коэффициентов по СБЦ ИГДИ-2004:
- K1: Коэффициенты из примечаний к таблицам (условия/опции внутри конкретного вида работ)
- K2: Коэффициенты из п.15 ОУ (способ/формат выполнения/выдачи)
- K3: Коэффициенты условий производства из п.8 и п.14 ОУ (район, режим, период и т.д.)
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from loguru import logger


class CostCalculator:
    """
    Калькулятор стоимости работ по СБЦ ИГДИ-2004
    
    Порядок применения коэффициентов:
    1. K1 (примечания к таблицам) - к базовой цене строки
    2. K2 (п.15 ОУ) - к стоимости работ
    3. K3 (п.8, п.14 ОУ) - к итогу (пока = 1.0, данные объекта не заданы)
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
            # Обработка None для work_stage
            if work_stage is None:
                work_stage = 'обе'
            
            logger.info(f"calculate_full: work={work}, quantity={quantity}, work_stage={work_stage}")
            logger.info(f"calculate_full: price_field={work.get('price_field')}, price_office={work.get('price_office')}")
            
            qty = Decimal(str(quantity))
            
            result = {
                'work': {
                    'id': work.get('id'),
                    'work_title': work.get('work_title'),
                    'unit': work.get('unit'),
                    'table_ref': f"т. {work.get('table_no')}, {work.get('section', '')}" if work.get('table_no') else work.get('section', ''),
                    'price_field': float(work.get('price_field') or 0),
                    'price_office': float(work.get('price_office') or 0)
                },
                'quantity': float(qty),
                'params': params,
                'field_calculation': None,
                'office_calculation': None,
                'addons_applied': [],
                'total_cost': 0,
                'justification': ''
            }
            
            total = Decimal(0)
            justification_parts = []
            
            if work.get('table_no'):
                justification_parts.append(f"Табл. {work.get('table_no')}")
            if work.get('section'):
                justification_parts.append(work.get('section'))
            
            # Расчет полевых работ
            if work_stage in ['полевые', 'обе']:
                field_calc = self._calculate_stage(
                    work=work,
                    quantity=qty,
                    params=params,
                    stage='field'
                )
                result['field_calculation'] = field_calc
                total += Decimal(str(field_calc['total']))
                
                if field_calc.get('coefficients'):
                    coeff_str = ', '.join([f"{k}={v['value']}" for k, v in field_calc['coefficients'].items()])
                    justification_parts.append(f"Полевые: {coeff_str}")
            
            # Расчет камеральных работ
            if work_stage in ['камеральные', 'обе']:
                office_calc = self._calculate_stage(
                    work=work,
                    quantity=qty,
                    params=params,
                    stage='office'
                )
                result['office_calculation'] = office_calc
                total += Decimal(str(office_calc['total']))
                
                if office_calc.get('coefficients'):
                    coeff_str = ', '.join([f"{k}={v['value']}" for k, v in office_calc['coefficients'].items()])
                    justification_parts.append(f"Камеральные: {coeff_str}")
            
            # Надбавки (применяются к сумме полевых + камеральных)
            addons = await self._calculate_addons(params, float(total))
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
    
    def _calculate_stage(
        self,
        work: Dict,
        quantity: Decimal,
        params: Dict,
        stage: str
    ) -> Dict:
        """
        Расчет стоимости для одного этапа (полевые или камеральные)
        
        Args:
            work: Данные работы
            quantity: Объем
            params: Параметры
            stage: 'field' или 'office'
            
        Returns:
            Расчет для этапа
        """
        # Базовая цена
        if stage == 'field':
            base_price = Decimal(str(work.get('price_field') or 0))
        else:
            base_price = Decimal(str(work.get('price_office') or 0))
        
        base_cost = base_price * quantity
        
        # Определяем коэффициенты
        coefficients = self._get_coefficients(params, stage)
        
        # Применяем коэффициенты
        total = base_cost
        for code, info in coefficients.items():
            total *= Decimal(str(info['value']))
        
        return {
            'stage': stage,
            'base_price': float(base_price),
            'base_cost': float(base_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'coefficients': coefficients,
            'total': float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
    
    async def _get_coefficients_from_db(self, params: Dict, table_no: int, stage: str) -> Dict:
        """
        Получает коэффициенты K1, K2, K3 из базы данных
        
        Args:
            params: Параметры работ
            table_no: Номер таблицы (например 9)
            stage: 'field' или 'office'
            
        Returns:
            Словарь коэффициентов K1, K2, K3
        """
        coefficients = {}
        
        # ========================================
        # K1 - Коэффициенты из примечаний к таблицам (из БД)
        # ========================================
        k1_value = Decimal('1.0')
        k1_reasons = []
        k1_sources = []
        
        try:
            k1_coeffs = await self.db.get_k1_coefficients(table_no, params)
            for coeff in k1_coeffs:
                k1_value *= Decimal(str(coeff['value']))
                k1_reasons.append(coeff['name'])
                source_ref = coeff.get('source_ref', {})
                if source_ref.get('section'):
                    k1_sources.append(source_ref['section'])
            
            if not k1_coeffs:
                k1_reasons.append('Базовый')
                k1_sources.append(f'табл. {table_no}')
                
        except Exception as e:
            logger.warning(f"Ошибка получения K1 из БД: {e}, используем fallback")
            k1_value, k1_reasons, k1_sources = self._get_k1_fallback(params)
        
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
        
        # Для камеральных работ добавляем коэффициенты из п.15 ОУ
        if stage == 'office':
            try:
                k2_coeffs = await self.db.get_k2_coefficients(params)
                for coeff in k2_coeffs:
                    k2_value *= Decimal(str(coeff['value']))
                    k2_reasons.append(coeff['name'])
                    source_ref = coeff.get('source_ref', {})
                    if source_ref.get('section'):
                        k2_sources.append(source_ref['section'])
                        
            except Exception as e:
                logger.warning(f"Ошибка получения K2 из БД: {e}, используем fallback")
                k2_value, k2_reasons, k2_sources = self._get_k2_fallback(params, stage)
        
        if not k2_reasons:
            k2_reasons.append('Базовый')
        
        coefficients['K2'] = {
            'value': float(k2_value),
            'reason': '; '.join(k2_reasons),
            'source': ', '.join(k2_sources) if k2_sources else 'ОУ п.15'
        }
        
        # ========================================
        # K3 - Коэффициенты условий производства (п.8, п.14 ОУ)
        # ПОКА = 1.0 (данные объекта не заданы)
        # ========================================
        coefficients['K3'] = {
            'value': 1.0,
            'reason': 'Условия объекта не заданы',
            'source': 'ОУ п.8, п.14'
        }
        
        return coefficients
    
    def _get_k1_fallback(self, params: Dict) -> tuple:
        """
        Fallback для K1 если БД недоступна
        K1 - коэффициент территории + подземные коммуникации (прим. 4 к табл. 9)
        """
        territory = params.get('territory_type')
        has_underground = params.get('has_underground_comms')
        update_mode = params.get('update_mode', False)
        
        k1_value = Decimal('1.0')
        k1_reasons = []
        k1_sources = []
        
        # Прим. 4 к табл. 9 - съемка подземных коммуникаций
        if has_underground:
            if territory == 'промпредприятие':
                k1_value = Decimal('1.75')
                k1_reasons.append('Промпредприятие + подземные')
                k1_sources.append('прим. 4')
            elif territory == 'застроенная':
                k1_value = Decimal('1.55')
                k1_reasons.append('Застроенная + подземные')
                k1_sources.append('прим. 4')
            else:
                k1_value = Decimal('1.20')
                k1_reasons.append('Незастроенная + подземные')
                k1_sources.append('прим. 4')
        
        # Обновление существующего плана (табл. 10)
        if update_mode:
            k1_value *= Decimal('0.50')
            k1_reasons.append('Обновление')
            k1_sources.append('табл. 10')
        
        if not k1_reasons:
            k1_reasons.append('Базовый')
            k1_sources.append('табл. 9')
        
        return k1_value, k1_reasons, k1_sources
    
    def _get_k2_fallback(self, params: Dict, stage: str) -> tuple:
        """
        Fallback для K2 если БД недоступна
        K2 - коэффициент эскизов опор (прим. 5 к табл. 9) для полевых
             + коэффициенты п.15 ОУ для камеральных
        """
        has_pole_sketches = params.get('has_pole_sketches', False)
        use_computer = params.get('use_computer', True)
        dual_format = params.get('dual_format', False)
        color_plan = params.get('color_plan', False)
        
        k2_value = Decimal('1.0')
        k2_reasons = []
        k2_sources = []
        
        # Прим. 5 к табл. 9 - эскизы опор (применяется к полевым работам)
        if stage == 'field':
            if has_pole_sketches:
                k2_value = Decimal('1.30')
                k2_reasons.append('Эскизы опор')
                k2_sources.append('прим. 5')
        
        # Коэффициенты п.15 ОУ (применяются к камеральным работам)
        if stage == 'office':
            # Прим. 5 к табл. 9 - эскизы опор (применяется и к камеральным)
            if has_pole_sketches:
                k2_value *= Decimal('1.30')
                k2_reasons.append('Эскизы опор')
                k2_sources.append('прим. 5')
            
            if use_computer and dual_format:
                logger.warning("Конфликт: п.15д и п.15е нельзя применять одновременно!")
                dual_format = False
            
            if use_computer:
                k2_value *= Decimal('1.20')
                k2_reasons.append('Компьютерные технологии')
                k2_sources.append('ОУ п.15д')
            
            if dual_format:
                k2_value *= Decimal('1.75')
                k2_reasons.append('Два носителя')
                k2_sources.append('ОУ п.15е')
            
            if color_plan:
                k2_value *= Decimal('1.10')
                k2_reasons.append('План в цвете')
                k2_sources.append('ОУ п.15г')
        
        if not k2_reasons:
            k2_reasons.append('Базовый')
        
        return k2_value, k2_reasons, k2_sources
    
    def _get_coefficients(self, params: Dict, stage: str) -> Dict:
        """
        Синхронная версия получения коэффициентов (fallback)
        Используется когда нет доступа к БД
        
        Args:
            params: Параметры работ
            stage: 'field' или 'office'
            
        Returns:
            Словарь коэффициентов K1, K2, K3
        """
        coefficients = {}
        
        # Обработка None для params
        if params is None:
            params = {}
        
        # K1 - из fallback
        k1_value, k1_reasons, k1_sources = self._get_k1_fallback(params)
        coefficients['K1'] = {
            'value': float(k1_value),
            'reason': '; '.join(k1_reasons),
            'source': ', '.join(k1_sources)
        }
        
        # K2 - из fallback
        k2_value, k2_reasons, k2_sources = self._get_k2_fallback(params, stage)
        coefficients['K2'] = {
            'value': float(k2_value),
            'reason': '; '.join(k2_reasons),
            'source': ', '.join(k2_sources) if k2_sources else 'ОУ п.15'
        }
        
        # K3 - пока всегда 1.0
        coefficients['K3'] = {
            'value': 1.0,
            'reason': 'Условия объекта не заданы',
            'source': 'ОУ п.8, п.14'
        }
        
        return coefficients
    
    async def _calculate_addons(self, params: Dict, base_cost: float) -> List[Dict]:
        """
        Рассчитывает надбавки
        
        Args:
            params: Параметры работ
            base_cost: Базовая стоимость (полевые + камеральные)
            
        Returns:
            Список надбавок с суммами
        """
        addons = []
        
        # Внутренний транспорт - зависит от стоимости работ
        if base_cost <= 75000:
            addon_code = 'INTERNAL_TRANSPORT_T4_1_1'
            addon_rate = 0.0875  # 8.75%
            addon_name = 'Внутренний транспорт: до 5 км, стоимость до 75 тыс.руб'
        elif base_cost <= 150000:
            addon_code = 'INTERNAL_TRANSPORT_T4_1_2'
            addon_rate = 0.075  # 7.5%
            addon_name = 'Внутренний транспорт: до 5 км, стоимость до 150 тыс.руб'
        elif base_cost <= 300000:
            addon_code = 'INTERNAL_TRANSPORT_T4_1_3'
            addon_rate = 0.0625  # 6.25%
            addon_name = 'Внутренний транспорт: до 5 км, стоимость до 300 тыс.руб'
        else:
            addon_code = 'INTERNAL_TRANSPORT_T4_1_4'
            addon_rate = 0.05  # 5%
            addon_name = 'Внутренний транспорт: до 5 км, стоимость свыше 300 тыс.руб'
        
        addon_amount = Decimal(str(base_cost)) * Decimal(str(addon_rate))
        
        addons.append({
            'code': addon_code,
            'name': addon_name,
            'rate': addon_rate,
            'base': base_cost,
            'amount': float(addon_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        })
        
        return addons
    
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
            
            # Применяем коэффициенты
            coefficients_applied = []
            current_field = base_field
            current_office = base_office
            
            if coefficient_codes:
                coeffs = await self.db.get_coefficients(codes=coefficient_codes)
                
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
            
            # Применяем надбавки
            addons_applied = []
            total_addons = Decimal(0)
            
            if addon_codes:
                addons = await self.db.get_addons(codes=addon_codes)
                
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
