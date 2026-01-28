-- Функция для выполнения SQL миграций через API
-- Используется MCP сервером для применения миграций

CREATE OR REPLACE FUNCTION public.exec_migration(sql_query TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Выполняем переданный SQL запрос
  EXECUTE sql_query;
  
  -- Возвращаем успешный результат
  RETURN json_build_object(
    'success', true,
    'message', 'Migration executed successfully'
  );
EXCEPTION
  WHEN OTHERS THEN
    -- В случае ошибки возвращаем информацию об ошибке
    RETURN json_build_object(
      'success', false,
      'error', SQLERRM,
      'detail', SQLSTATE
    );
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION public.exec_migration(TEXT) IS 
'Выполняет SQL миграции. Используется MCP сервером для применения миграций через API.';

-- Даем права на выполнение функции
GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.exec_migration(TEXT) TO anon;
