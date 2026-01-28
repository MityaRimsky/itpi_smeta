# Установка функции exec_migration в базу данных ITPI

## Проблема
В базе данных ITPI (https://itpi.webtm.ru) отсутствует функция `exec_migration`, которая необходима для работы MCP сервера.

## Решение

### Вариант 1: Через Supabase Dashboard (Рекомендуется)

1. Откройте Supabase Dashboard для проекта ITPI
2. Перейдите в раздел **SQL Editor**
3. Скопируйте и выполните SQL код из файла `create_exec_migration.sql`:

```sql
CREATE OR REPLACE FUNCTION public.exec_migration(sql_query TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  EXECUTE sql_query;
  RETURN json_build_object(
    'success', true,
    'message', 'Migration executed successfully'
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN json_build_object(
      'success', false,
      'error', SQLERRM,
      'detail', SQLSTATE
    );
END;
$$;

COMMENT ON FUNCTION public.exec_migration(TEXT) IS 
'Выполняет SQL миграции. Используется MCP сервером для применения миграций через API.';

GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO anon;
```

4. Нажмите **Run** для выполнения

### Вариант 2: Через psql (если есть прямой доступ к БД)

```bash
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" -f create_exec_migration.sql
```

### Вариант 3: Через Supabase CLI

```bash
supabase db push --db-url "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" --file create_exec_migration.sql
```

## Проверка установки

После установки функции, проверьте её работу через MCP сервер:

```bash
# Используйте MCP инструмент itpi_list_tables
# Если функция установлена правильно, вы получите список таблиц
```

Или через curl:

```bash
curl -X POST "https://itpi.webtm.ru/rest/v1/rpc/exec_migration" \
  -H "apikey: YOUR_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer YOUR_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sql_query": "SELECT current_user, current_database();"}'
```

Ожидаемый результат:
```json
{
  "success": true,
  "message": "Migration executed successfully"
}
```

## Что дальше?

После установки функции `exec_migration`:

1. ✅ MCP сервер сможет получать список таблиц
2. ✅ Можно будет выполнять миграции через MCP
3. ✅ Можно создать структуру базы данных для проекта ITPI Smeta

## Дополнительная информация

Эта функция аналогична той, что используется в проекте Shema (https://shema.one) и позволяет безопасно выполнять SQL миграции через REST API.
