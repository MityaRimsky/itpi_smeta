"""
Калькулятор стоимости работ
Рассчитывает стоимость с учетом коэффициентов и надбавок
"""

from typing import Dict, List, Optional
from decimal import Decimal
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
    
    async def calculate(
        self,
        work: Dict,
        quantity: float,
        coefficient_codes: Optional[List[str]] = None,
        addon_codes: Optional[List[str]] = None
    ) -> Dict:
        """
        Рассчитать стоимость работ
        
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
