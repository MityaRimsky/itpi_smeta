# Структура базы данных для системы расчета смет

## Обзор

База данных спроектирована для хранения нормативов, расценок, коэффициентов и расчета смет инженерных изысканий на основе СБЦ (Справочников базовых цен).

## Основные таблицы

### 1. norm_docs - Нормативные документы
Реестр нормативных документов (СБЦ, расценки).

**Ключевые поля:**
- `code` - уникальный код документа (например, `SBC_IGDI_2004`)
- `title` - полное название документа
- `base_date` - базисный уровень цен (обычно 01.01.2001)
- `is_active` - активен ли документ

**Пример:**
```sql
{
  "code": "SBC_IGDI_2004",
  "title": "СБЦ на инженерные изыскания для строительства. Инженерно-геодезические изыскания",
  "base_date": "2001-01-01"
}
```

### 2. norm_items - Расценки
Основные расценки из таблиц СБЦ. Это то, что агент должен "находить" по названию работ.

**Ключевые поля:**
- `doc_id` - ссылка на нормативный документ
- `table_no` - номер таблицы (например, 9)
- `section` - параграф (§5)
- `work_title` - название работы для поиска
- `unit` - единица измерения (га, км, пункт, м)
- `price_field` / `price_office` - цены полевых/камеральных работ
- `params` - JSON с параметрами (масштаб, категория, высота сечения)
- `search_text` - tsvector для полнотекстового поиска
- `usage_count` / `popularity_score` - для ранжирования результатов

**Пример:**
```sql
{
  "table_no": 9,
  "section": "§5",
  "work_title": "Создание инженерно-топографического плана м-ба 1:500, высота сечения рельефа 0,5м (II кат., пром.предприятие)",
  "unit": "га",
  "price_field": 4632,
  "price_office": 2558,
  "params": {
    "scale": "1:500",
    "height_section": 0.5,
    "category": "II",
    "territory_type": "промпредприятие"
  }
}
```

### 3. norm_addons - Добавочные начисления
Фиксированные суммы, проценты или начисления за единицу.

**Типы расчета (calc_type):**
- `fixed` - фиксированная сумма (480 руб за проверку)
- `per_unit` - за единицу (160 руб/пункт)
- `percent` - процент (6% от базы)

**К чему применяется (base_type):**
- `field` - к полевым работам
- `office` - к камеральным работам
- `field_plus_office` - к сумме полевых и камеральных
- `field_plus_internal` - к полевым + внутренний транспорт
- `subtotal` - к промежуточному итогу

**Пример:**
```sql
{
  "code": "ORG_LIQ_6PCT",
  "name": "Организация и ликвидация работ на объекте",
  "calc_type": "percent",
  "value": 0.06,
  "base_type": "field_plus_internal"
}
```

### 4. norm_coeffs - Коэффициенты
Множители для расчета стоимости.

**К чему применяется (apply_to):**
- `field` - к полевым работам
- `office` - к камеральным работам
- `total` - к итоговой сумме
- `price` - к базовой цене (до умножения на объем)

**Пример:**
```sql
{
  "code": "SPECIAL_REGIME_1_25",
  "name": "Спецрежим территории 1.25 (25%)",
  "value": 1.25,
  "apply_to": "field"
}
```

### 5. projects - Проекты
Группировка смет по проектам.

**Статусы:**
- `draft` - черновик
- `in_progress` - в работе
- `completed` - завершен
- `archived` - архивирован

### 6. estimates - Сметы (шапка)
Документ сметы с итоговыми суммами.

**Ключевые поля:**
- `project_id` - ссылка на проект
- `doc_id` - используемый норматив
- `total_field` - итого полевые работы
- `total_office` - итого камеральные работы
- `total_final` - итоговая стоимость с коэффициентами

**Статусы:**
- `draft` - черновик
- `final` - финальная версия
- `approved` - утверждена
- `archived` - архивирована

### 7. estimate_lines - Строки сметы
Детальные строки расчета с обоснованиями.

**Ключевые поля:**
- `estimate_id` - ссылка на смету
- `line_no` - номер строки
- `norm_item_id` - выбранная расценка
- `qty` - объем работ
- `applied_coeffs` - примененные коэффициенты (JSON массив)
- `applied_addons` - примененные надбавки (JSON массив)
- `calc_breakdown` - детальная раскладка расчета
- `justification` - обоснование (табл/пункт/примечание)
- `confidence` - уверенность AI в подборе нормы (0-1)

**Пример calc_breakdown:**
```json
{
  "base_field": 969477.60,
  "base_office": 662859.28,
  "coeffs_applied": [
    {"code": "K1", "value": 1.75, "result": 1696585.80},
    {"code": "K2", "value": 1.30, "result": 2205561.54}
  ],
  "addons_applied": [
    {"code": "ORG_LIQ_6PCT", "base": 1054307, "result": 63258.42}
  ],
  "total": 2883544.67
}
```

### 8. estimate_templates - Шаблоны смет
Готовые шаблоны для быстрого создания смет.

