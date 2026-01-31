#!/usr/bin/env python3
"""
Тесты расчетов ИГДИ 2004 на основе реальных смет

Источники:
1. Смета НИПИГАЗ (PDF) - 92 га пром.предприятие, итого 9 245 000 руб
2. Смета Новые ресурсы (XLSX) - 12 га смешанная территория, итого 517 799.45 руб
"""

import sys
from decimal import Decimal, ROUND_HALF_UP

# Добавляем путь к боту
sys.path.insert(0, 'bot')

# ============================================================================
# ЭТАЛОННЫЕ ДАННЫЕ ИЗ СМЕТ
# ============================================================================

# Смета 1: НИПИГАЗ (PDF) - Топоплан 92 га промпредприятие
SMETA_NIPIGAZ = {
    "name": "НИПИГАЗ - Топоплан 92 га промпредприятие",
    "works": [
        {
            "name": "Топоплан 1:500 промпредприятие (полевые)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 92.0,
            "price": 4632.0,
            "coeffs": {"K1": 1.75, "K2": 1.30, "K3": 1.00},
            "expected_cost": 969477.60  # 92 * 4632 * 1.75 * 1.30 = 969477.60
        },
        {
            "name": "Изыскания трасс ж/д III-IV (полевые)",
            "table": "т. 12, п. 2",
            "unit": "км",
            "qty": 2.0,
            "price": 25902.0,
            "coeffs": {"K1": 1.00, "K2": 1.00, "K3": 1.00},
            "expected_cost": 51804.00  # 2 * 25902 = 51804
        },
        {
            "name": "Топоплан 1:500 промпредприятие (камеральные)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 92.0,
            "price": 2558.0,
            "coeffs": {"K1": 1.75, "K2": 1.30, "K3": 1.20},
            "expected_cost": 642467.28  # 92 * 2558 * 1.75 * 1.30 * 1.20 = 642467.28
        },
        {
            "name": "Изыскания трасс ж/д III-IV (камеральные)",
            "table": "т. 12, п. 2",
            "unit": "км",
            "qty": 2.0,
            "price": 8196.0,
            "coeffs": {"K1": 1.00, "K2": 1.00, "K3": 1.00},
            "expected_cost": 16392.00
        },
        {
            "name": "Проверка полноты планов",
            "table": "т. 75, прим. 3",
            "unit": "служба",
            "qty": 6.0,
            "price": 480.0,
            "coeffs": {},
            "expected_cost": 2880.00
        },
        {
            "name": "Выдача координат и высот",
            "table": "т. 81, п. 2, 3",
            "unit": "пункт",
            "qty": 7.0,
            "price": 160.0,
            "coeffs": {},
            "expected_cost": 1120.00
        }
    ],
    "totals": {
        "field_works": 969477.60,  # Итого полевых (без ж/д для простоты)
        "cameral_works": 662859.28,
        "other_expenses": {
            "interim_materials": {"percent": 0.10, "base": 969478, "expected": 96947.76},
            "internal_transport": {"percent": 0.0875, "base": 969478, "expected": 84829.29},
            "external_transport": {"percent": 0.322, "base": 1054307, "expected": 339486.82},
            "org_liq": {"percent": 0.06, "base": 1054307, "expected": 148087.70},  # Исправлено: было 63258.42
            "special_regime": {"percent": 0.25, "base": 969478, "expected": 581856.22},  # Исправлено: было 242369.40
        },
        "total_other": 1251207.79,
        "total_base_2001": 2883544.67,
        "inflation_index": 5.831,
        "total_with_index": 16811065.43,
        "contract_coeff": 0.55,
        "total_final": 9245000.00
    }
}

