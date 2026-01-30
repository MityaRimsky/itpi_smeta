# Миграции базы данных для системы расчета смет

## Структура миграций

### Базовые таблицы
- **001_create_smeta_tables.sql** - Создание основных таблиц системы
- **002_seed_initial_data.sql** - Начальные тестовые данные
- **003_smart_search.sql** - Система умного поиска с синонимами

### Нормативная база СБЦ ИГДИ 2004
- **004_norm_docs.sql** - Справочник базовых цен на инженерно-геодезические изыскания
- **005_norm_coeffs.sql** - Коэффициенты (горные районы, спецрежим, районные, Крайний Север и др.)
- **006_norm_addons.sql** - Добавочные начисления (транспорт, орг.ликвидация)

### Расценки (в разработке)
- **007_norm_items_basic.sql** - Базовые расценки (таблица 8-9)
- **008_norm_items_linear.sql** - Расценки для линейных сооружений (таблица 12-17)
- **009_norm_items_additional.sql** - Дополнительные работы
- **010_search_synonyms.sql** - Расширенные синонимы для поиска

## Порядок применения миграций

Миграции должны применяться **строго по порядку**:

```bash
# 1. Базовая структура
psql -f migrations/001_create_smeta_tables.sql
psql -f migrations/002_seed_initial_data.sql
psql -f migrations/003_smart_search.sql

# 2. Нормативная база
psql -f migrations/004_norm_docs.sql
psql -f migrations/005_norm_coeffs.sql
psql -f migrations/006_norm_addons.sql

# 3. Расценки (когда будут готовы)
# psql -f migrations/007_norm_items_basic.sql
# psql -f migrations/008_norm_items_linear.sql
# psql -f migrations/009_norm_items_additional.sql
# psql -f migrations/010_search_synonyms.sql
```

## Применение через MCP сервер

Если у вас настроен MCP сервер `supabase-itpi-smeta`, можно применить миграции через него:

```javascript
// Пример использования MCP инструмента
{
  "tool": "itpi_execute_migration",
  "sql": "-- содержимое миграции --"
}
```

## Автоматическое применение всех миграций

Используйте скрипт `apply_all_migrations.sh`:

```bash
chmod +x migrations/apply_all_migrations.sh
./migrations/apply_all_migrations.sh
```

## Проверка применения миграций

После применения миграций проверьте:

```sql
-- Проверка документов
SELECT code, title, version FROM norm_docs;

-- Проверка коэффициентов
SELECT code, name, value, apply_to 
FROM norm_coeffs 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
LIMIT 10;

-- Проверка добавочных начислений
SELECT code, name, calc_type, value, base_type
FROM norm_addons 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
LIMIT 10;

-- Проверка поиска
SELECT * FROM smart_search_norms('топографическая съемка', 5);
```

## Структура данных

### norm_docs (Нормативные документы)
- `code` - уникальный код документа (например, 'SBC_IGDI_2004')
- `title` - полное название
- `version` - версия/год
- `base_date` - базисная дата цен
- `source_name` - источник/примечания

### norm_coeffs (Коэффициенты)
- `code` - уникальный код коэффициента
- `name` - название
- `value` - значение коэффициента
- `apply_to` - к чему применяется: 'field', 'office', 'total'
- `conditions` - условия применения (JSONB)
- `source_ref` - ссылка на источник (таблица, пункт)

### norm_addons (Добавочные начисления)
- `code` - уникальный код
- `name` - название
- `calc_type` - тип расчета: 'fixed', 'per_unit', 'percent'
- `value` - значение
- `base_type` - к чему применяется: 'field', 'office', 'field_plus_office', 'field_plus_internal', 'subtotal'
- `conditions` - условия (расстояние, стоимость, продолжительность)
- `source_ref` - ссылка на источник

### norm_items (Расценки) - в разработке
- `table_no` - номер таблицы в СБЦ
- `section` - раздел/параграф
- `work_title` - название работы
- `unit` - единица измерения
- `price_field` - цена полевых работ
- `price_office` - цена камеральных работ
- `params` - параметры (масштаб, категория сложности)
- `source_ref` - обоснование

## Примеры использования

### Поиск расценок
```sql
-- Поиск по ключевым словам
SELECT * FROM smart_search_norms('топографическая съемка масштаб 1:500', 10);

-- Поиск коэффициентов
SELECT * FROM norm_coeffs 
WHERE name ILIKE '%спецрежим%';

-- Поиск транспортных расходов
SELECT * FROM norm_addons 
WHERE code LIKE 'INTERNAL_TRANSPORT%'
AND conditions->>'distance_max' = '15';
```

### Расчет стоимости работ
```sql
-- Пример: топосъемка 92 га, II категория, промпредприятие
-- Базовая цена из таблицы 9, §5
-- + коэффициенты (спецрежим 1.25, районный и т.д.)
-- + транспорт (внутренний + внешний)
-- + орг.ликвидация 6%
```

## Источники данных

Все данные взяты из официальных документов:
- **СБЦ ИГДИ 2004** - Справочник базовых цен на инженерно-геодезические изыскания для строительства
- Утвержден постановлением Госстроя России от 23.12.2003 г. No 213
- Цены приведены к базисному уровню на 01.01.2001 г.

## Следующие шаги

1. ✅ Создать базовую структуру таблиц
2. ✅ Добавить документ СБЦ ИГДИ 2004
3. ✅ Добавить коэффициенты
4. ✅ Добавить добавочные начисления
5. ⏳ Добавить расценки из таблицы 8 (опорные сети)
6. ⏳ Добавить расценки из таблицы 9 (топосъемка)
7. ⏳ Добавить расценки из таблиц 12-17 (линейные сооружения)
8. ⏳ Расширить синонимы для поиска
9. ⏳ Создать примеры расчета смет

## Контакты и поддержка

Для вопросов и предложений создавайте issues в репозитории проекта.
