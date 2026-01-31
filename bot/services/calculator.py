"""
Калькулятор стоимости работ
Рассчитывает стоимость с учетом коэффициентов и надбавок
Поддерживает раздельный расчет полевых и камеральных работ
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from loguru import logger


class CostCalculator:
    """Калькулятор стоимости работ"""
    
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
    
    def _get_coefficients(self, params: Dict, stage: str) -> Dict:
        """
        Получает коэффициенты для этапа работ
        
        Args:
            params: Параметры работ
            stage: 'field' или 'office'
            
        Returns:
            Словарь коэффициентов
        """
        coefficients = {}
        
        territory = params.get('territory_type')
        has_underground = params.get('has_underground_comms')
        has_poles = params.get('has_pole_sketches')
        use_computer = params.get('use_computer', True)
        update_mode = params.get('update_mode')
        
        # К1 - Территория промпредприятия (прим. 4 к т. 9)
        if territory == 'промпредприятие':
            coefficients['К1'] = {
                'value': 1.75,
                'reason': 'Территория промпредприятия (прим. 4)'
            }
        elif territory == 'застроенная':
            # Базовый коэффициент для застроенной территории
            coefficients['К1'] = {
                'value': 1.0,
                'reason': 'Застроенная территория'
            }
        # Для незастроенной территории К1 = 1.0 (не добавляем)
        
        # К2 - Съемка подземных коммуникаций (прим. 5 к т. 9)
        if has_underground:
            coefficients['К2'] = {
                'value': 1.30,
                'reason': 'Съемка подземных коммуникаций (прим. 5)'
            }
        
        # К3 - Эскизы опор (прим. 5 к т. 9)
        if has_poles:
            coefficients['К3'] = {
                'value': 1.0,
                'reason': 'С эскизами опор (прим. 5)'
            }
        
        # К4 - Компьютерные технологии (только для камеральных, ОУ 15г, 15д)
        if stage == 'office' and use_computer:
            coefficients['К4'] = {
                'value': 1.20,
                'reason': 'Компьютерные технологии (ОУ 15г, 15д)'
            }
        
        # Кобн - Обновление существующего плана
        if update_mode:
            coefficients['Кобн'] = {
                'value': 0.50,
                'reason': 'Обновление существующего плана'
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