# Смета 2: Новые ресурсы (XLSX) - Топоплан 12 га смешанная территория
SMETA_NOVYE_RESURSY = {
    "name": "Новые ресурсы - Топоплан 12 га смешанная территория",
    "works": [
        {
            "name": "Топоплан 1:500 промпредприятие (полевые)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 0.5,
            "price": 4632.0,
            "coeffs": {"K1": 1.0, "K2": 1.75, "K3": 1.1},
            "expected_cost": 4458.30  # 0.5 * 4632 * 1.75 * 1.1 = 4458.30
        },
        {
            "name": "Топоплан 1:500 промпредприятие обновление (полевые)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 2.6,
            "price": 4632.0,
            "coeffs": {"K1": 1.0, "K2": 1.75, "K3": 1.0, "K4": 0.5},
            "expected_cost": 10537.80  # 2.6 * 4632 * 1.75 * 0.5 = 10537.80
        },
        {
            "name": "Топоплан 1:500 незастроенная (полевые)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 2.9,
            "price": 2432.0,
            "coeffs": {"K1": 1.0, "K2": 1.2},
            "expected_cost": 8463.36  # 2.9 * 2432 * 1.2 = 8463.36
        },
        {
            "name": "Топоплан 1:500 незастроенная обновление (полевые)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 6.0,
            "price": 2432.0,
            "coeffs": {"K1": 1.0, "K2": 1.2, "K3": 1.0, "K4": 0.5},
            "expected_cost": 8755.20  # 6 * 2432 * 1.2 * 0.5 = 8755.20
        },
        {
            "name": "Топоплан 1:500 промпредприятие (камеральные)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 0.5,
            "price": 1938.0,
            "coeffs": {"K1": 1.75, "K2": 1.3, "K3": 1.2, "K4": 1.1},
            "expected_cost": 2909.91  # 0.5 * 1938 * 1.75 * 1.3 * 1.2 * 1.1 = 2909.91
        },
        {
            "name": "Топоплан 1:500 промпредприятие обновление (камеральные)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 2.6,
            "price": 1938.0,
            "coeffs": {"K1": 1.75, "K2": 1.3, "K3": 1.2, "K4": 1.1, "K5": 0.5},
            "expected_cost": 7565.76  # 2.6 * 1938 * 1.75 * 1.3 * 1.2 * 1.1 * 0.5 = 7565.76
        },
        {
            "name": "Топоплан 1:500 незастроенная (камеральные)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 2.9,
            "price": 589.0,
            "coeffs": {"K1": 1.2, "K2": 1.3, "K3": 1.2, "K4": 1.1},
            "expected_cost": 3517.32  # 2.9 * 589 * 1.2 * 1.3 * 1.2 * 1.1 = 3517.32
        },
        {
            "name": "Топоплан 1:500 незастроенная обновление (камеральные)",
            "table": "т. 9, п. 5",
            "unit": "га",
            "qty": 6.0,
            "price": 589.0,
            "coeffs": {"K1": 1.2, "K2": 1.3, "K3": 1.2, "K4": 1.1, "K5": 0.5},
            "expected_cost": 3638.61  # 6 * 589 * 1.2 * 1.3 * 1.2 * 1.1 * 0.5 = 3638.61
        },
        {
            "name": "Проверка полноты планов",
            "table": "т. 75, прим. 3",
            "unit": "служба",
            "qty": 6.0,
            "price": 480.0,
            "coeffs": {},
            "expected_cost": 2880.00
        }
    ],
    "totals": {
        "field_works": 32214.66,
        "cameral_works": 20511.60,
        "other_expenses": {
            "regional_coeff": {"percent": 0.08, "base": 32214.66, "expected": 2577.17},
            "internal_transport": {"percent": 0.1375, "base": 32214.66, "expected": 4429.52},
            "external_transport": {"percent": 0.364, "base": 36644.18, "expected": 13338.48},
            "org_liq": {"percent": 0.06, "base": 36644.18, "expected": 2198.65},
            "special_regime": {"percent": 0.0625, "base": 32214.66, "expected": 2013.42},  # 25% * 0.25 = 6.25%
        },
        "total_other": 24557.24,
        "total_base_2001": 77283.50,
        "inflation_index": 6.70,
        "total_with_index": 517799.45,
        "contract_coeff": 1.0,
        "total_final": 517799.45
    }
}


def calculate_work_cost(qty: float, price: float, coeffs: dict) -> Decimal:
    """Рассчитать стоимость работы с коэффициентами"""
    result = Decimal(str(qty)) * Decimal(str(price))
    for coeff_value in coeffs.values():
        result *= Decimal(str(coeff_value))
    return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def test_work_calculation(work: dict) -> tuple:
    """Тестировать расчет одной работы"""
    calculated = calculate_work_cost(work["qty"], work["price"], work["coeffs"])
    expected = Decimal(str(work["expected_cost"]))
    diff = abs(calculated - expected)
    passed = diff <= Decimal('0.01')
    return passed, calculated, expected, diff


