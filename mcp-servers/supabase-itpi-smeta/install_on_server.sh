#!/bin/bash
# Скрипт для установки функции exec_migration на сервере ITPI
# Запустите на сервере: bash install_on_server.sh

echo "🔧 Установка функции exec_migration в базу данных ITPI..."

# SQL код функции
SQL='CREATE OR REPLACE FUNCTION public.exec_migration(sql_query TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result_message TEXT;
BEGIN
    EXECUTE sql_query;
    RETURN json_build_object('\''success'\'', true, '\''message'\'', '\''Migration executed successfully'\'');
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object('\''success'\'', false, '\''error'\'', SQLERRM, '\''detail'\'', SQLSTATE);
END;
$$;

COMMENT ON FUNCTION public.exec_migration(TEXT) IS '\''Выполняет SQL миграции. Используется MCP сервером для применения миграций через API.'\'';

GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO service_role;'

# Выполнение через docker
docker exec supabase-db psql -U postgres -d postgres -c "$SQL"

if [ $? -eq 0 ]; then
    echo "✅ Функция exec_migration успешно установлена!"
    echo ""
    echo "Проверка работы..."
    docker exec supabase-db psql -U postgres -d postgres -c "SELECT exec_migration('SELECT 1;');"
else
    echo "❌ Ошибка при установке функции"
    exit 1
fi
