#!/usr/bin/env python3
"""
Тест нового расчета с полевыми и камеральными работами
"""

import asyncio
import sys
sys.path.insert(0, 'bot')

from decimal import Decimal

# Тестовые данные из сметы НИПИГАЗ
TEST_WORK = {
    'id': 'test-1',
    'work_title': 'Создание инженерно-топографического плана м-ба 1:500, высота сечения рельефа 0,5м (II кат., пром.предприятие) со съемкой подземных коммуникаций, с эскизами опор',
    'unit': 'га',
    'price_field': 4632.0,
    'price_office': 2558.0,
    'table_no': '9',
    'section': 'п. 5'
}

# Параметры из сметы
TEST_PARAMS = {
    'work_type': 'топографическая съемка',
    'quantity': 92.0,
    'territory_type': 'промпредприятие',
    'has_underground_comms': True,
    'has_pole_sketches': True,
    'use_computer': True,
    'work_stage': 'обе'
}

# Ожидаемые результаты из сметы
EXPECTED = {
    'field_base': 92 * 4632,  # 426,144
    'field_k1': 1.75,  # промпредприятие
    'field_k2': 1.30,  # подземные коммуникации
    'field_k3': 1.00,  # эскизы опор
    'field_total': 969477.60,  # 92 × 4632 × 1.75 × 1.30 × 1.00
    
    'office_base': 92 * 2558,  # 235,336
    'office_k1': 1.75,  # промпредприятие
    'office_k2': 1.30,  # подземные коммуникации
    'office_k3': 1.00,  # эскизы опор
    'office_k4': 1.20,  # компьютерные технологии
    'office_total': 642467.28,  # 92 × 2558 × 1.75 × 1.30 × 1.20
    
    'total_works': 1611944.88  # полевые + камеральные
}


class MockDBService:
    """Мок для сервиса БД"""
    async def get_coefficients(self, codes=None):
        return []
    
    async def get_addons(self, codes=None):
        return []


async def test_calculation():
    """Тест расчета"""
    from services.calculator import CostCalculator
    
    db = MockDBService()
    calc = CostCalculator(db)
    
    print("=" * 70)
    print("ТЕСТ НОВОГО РАСЧЕТА С ПОЛЕВЫМИ И КАМЕРАЛЬНЫМИ РАБОТАМИ")
    print("=" * 70)
    print()
    
    # Выполняем расчет
    result = await calc.calculate_full(
        work=TEST_WORK,
        quantity=TEST_PARAMS['quantity'],
        params=TEST_PARAMS,
        work_stage='обе'
    )
    
    print(f"📋 Работа: {TEST_WORK['work_title']}")
    print(f"📏 Объем: {TEST_PARAMS['quantity']} {TEST_WORK['unit']}")
    print()
    
    # Проверяем полевые работы
    print("🏕 ПОЛЕВЫЕ РАБОТЫ:")
    fc = result['field_calculation']
    print(f"   Базовая цена: {fc['base_price']:,.2f} руб/{TEST_WORK['unit']}")
    print(f"   Базовая стоимость: {fc['base_cost']:,.2f} руб")
    print(f"   Ожидание: {EXPECTED['field_base']:,.2f} руб")
    
    if fc['coefficients']:
        print("   Коэффициенты:")
        for code, info in fc['coefficients'].items():
            print(f"      {code}: {info['value']} ({info['reason']})")
    
    print(f"   Итого полевые: {fc['total']:,.2f} руб")
    print(f"   Ожидание: {EXPECTED['field_total']:,.2f} руб")
    
    field_ok = abs(fc['total'] - EXPECTED['field_total']) < 0.01
    print(f"   {'✅ OK' if field_ok else '❌ ОШИБКА'}")
    print()
    
    # Проверяем камеральные работы
    print("🖥 КАМЕРАЛЬНЫЕ РАБОТЫ:")
    oc = result['office_calculation']
    print(f"   Базовая цена: {oc['base_price']:,.2f} руб/{TEST_WORK['unit']}")
    print(f"   Базовая стоимость: {oc['base_cost']:,.2f} руб")
    print(f"   Ожидание: {EXPECTED['office_base']:,.2f} руб")
    
    if oc['coefficients']:
        print("   Коэффициенты:")
        for code, info in oc['coefficients'].items():
            print(f"      {code}: {info['value']} ({info['reason']})")
    
    print(f"   Итого камеральные: {oc['total']:,.2f} руб")
    print(f"   Ожидание: {EXPECTED['office_total']:,.2f} руб")
    
    office_ok = abs(oc['total'] - EXPECTED['office_total']) < 0.01
    print(f"   {'✅ OK' if office_ok else '❌ ОШИБКА'}")
    print()
    
    # Итого
    total_works = fc['total'] + oc['total']
    print("━" * 70)
    print(f"✅ ИТОГО (полевые + камеральные): {total_works:,.2f} руб")
    print(f"   Ожидание: {EXPECTED['total_works']:,.2f} руб")
    
    total_ok = abs(total_works - EXPECTED['total_works']) < 0.01
    print(f"   {'✅ OK' if total_ok else '❌ ОШИБКА'}")
    print()
    
    # Надбавки
    if result['addons_applied']:
        print("➕ НАДБАВКИ:")
        for addon in result['addons_applied']:
            print(f"   {addon['name']}: {addon['amount']:,.2f} руб ({addon['rate']*100}%)")
    
    print()
    print(f"💰 ИТОГО С НАДБАВКАМИ: {result['total_cost']:,.2f} руб")
    print()
    
    # Общий результат
    all_ok = field_ok and office_ok and total_ok
    print("=" * 70)
    if all_ok:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("❌ ЕСТЬ ОШИБКИ В РАСЧЕТАХ")
    print("=" * 70)
    
    return all_ok


async def test_ai_agent():
    """Тест AI агента"""
    from services.ai_agent import AIAgent
    
    print()
    print("=" * 70)
    print("ТЕСТ ОПРЕДЕЛЕНИЯ КОЭФФИЦИЕНТОВ")
    print("=" * 70)
    print()
    
    ai = AIAgent("dummy", "dummy")
    
    # Тест для полевых работ
    coeffs_field, details_field = ai.determine_coefficients(TEST_PARAMS, 'field')
    print("Полевые работы:")
    for code, info in details_field.items():
        print(f"   {code}: {info['value']} - {info['reason']}")
    
    # Проверяем
    expected_field = {'К1': 1.75, 'К2': 1.30}
    field_ok = all(
        details_field.get(k, {}).get('value') == v 
        for k, v in expected_field.items()
    )
    print(f"   {'✅ OK' if field_ok else '❌ ОШИБКА'}")
    print()
    
    # Тест для камеральных работ
    coeffs_office, details_office = ai.determine_coefficients(TEST_PARAMS, 'office')
    print("Камеральные работы:")
    for code, info in details_office.items():
        print(f"   {code}: {info['value']} - {info['reason']}")
    
    # Проверяем
    expected_office = {'К1': 1.75, 'К2': 1.30, 'К4': 1.20}
    office_ok = all(
        details_office.get(k, {}).get('value') == v 
        for k, v in expected_office.items()
    )
    print(f"   {'✅ OK' if office_ok else '❌ ОШИБКА'}")
    print()
    
    return field_ok and office_ok


async def main():
    calc_ok = await test_calculation()
    ai_ok = await test_ai_agent()
    
    print()
    print("=" * 70)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("=" * 70)
    
    if calc_ok and ai_ok:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        print("❌ ЕСТЬ ОШИБКИ")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