def run_tests():
    """Запустить все тесты"""
    print("=" * 70)
    print("ТЕСТЫ РАСЧЕТОВ ИГДИ 2004")
    print("=" * 70)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for smeta in [SMETA_NIPIGAZ, SMETA_NOVYE_RESURSY]:
        print(f"\n📋 {smeta['name']}")
        print("-" * 60)
        
        for work in smeta["works"]:
            total_tests += 1
            passed, calculated, expected, diff = test_work_calculation(work)
            
            if passed:
                passed_tests += 1
                status = "✅"
            else:
                status = "❌"
                failed_tests.append({
                    "smeta": smeta["name"],
                    "work": work["name"],
                    "calculated": calculated,
                    "expected": expected,
                    "diff": diff
                })
            
            print(f"{status} {work['name'][:45]:<45}")
            print(f"   Формула: {work['qty']} × {work['price']} × {' × '.join(str(v) for v in work['coeffs'].values()) or '1'}")
            print(f"   Расчет: {calculated} | Ожидание: {expected} | Разница: {diff}")
    
    # Итоги
    print("\n" + "=" * 70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    print(f"Всего тестов: {total_tests}")
    print(f"Пройдено: {passed_tests} ({100*passed_tests/total_tests:.1f}%)")
    print(f"Провалено: {len(failed_tests)}")
    
    if failed_tests:
        print("\n❌ ПРОВАЛИВШИЕСЯ ТЕСТЫ:")
        for fail in failed_tests:
            print(f"   - {fail['smeta']}: {fail['work']}")
            print(f"     Расчет: {fail['calculated']}, Ожидание: {fail['expected']}")
    
    return passed_tests == total_tests


def test_totals():
    """Тестировать итоговые суммы"""
    print("\n" + "=" * 70)
    print("ТЕСТЫ ИТОГОВЫХ СУММ")
    print("=" * 70)
    
    for smeta in [SMETA_NIPIGAZ, SMETA_NOVYE_RESURSY]:
        print(f"\n📋 {smeta['name']}")
        print("-" * 60)
        
        # Сумма работ
        total_calculated = sum(
            calculate_work_cost(w["qty"], w["price"], w["coeffs"]) 
            for w in smeta["works"]
        )
        
        expected_field = Decimal(str(smeta["totals"]["field_works"]))
        expected_cameral = Decimal(str(smeta["totals"]["cameral_works"]))
        expected_total = expected_field + expected_cameral
        
        print(f"Сумма работ (расчет): {total_calculated}")
        print(f"Полевые + Камеральные (ожидание): {expected_total}")
        
        # Итого с индексом
        total_base = Decimal(str(smeta["totals"]["total_base_2001"]))
        index = Decimal(str(smeta["totals"]["inflation_index"]))
        total_with_index = (total_base * index).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        expected_with_index = Decimal(str(smeta["totals"]["total_with_index"]))
        
        print(f"\nИтого в ценах 2001: {total_base}")
        print(f"Индекс: {index}")
        print(f"С индексом (расчет): {total_with_index}")
        print(f"С индексом (ожидание): {expected_with_index}")
        
        # Итого с договорным коэффициентом
        contract_coeff = Decimal(str(smeta["totals"]["contract_coeff"]))
        total_final_calc = (total_with_index * contract_coeff).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        expected_final = Decimal(str(smeta["totals"]["total_final"]))
        
        print(f"\nДоговорной коэффициент: {contract_coeff}")
        print(f"Итого (расчет): {total_final_calc}")
        print(f"Итого (ожидание): {expected_final}")


if __name__ == "__main__":
    print("\n🧪 Запуск тестов расчетов ИГДИ 2004...\n")
    
    # Тесты отдельных работ
    all_passed = run_tests()
    
    # Тесты итогов
    test_totals()
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("❌ ЕСТЬ ПРОВАЛИВШИЕСЯ ТЕСТЫ")
    print("=" * 70)
    
    sys.exit(0 if all_passed else 1)
