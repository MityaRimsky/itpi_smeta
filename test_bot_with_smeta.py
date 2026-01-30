"""
Тестовый скрипт для проверки бота с данными из реальной сметы
Отправляет название работ и объем, получает полный расчет
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

# Теперь импортируем
from services.database import DatabaseService  # type: ignore
from services.calculator import CostCalculator  # type: ignore
from services.ai_agent import AIAgent  # type: ignore

# Тестовые данные - работы которые ЕСТЬ в БД
TEST_CASES = [
    {
        "name": "Создание инженерно-топографического плана М 1:500, сечение 0,5м, незастроенная территория",
        "quantity": 92.00,
        "unit": "га",
        "expected": {
            "price_field": 2432.00,
            "base_cost": 223744.00  # 92 * 2432
        }
    },
    {
        "name": "Изыскания новых железных и автомобильных дорог I-II технических категорий",
        "quantity": 2.00,
        "unit": "км",
        "expected": {
            "price_field": 27375.00,
            "base_cost": 54750.00  # 2 * 27375
        }
    },
    {
        "name": "Изыскания новых железных и автомобильных дорог III-IV технических категорий",
        "quantity": 2.00,
        "unit": "км",
        "expected": {
            "price_field": 25902.00,
            "base_cost": 51804.00  # 2 * 25902
        }
    },
    {
        "name": "Изыскания автомобильных дорог V технической категории",
        "quantity": 5.00,
        "unit": "км",
        "expected": {
            "price_field": 13122.00,
            "base_cost": 65610.00  # 5 * 13122
        }
    },
    {
        "name": "Изыскания трасс магистральных трубопроводов",
        "quantity": 10.00,
        "unit": "км",
        "expected": {
            "price_field": 5790.00,
            "base_cost": 57900.00  # 10 * 5790
        }
    },
    {
        "name": "Изыскания трасс воздушных линий электропередачи 35-110 кВ",
        "quantity": 15.00,
        "unit": "км",
        "expected": {
            "price_field": 3440.00,
            "base_cost": 51600.00  # 15 * 3440
        }
    },
    {
        "name": "Плановая опорная сеть 4 класс",
        "quantity": 10.00,
        "unit": "пункт",
        "expected": {
            "price_field": 12740.00,
            "base_cost": 127400.00  # 10 * 12740
        }
    },
    {
        "name": "Плановая опорная сеть 1 разряд",
        "quantity": 5.00,
        "unit": "пункт",
        "expected": {
            "price_field": 8407.00,
            "base_cost": 42035.00  # 5 * 8407
        }
    },
    {
        "name": "Высотная опорная сеть IV класс",
        "quantity": 8.00,
        "unit": "пункт",
        "expected": {
            "price_field": 2463.00,
            "base_cost": 19704.00  # 8 * 2463
        }
    },
    {
        "name": "Создание инженерно-топографического плана М 1:1000, сечение 0,5м, незастроенная территория",
        "quantity": 50.00,
        "unit": "га",
        "expected": {
            "price_field": 936.00,
            "base_cost": 46800.00  # 50 * 936
        }
    },
    {
        "name": "Создание инженерно-топографического плана М 1:2000, сечение 0,5м, незастроенная территория",
        "quantity": 100.00,
        "unit": "га",
        "expected": {
            "price_field": 408.00,
            "base_cost": 40800.00  # 100 * 408
        }
    },
    {
        "name": "Создание инженерно-топографического плана М 1:5000, сечение 0,5м, незастроенная территория",
        "quantity": 200.00,
        "unit": "га",
        "expected": {
            "price_field": 228.00,
            "base_cost": 45600.00  # 200 * 228
        }
    },
    {
        "name": "Создание инженерно-топографического плана М 1:10000, сечение 1,0м, незастроенная территория",
        "quantity": 500.00,
        "unit": "га",
        "expected": {
            "price_field": 121.00,
            "base_cost": 60500.00  # 500 * 121
        }
    },
    {
        "name": "Создание инженерно-топографического плана М 1:500, сечение 0,25м, застроенная территория",
        "quantity": 25.00,
        "unit": "га",
        "expected": {
            "price_field": 2518.00,
            "base_cost": 62950.00  # 25 * 2518
        }
    },
    {
        "name": "Изыскания трасс воздушных линий электропередачи 0,4-20 кВ",
        "quantity": 20.00,
        "unit": "км",
        "expected": {
            "price_field": 1918.00,
            "base_cost": 38360.00  # 20 * 1918
        }
    }
]


async def test_bot_calculation(test_case: dict, test_num: int, total_tests: int):
    """Тестирование расчета для одного случая"""
    
    print("\n" + "="*80)
    print(f"ТЕСТ {test_num}/{total_tests}: {test_case['name'][:55]}...")
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
        
        # 4. Рассчитываем стоимость
        print("4️⃣ Расчет стоимости...")
        calculation = await calculator.calculate(
            work=selected_work,
            quantity=test_case['quantity'],
            coefficient_codes=None,
            addon_codes=None  # Без надбавок для чистого теста
        )
        
        # 5. Проверка результатов
        print("\n📊 РЕЗУЛЬТАТЫ:")
        print(f"   Базовая цена (полевые): {calculation['base_field']:.2f} руб.")
        print(f"   Итоговая стоимость: {calculation['total_cost']:.2f} руб.")
        
        # Проверка ожидаемых значений
        if 'expected' in test_case:
            expected = test_case['expected']
            actual_base = calculation['base_field']
            expected_base = expected['base_cost']
            
            diff = abs(actual_base - expected_base)
            diff_percent = (diff / expected_base * 100) if expected_base > 0 else 0
            
            if diff < 1:
                print(f"   ✅ Расчет ВЕРНЫЙ: {actual_base:.2f} руб.")
                return {"success": True, "diff": 0, "diff_percent": 0}
            else:
                print(f"   ⚠️  РАСХОЖДЕНИЕ:")
                print(f"      Ожидалось: {expected_base:.2f} руб.")
                print(f"      Получено:  {actual_base:.2f} руб.")
                print(f"      Разница:   {diff:.2f} руб. ({diff_percent:.1f}%)")
                return {"success": False, "reason": "mismatch", "diff": diff, "diff_percent": diff_percent}
        
        return {"success": True}
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        return {"success": False, "reason": "error", "error": str(e)}


async def main():
    """Главная функция для запуска всех тестов"""
    
    print("\n" + "="*80)
    print("🤖 ТЕСТИРОВАНИЕ БОТА С РАБОТАМИ ИЗ БД")
    print("="*80)
    
    results = []
    total_tests = len(TEST_CASES)
    
    for i, test_case in enumerate(TEST_CASES, 1):
        result = await test_bot_calculation(test_case, i, total_tests)
        results.append({
            "name": test_case['name'][:45] + "...",
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
    mismatch_count = 0
    not_found_count = 0
    error_count = 0
    
    for i, item in enumerate(results, 1):
        result = item['result']
        if result['success']:
            status = "✅"
            success_count += 1
        elif result.get('reason') == 'not_found':
            status = "❌ НЕ НАЙДЕНО"
            not_found_count += 1
        elif result.get('reason') == 'mismatch':
            status = f"⚠️  РАСХОЖДЕНИЕ {result.get('diff_percent', 0):.1f}%"
            mismatch_count += 1
        else:
            status = "❌ ОШИБКА"
            error_count += 1
            
        print(f"{i:2d}. {status:20s} {item['name']}")
    
    print("\n" + "─"*80)
    print(f"✅ Успешно (точное совпадение): {success_count}/{total_tests}")
    print(f"⚠️  Расхождения в расчетах:      {mismatch_count}/{total_tests}")
    print(f"❌ Не найдено в БД:             {not_found_count}/{total_tests}")
    print(f"❌ Ошибки выполнения:           {error_count}/{total_tests}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