### 9. template_sections - Разделы шаблонов
Строки шаблонов с параметрами по умолчанию.

### 10. inflation_indices - Индексы изменения стоимости
Коэффициенты пересчета из базисного уровня в текущие цены.

**Пример:**
```sql
{
  "period_year": 2024,
  "period_quarter": 1,
  "index_value": 5.83,
  "work_type": "ИГДИ",
  "source_document": "Письмо Минстроя России от 07.03.2024 N 13023-ИФ/09"
}
```

### 11. regional_coeffs - Районные коэффициенты
Коэффициенты к зарплате и итогу сметы по регионам.

**Пример:**
```sql
{
  "region_name": "Республика Татарстан",
  "region_code": "RU-TA",
  "salary_coeff": 1.15,
  "estimate_coeff": 1.08
}
```

## Индексы и оптимизация

### Полнотекстовый поиск
Для `norm_items` создан триггер, автоматически обновляющий `search_text`:
- Вес A: название работы (`work_title`)
- Вес B: примечания (`notes`)
- Вес C: параметры (`params`)

### Индексы для поиска
- GIN индекс на `search_text` для полнотекстового поиска
- GIN индекс на `work_title` с pg_trgm для нечеткого поиска
- Индекс на `popularity_score` для ранжирования

### Популярность расценок
Триггер автоматически увеличивает `usage_count` и `popularity_score` при добавлении строки в смету.

## Триггеры

1. **update_norm_items_search_text** - обновление tsvector для поиска
2. **increment_norm_item_usage** - увеличение счетчика использования
3. **update_*_updated_at** - автоматическое обновление `updated_at`

## Логика расчета сметы

### Порядок применения коэффициентов и надбавок:

1. **Базовая стоимость:**
   ```
   base_cost_field = qty × price_field
   base_cost_office = qty × price_office
   ```

2. **Применение коэффициентов к ценам (apply_to = 'price'):**
   ```
   price_field = price_field × K1 × K2 × ...
   ```

3. **Применение коэффициентов к полевым/камеральным (apply_to = 'field'/'office'):**
   ```
   cost_field = base_cost_field × K1 × K2 × ...
   cost_office = base_cost_office × K1 × K2 × ...
   ```

4. **Добавочные начисления (addons):**
   - Внутренний транспорт: `% от полевых работ`
   - Внешний транспорт: `% от (полевые + внутренний транспорт)`
   - Организация и ликвидация: `% от (полевые + внутренний транспорт)`

5. **Применение коэффициентов к итогу (apply_to = 'total'):**
   ```
   total = (cost_field + cost_office + addons) × K_regional × ...
   ```

6. **Индекс изменения стоимости:**
   ```
   final_total = total × inflation_index
   ```

## Примеры запросов

### Поиск расценок по названию работы
```sql
SELECT 
  id,
  work_title,
  unit,
  price_field,
  price_office,
  params,
  ts_rank(search_text, websearch_to_tsquery('russian', 'топографический план 1:500')) as rank
FROM norm_items
WHERE search_text @@ websearch_to_tsquery('russian', 'топографический план 1:500')
ORDER BY rank DESC, popularity_score DESC
LIMIT 10;
```

### Нечеткий поиск с учетом популярности
```sql
SELECT 
  id,
  work_title,
  similarity(work_title, 'топаграфический план') as sim,
  popularity_score
FROM norm_items
WHERE work_title % 'топаграфический план'
ORDER BY sim DESC, popularity_score DESC
LIMIT 10;
```

### Получение всех коэффициентов для документа
```sql
SELECT code, name, value, apply_to
FROM norm_coeffs
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
ORDER BY apply_to, code;
```

### Расчет итоговой стоимости сметы
```sql
SELECT 
  e.id,
  e.title,
  SUM(el.cost_total) as subtotal,
  e.total_final
FROM estimates e
JOIN estimate_lines el ON el.estimate_id = e.id
WHERE e.id = 'uuid-here'
GROUP BY e.id;
```

## RLS (Row Level Security)

TODO: Настроить политики доступа для ролей:
- `authenticated` - доступ к своим проектам и сметам
- `service_role` - полный доступ для бота
- Публичный доступ к справочникам (norm_docs, norm_items, norm_coeffs, norm_addons)

## Миграции

Миграции находятся в папке `migrations/`:
1. `001_create_smeta_tables.sql` - создание всех таблиц
2. `002_seed_initial_data.sql` - начальные данные из СБЦ ИГДИ 2004

Применение через MCP сервер:
```javascript
await use_mcp_tool("chx1du0mcp0", "itpi_execute_migration", {
  sql: fs.readFileSync('migrations/001_create_smeta_tables.sql', 'utf8')
});
```

## Следующие шаги

1. ✅ Создать структуру таблиц
2. ✅ Загрузить начальные данные
3. ⏳ Настроить RLS политики
4. ⏳ Создать шаблон сметы из примера
5. ⏳ Протестировать на реальных данных
6. ⏳ Разработать API для телеграм-бота
