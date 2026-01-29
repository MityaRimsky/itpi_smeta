# Руководство по применению миграций

## Обзор

Миграции находятся в папке `migrations/` и применяются последовательно для создания структуры БД и загрузки начальных данных.

## Список миграций

1. **001_create_smeta_tables.sql** - Создание всех 11 таблиц с индексами и триггерами
2. **002_seed_initial_data.sql** - Загрузка начальных данных из СБЦ ИГДИ 2004

## Способы применения миграций

### Способ 1: Через MCP сервер (рекомендуется)

Используйте MCP сервер `supabase-itpi-smeta` для выполнения миграций:

```javascript
// Применение миграции 001
const migration001 = fs.readFileSync('migrations/001_create_smeta_tables.sql', 'utf8');
await use_mcp_tool("chx1du0mcp0", "itpi_execute_migration", {
  sql: migration001
});

// Применение миграции 002
const migration002 = fs.readFileSync('migrations/002_seed_initial_data.sql', 'utf8');
await use_mcp_tool("chx1du0mcp0", "itpi_execute_migration", {
  sql: migration002
});
```

### Способ 2: Через psql

Если у вас есть прямой доступ к БД:

```bash
# Загрузите переменные окружения
source .env.supabase

# Примените миграции
psql "$DATABASE_URL" -f migrations/001_create_smeta_tables.sql
psql "$DATABASE_URL" -f migrations/002_seed_initial_data.sql
```

### Способ 3: Через Supabase Dashboard

1. Откройте Supabase Dashboard
2. Перейдите в раздел SQL Editor
3. Скопируйте содержимое файла миграции
4. Выполните SQL

## Проверка применения миграций

После применения миграций проверьте результат:

```sql
-- Проверка созданных таблиц
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Проверка загруженных данных
SELECT 
  (SELECT COUNT(*) FROM norm_docs) as docs,
  (SELECT COUNT(*) FROM norm_items) as items,
  (SELECT COUNT(*) FROM norm_coeffs) as coeffs,
  (SELECT COUNT(*) FROM norm_addons) as addons,
  (SELECT COUNT(*) FROM inflation_indices) as indices,
  (SELECT COUNT(*) FROM regional_coeffs) as regions;
```

Ожидаемый результат:
```
docs | items | coeffs | addons | indices | regions
-----|-------|--------|--------|---------|--------
  1  |   6   |   4    |   5    |    3    |    5
```

## Откат миграций

Если нужно откатить изменения:

```sql
-- Удаление всех таблиц (ОСТОРОЖНО!)
DROP TABLE IF EXISTS estimate_lines CASCADE;
DROP TABLE IF EXISTS estimates CASCADE;
DROP TABLE IF EXISTS template_sections CASCADE;
DROP TABLE IF EXISTS estimate_templates CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS norm_coeffs CASCADE;
DROP TABLE IF EXISTS norm_addons CASCADE;
DROP TABLE IF EXISTS norm_items CASCADE;
DROP TABLE IF EXISTS norm_docs CASCADE;
DROP TABLE IF EXISTS inflation_indices CASCADE;
DROP TABLE IF EXISTS regional_coeffs CASCADE;

-- Удаление функций и триггеров
DROP FUNCTION IF EXISTS update_norm_items_search_text() CASCADE;
DROP FUNCTION IF EXISTS update_norm_item_popularity() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```

## Следующие шаги после применения миграций

1. **Настроить RLS политики** - для безопасного доступа к данным
2. **Загрузить больше расценок** - из других таблиц СБЦ
3. **Создать шаблоны смет** - для быстрого создания типовых смет
4. **Протестировать поиск** - проверить работу полнотекстового поиска
5. **Разработать API** - для телеграм-бота

## Добавление новых расценок

Пример добавления расценки вручную:

```sql
DO $$
DECLARE
    doc_uuid uuid;
BEGIN
    SELECT id INTO doc_uuid FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit, 
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_uuid, 
        9, 
        '§11',
        'Создание инженерно-топографического плана м-ба 1:1000, высота сечения рельефа 0,5м (II кат., застроенная)',
        'га',
        1430, 343,
        jsonb_build_object(
            'scale', '1:1000',
            'height_section', 0.5,
            'category', 'II',
            'territory_type', 'застроенная'
        ),
        jsonb_build_object('table', 9, 'section', 11)
    );
END $$;
```

## Массовая загрузка данных

Для загрузки большого количества расценок используйте скрипт:

```sql
-- Создайте временную таблицу для импорта
CREATE TEMP TABLE temp_import (
    table_no int,
    section text,
    work_title text,
    unit text,
    price_field numeric,
    price_office numeric,
    scale text,
    height_section numeric,
    category text,
    territory_type text
);

-- Загрузите данные из CSV
COPY temp_import FROM '/path/to/data.csv' CSV HEADER;

-- Вставьте в основную таблицу
INSERT INTO norm_items (
    doc_id, table_no, section, work_title, unit,
    price_field, price_office, params, source_ref
)
SELECT 
    (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004'),
    table_no,
    section,
    work_title,
    unit,
    price_field,
    price_office,
    jsonb_build_object(
        'scale', scale,
        'height_section', height_section,
        'category', category,
        'territory_type', territory_type
    ),
    jsonb_build_object('table', table_no, 'section', section)
FROM temp_import;
```

## Troubleshooting

### Ошибка: "relation already exists"

Таблица уже существует. Либо удалите её, либо пропустите миграцию.

### Ошибка: "permission denied"

Убедитесь, что используете правильные credentials с правами на создание таблиц.

### Ошибка: "extension pg_trgm does not exist"

Установите расширение:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

## Полезные запросы

### Просмотр структуры таблицы
```sql
\d+ norm_items
```

### Просмотр всех индексов
```sql
SELECT tablename, indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename, indexname;
```

### Просмотр всех триггеров
```sql
SELECT trigger_name, event_manipulation, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 'public';
```

## Контакты и поддержка

При возникновении проблем с миграциями:
1. Проверьте логи Supabase
2. Убедитесь в правильности SQL синтаксиса
3. Проверьте права доступа к БД
