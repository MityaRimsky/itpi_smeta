"""
Тесты для проверки расчетов смет на основе эталонных данных
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List

from tests.fixtures.expected_results import (
    ALL_ESTIMATES,
    KASHIRSKAYA_GRES,
    OMSK,
    AMUR,
    MOSCOW,
    NIZHNEKAMSK,
    MAGADAN,
    K1_RULES,
    K2_RULES,
    K3_RULES,
    ADDON_RULES
)


def round_cost(value: float, decimals: int = 2) -> float:
    """Округление стоимости до копеек"""
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def calculate_line_cost(base_price: float, quantity: float, k1: float, k2: float, k3: float) -> float:
    """Расчет стоимости строки: цена × количество × K1 × K2 × K3"""
    return round_cost(base_price * quantity * k1 * k2 * k3)


class TestLineCostCalculations:
    """Тесты расчета стоимости отдельных строк"""
    
    @pytest.mark.parametrize("estimate", ALL_ESTIMATES, ids=lambda e: e["name"])
    def test_field_works_costs(self, estimate: Dict[str, Any]):
        """Проверка расчета полевых работ"""
        for work in estimate.get("field_works", []):
            calculated = calculate_line_cost(
                work["base_price"],
                work["quantity"],
                work["K1"],
                work["K2"],
                work["K3"]
            )
            expected = work["expected_cost"]
            
            # Допустимая погрешность 0.5% (из-за округлений)
            tolerance = max(expected * 0.005, 1.0)
            
            assert abs(calculated - expected) <= tolerance, (
                f"Смета: {estimate['name']}\n"
                f"Работа: {work['name'][:50]}...\n"
                f"Расчет: {work['base_price']} × {work['quantity']} × "
                f"{work['K1']} × {work['K2']} × {work['K3']} = {calculated}\n"
                f"Ожидалось: {expected}\n"
                f"Разница: {abs(calculated - expected)}"
            )
    
    @pytest.mark.parametrize("estimate", ALL_ESTIMATES, ids=lambda e: e["name"])
    def test_office_works_costs(self, estimate: Dict[str, Any]):
        """Проверка расчета камеральных работ"""
        for work in estimate.get("office_works", []):
            calculated = calculate_line_cost(
                work["base_price"],
                work["quantity"],
                work["K1"],
                work["K2"],
                work["K3"]
            )
            expected = work["expected_cost"]
            
            tolerance = max(expected * 0.005, 1.0)
            
            assert abs(calculated - expected) <= tolerance, (
                f"Смета: {estimate['name']}\n"
                f"Работа: {work['name'][:50]}...\n"
                f"Расчет: {work['base_price']} × {work['quantity']} × "
                f"{work['K1']} × {work['K2']} × {work['K3']} = {calculated}\n"
                f"Ожидалось: {expected}\n"
                f"Разница: {abs(calculated - expected)}"
            )


class TestCoefficientSelection:
    """Тесты выбора коэффициентов по условиям"""
    
    def test_k1_territory_type_industrial(self):
        """K1 для промпредприятия = 1.75"""
        assert K1_RULES["territory_type"]["промпредприятие"] == 1.75
        
        # Проверяем в реальных сметах
        for work in KASHIRSKAYA_GRES["field_works"]:
            if "пром.предприятие" in work["name"].lower() or "промпредприятие" in work["name"].lower():
                assert work["K1"] == 1.75, f"Ожидался K1=1.75 для {work['name']}"
    
    def test_k1_territory_type_built_up(self):
        """K1 для застроенной территории = 1.5"""
        assert K1_RULES["territory_type"]["застроенная"] == 1.5
        
        # Проверяем в смете Нижнекамск
        for work in NIZHNEKAMSK["field_works"]:
            if "застроенная" in work["name"].lower():
                assert work["K1"] == 1.5, f"Ожидался K1=1.5 для {work['name']}"
    
    def test_k1_small_area(self):
        """K1 для небольших участков до 5 га = 1.55"""
        assert K1_RULES["small_area_up_to_5ha"] == 1.55
        
        # Проверяем в смете Москва
        for work in MOSCOW["field_works"]:
            if "небольшие участки" in work["name"].lower():
                assert work["K1"] == 1.55, f"Ожидался K1=1.55 для {work['name']}"
    
    def test_k1_update_mode(self):
        """K1 для обновления = 0.5"""
        assert K1_RULES["update_mode"] == 0.5
        
        # Проверяем в смете АМУР
        for work in AMUR["field_works"]:
            if "обновление" in work["name"].lower():
                assert work["K2"] == 0.5, f"Ожидался K2=0.5 (обновление) для {work['name']}"
    
    def test_k2_computer_tech(self):
        """K2 для компьютерных технологий = 1.2"""
        assert K2_RULES["computer_tech"] == 1.2
    
    def test_k2_color_plan(self):
        """K2 для плана в цвете = 1.1"""
        assert K2_RULES["color_plan"] == 1.1
    
    def test_k2_satellite_systems(self):
        """K2 для спутниковых систем = 1.3"""
        assert K1_RULES["satellite_systems"] == 1.3
        
        # Проверяем в сметах
        for work in OMSK["field_works"]:
            if "спутников" in work["name"].lower() or "2 разряд" in work["name"].lower():
                assert work["K2"] == 1.3, f"Ожидался K2=1.3 для {work['name']}"
    
    def test_k3_special_regime(self):
        """K3 для спецрежима = 1.25"""
        assert K3_RULES["special_regime"] == 1.25
        
        # Проверяем в смете Каширская ГРЭС - спецрежим применяется к топосъемке
        for work in KASHIRSKAYA_GRES["field_works"]:
            if "специальный режим" in work["name"].lower() and "топографического" in work["name"].lower():
                assert work["K3"] == 1.25, f"Ожидался K3=1.25 для {work['name']}"


class TestAddonCalculations:
    """Тесты расчета надбавок"""
    
    def test_internal_transport_rates(self):
        """Проверка ставок внутреннего транспорта"""
        # До 5 км, стоимость > 150000 = 3.75%
        assert ADDON_RULES["internal_transport"][(0, 5)][(150000, None)] == 0.0375
        
        # 15-20 км, стоимость < 30000 = 16.25%
        assert ADDON_RULES["internal_transport"][(15, 20)][(0, 30000)] == 0.1625
    
    def test_org_liquidation_base_rate(self):
        """Базовая ставка организации/ликвидации = 6%"""
        assert ADDON_RULES["org_liquidation"]["base_rate"] == 0.06
    
    def test_org_liquidation_coefficients(self):
        """Коэффициенты организации/ликвидации по стоимости"""
        coeffs = ADDON_RULES["org_liquidation"]["coefficients"]
        assert coeffs[(0, 30000)] == 2.5
        assert coeffs[(30000, 75000)] == 2.0
        assert coeffs[(75000, 150000)] == 1.5
        assert coeffs[(150000, None)] == 1.0
    
    def test_seasonal_rates(self):
        """Ставки сезонного удорожания"""
        assert ADDON_RULES["seasonal"][(4, 5.5)] == 0.20
        assert ADDON_RULES["seasonal"][(6, 7.5)] == 0.30
        assert ADDON_RULES["seasonal"][(8, 9.5)] == 0.40
    
    def test_regional_rates(self):
        """Ставки районного удорожания"""
        assert ADDON_RULES["regional"][1.15] == 0.08
        assert ADDON_RULES["regional"][1.70] == 0.35
    
    def test_mountain_rates(self):
        """Ставки для горных районов"""
        assert ADDON_RULES["mountain"][(1500, 1700)] == 0.10
        assert ADDON_RULES["mountain"][(2000, 3000)] == 0.20
    
    def test_intermediate_materials_rate(self):
        """Ставка промежуточных материалов = 10%"""
        assert ADDON_RULES["intermediate_materials"] == 0.10
    
    def test_special_regime_rate(self):
        """Ставка спецрежима = 25%"""
        assert ADDON_RULES["special_regime"] == 0.25


class TestTotalCalculations:
    """Тесты итоговых расчетов"""
    
    @pytest.mark.parametrize("estimate", ALL_ESTIMATES, ids=lambda e: e["name"])
    def test_total_sbc_2001(self, estimate: Dict[str, Any]):
        """Проверка итога в ценах СБЦ 2001"""
        field_total = estimate.get("field_total", 0)
        office_total = estimate.get("office_total", 0)
        addons_total = estimate.get("addons_total", 0)
        
        calculated_total = field_total + office_total + addons_total
        expected_total = estimate["total_sbc_2001"]
        
        # Допустимая погрешность 1% (из-за накопления округлений)
        tolerance = expected_total * 0.01
        
        assert abs(calculated_total - expected_total) <= tolerance, (
            f"Смета: {estimate['name']}\n"
            f"Полевые: {field_total}\n"
            f"Камеральные: {office_total}\n"
            f"Надбавки: {addons_total}\n"
            f"Расчет: {calculated_total}\n"
            f"Ожидалось: {expected_total}\n"
            f"Разница: {abs(calculated_total - expected_total)}"
        )
    
    @pytest.mark.parametrize("estimate", ALL_ESTIMATES, ids=lambda e: e["name"])
    def test_total_with_index(self, estimate: Dict[str, Any]):
        """Проверка итога с индексом"""
        total_sbc = estimate["total_sbc_2001"]
        index = estimate["index_2025"]
        
        calculated = round_cost(total_sbc * index)
        expected = estimate["total_with_index"]
        
        # Допустимая погрешность 1%
        tolerance = expected * 0.01
        
        assert abs(calculated - expected) <= tolerance, (
            f"Смета: {estimate['name']}\n"
            f"СБЦ 2001: {total_sbc}\n"
            f"Индекс: {index}\n"
            f"Расчет: {calculated}\n"
            f"Ожидалось: {expected}\n"
            f"Разница: {abs(calculated - expected)}"
        )


class TestSpecificEstimates:
    """Тесты для конкретных смет"""
    
    def test_kashirskaya_gres_special_regime(self):
        """Каширская ГРЭС: спецрежим применяется к полевым работам"""
        params = KASHIRSKAYA_GRES["params"]
        assert params["special_regime"] == True
        assert params["territory_type"] == "промпредприятие"
        
        # Проверяем K3=1.25 для топосъемки со спецрежимом
        for work in KASHIRSKAYA_GRES["field_works"]:
            if "специальный режим" in work["name"].lower() and "топографического" in work["name"].lower():
                assert work["K3"] == 1.25
    
    def test_omsk_seasonal_and_regional(self):
        """Омск: сезонное 30% + районное 8%"""
        params = OMSK["params"]
        assert params["unfavorable_months"] == 7  # 30%
        assert params["salary_coeff"] == 1.15  # 8%
    
    def test_amur_update_mode(self):
        """АМУР: обновление K=0.5"""
        params = AMUR["params"]
        assert params["update_mode"] == True
        
        for work in AMUR["field_works"]:
            if "обновление" in work["name"].lower():
                assert work["K2"] == 0.5
    
    def test_moscow_small_area(self):
        """Москва: небольшие участки до 5 га"""
        params = MOSCOW["params"]
        assert params["small_area"] == True
        assert params["territory_type"] == "застроенная"
    
    def test_nizhnekamsk_intermediate_materials(self):
        """Нижнекамск: промежуточные материалы 10%"""
        params = NIZHNEKAMSK["params"]
        assert params["intermediate_materials"] == True
    
    def test_magadan_far_north(self):
        """Магадан: Крайний Север + горные районы"""
        params = MAGADAN["params"]
        assert params["region_type"] == "far_north"
        assert params["altitude"] == 1600  # 10% за горы
        assert params["salary_coeff"] == 1.70  # 35% районное


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_zero_quantity(self):
        """Нулевое количество = нулевая стоимость"""
        cost = calculate_line_cost(1000, 0, 1.5, 1.2, 1.0)
        assert cost == 0.0
    
    def test_all_coefficients_one(self):
        """Все коэффициенты = 1"""
        cost = calculate_line_cost(1000, 10, 1.0, 1.0, 1.0)
        assert cost == 10000.0
    
    def test_multiple_coefficients(self):
        """Множественные коэффициенты перемножаются"""
        cost = calculate_line_cost(1000, 1, 1.5, 1.2, 1.25)
        expected = 1000 * 1 * 1.5 * 1.2 * 1.25
        assert cost == round_cost(expected)
    
    def test_rounding(self):
        """Проверка округления до копеек"""
        cost = calculate_line_cost(1000, 1, 1.333, 1.0, 1.0)
        assert cost == 1333.0  # Округление до копеек


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
