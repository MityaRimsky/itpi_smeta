"""
Тест бота на основе реальной сметы
Проверяет что все работы из сметы находятся в БД
"""

import asyncio
import os
import sys

# Устанавливаем переменные окружения из bot/.env
env_path = os.path.join(os.path.dirname(__file__), 'bot', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Добавляем bot в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from services.database import DatabaseService  # type: ignore
from services.calculator import CostCalculator  # type: ignore
from services.ai_agent import AIAgent  # type: ignore

# Тестовые данные из реальной сметы
REAL_SMETA_CASES = [
    {
        "name": "Создание инженерно-топографического плана м-ба 1:500, высота сечения рельефа 0,5м (II кат., пром.предприятие) со съемкой подземных коммуникаций, с эскизами опор",
        "quantity": 92.00,
        "unit": "га",
        "expected": {
            "price_field": 4632.00,
            "base_cost": 426144.00  # 92 * 4632
        }
    },
    {
        "name": "Инженерные изыскания трасс железных дорог III-IV категории (II кат.сложности)",
        "quantity": 2.00,
        "unit": "км",
        "expected": {
            "price_field": 25902.00,
            "base_cost": 51804.00  # 2 * 25902
        }
    },
    {
        "name": "Создание инженерно-топографического плана м-ба 1:500 сечение рельефа 0,5 (составление плана в цвете с применением компьютерных технологий)",
        "quantity": 92.00,
        "unit": "га",
        "expected": {
            "price_office": 2558.00,
            "base_cost": 235336.00  # 92 * 2558
        }
    },
    {
        "name": "Стоимость проверки полноты планов в эксплуатирующих организациях",
        "quantity": 6.00,
        "unit": "служба",
        "expected": {
            "price_office": 480.00,
            "base_cost": 2880.00  # 6 * 480
        }
    },
    {
        "name": "Выдача координат и высот исходных пунктов",
        "quantity": 7.00,
        "unit": "пункт",
        "expected": {
            "price_office": 160.00,
            "base_cost": 1120.00  # 7 * 160
        }
    },
    {
        "name": "Инженерно-геологическая рекогносцировка III категория сложности при хорошей проходимости",
        "quantity": 5.00,
        "unit": "км",
        "expected": {
            "price_field": 28.30,
            "base_cost": 141.50  # 5 * 28.30
        }
    },
    {
        "name": "Маршрутные наблюдения",
        "quantity": 5.00,
        "unit": "км",
        "expected": {
            "price_field": 16.30,
            "base_cost": 81.50  # 5 * 16.30
        }
    },
    {
        "name": "Описание точек наблюдений",
        "quantity": 30.00,
        "unit": "точка",
        "expected": {
            "price_field": 10.20,
            "base_cost": 306.00  # 30 * 10.20
        }
    },
]


async def test_real_smeta_work(test_case: dict, test_num: int, total_tests: int):
    """Тестирование одной работы из реальной сметы"""
    
    print("\n" + "="*80)
    print(f"ТЕСТ {test_num}/{total_tests}: {test_case['name'][:60]}...")
    print(f"Объем: {test_case['quantity']} {test_case['unit']}")
    print("="*80)
    
    # Получаем настройки из переменных окружения
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    openrouter_model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    
    # Инициализация сервисов
    db = DatabaseService(supabase_url, supabase_key)
    calculator = CostCalculator(db)
    ai = AIAgent(openrouter_key, openrouter_model)
    
    try:
        # 1. Извлекаем параметры через AI
        print("1️⃣ Извлечение параметров...")
        user_query = f"{test_case['name']} {test_case['quantity']} {test_case['unit']}"
        params = await ai.extract_parameters(user_query)
        
        # 2. Ищем работы в БД
        print("2️⃣ Поиск работ...")
        works = await db.search_works(
            query=params.get("work_type", test_case['name']),
            scale=params.get("scale"),
            category=params.get("category"),
            territory=params.get("territory")
        )
        
        if not works:
            print("   ❌ Работы не найдены!")
            return {"success": False, "reason": "not_found"}
        
        print(f"   ✅ Найдено: {len(works)} работ")
        
        # 3. Выбираем лучшую работу через AI
        print("3️⃣ Выбор работы...")
        selected_work = await ai.select_best_work(user_query, works)
        
        if not selected_work:
            print("   ❌ Не удалось выбрать работу!")
            return {"success": False, "reason": "selection_failed"}
        
        print(f"   ✅ Выбрана: {selected_work.get('name')[:50]}...")
        print(f"   💰 Цена: {selected_work.get('price_field') or selected_work.get('price_office')} руб/{selected_work.get('unit')}")
        
        # 4. Проверка цены
        expected = test_case['expected']
        actual_price = selected_work.get('price_field') or selected_work.get('price_office')
        expected_price = expected.get('price_field') or expected.get('price_office')
        
        if abs(actual_price - expected_price) < 0.01:
            print(f"   ✅ Цена ВЕРНАЯ: {actual_price} руб/{selected_work.get('unit')}")
            return {"success": True}
        else:
            print(f"   ⚠️  РАСХОЖДЕНИЕ В ЦЕНЕ:")
            print(f"      Ожидалось: {expected_price} руб")
            print(f"      Получено:  {actual_price} руб")
            return {"success": False, "reason": "price_mismatch"}
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "reason": "error", "error": str(e)}


async def main():
    """Главная функция для запуска всех тестов"""
    
    print("\n" + "="*80)
    print("🤖 ТЕСТИРОВАНИЕ БОТА НА РЕАЛЬНОЙ СМЕТЕ")
    print("="*80)
    
    results = []
    total_tests = len(REAL_SMETA_CASES)
    
    for i, test_case in enumerate(REAL_SMETA_CASES, 1):
        result = await test_real_smeta_work(test_case, i, total_tests)
        results.append({
            "name": test_case['name'][:50] + "...",
            "result": result
        })
        
        # Пауза между тестами
        if i < total_tests:
            await asyncio.sleep(1)
    
    # Итоговый отчет
    print("\n\n" + "="*80)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("="*80)
    
    success_count = 0
    not_found_count = 0
    price_mismatch_count = 0
    error_count = 0
    
    for i, item in enumerate(results, 1):
        result = item['result']
        if result['success']:
            status = "✅ НАЙДЕНО"
            success_count += 1
        elif result.get('reason') == 'not_found':
            status = "❌ НЕ НАЙДЕНО"
            not_found_count += 1
        elif result.get('reason') == 'price_mismatch':
            status = "⚠️  ЦЕНА НЕ СОВПАДАЕТ"
            price_mismatch_count += 1
        else:
            status = "❌ ОШИБКА"
            error_count += 1
            
        print(f"{i:2d}. {status:20s} {item['name']}")
    
    print("\n" + "─"*80)
    print(f"✅ Найдено и цена верна:     {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
    print(f"⚠️  Найдено, но цена не та:  {price_mismatch_count}/{total_tests}")
    print(f"❌ Не найдено в БД:          {not_found_count}/{total_tests}")
    print(f"❌ Ошибки выполнения:        {error_count}/{total_tests}")
    print("="*80)
    
    # Цель: 100% работ должны быть найдены
    if success_count == total_tests:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    elif success_count + price_mismatch_count == total_tests:
        print("\n✅ Все работы найдены, но есть расхождения в ценах")
    else:
        print(f"\n⚠️  {not_found_count} работ не найдено в БД - нужно добавить!")


if __name__ == "__main__":
    asyncio.run(main())
