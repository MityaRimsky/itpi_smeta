-- =====================================================
-- Откат к рабочей версии функции поиска
-- =====================================================
-- Возвращаемся к версии из 003_fix_search_function.sql
-- которая давала 2/15 успешных тестов
-- =====================================================

DROP FUNCTION IF EXISTS semantic_search_norm_items(text, int);

CREATE OR REPLACE FUNCTION semantic_search_norm_items(
  search_query text,
  limit_count int DEFAULT 20
)
RETURNS TABLE (
  id uuid,
  work_title text,
  unit text,
  price numeric,
  table_no int,
  relevance_score float,
  match_type text,
  matched_synonym text
) AS $$
BEGIN
  RETURN QUERY
  WITH synonym_matches AS (
    -- Находим все синонимы для запроса
    SELECT DISTINCT 
      ws.main_term,
      unnest(ws.synonyms || ws.main_term) as term,
      ws.category
    FROM work_synonyms ws
    WHERE 
      -- Прямое совпадение с основным термином
      ws.main_term ILIKE '%' || search_query || '%'
      -- Или совпадение с любым синонимом
      OR EXISTS (
        SELECT 1 FROM unnest(ws.synonyms) s 
        WHERE s ILIKE '%' || search_query || '%'
      )
      -- Или полнотекстовый поиск
      OR ws.search_vector @@ plainto_tsquery('russian', search_query)
      -- Или триграммное сходство
      OR ws.main_term % search_query
  )
  SELECT 
    ni.id,
    ni.work_title,
    ni.unit,
    ni.price_field as price,  -- ИСПРАВЛЕНО: используем price_field вместо price
    ni.table_no,
    (
      -- 1. Прямое точное совпадение (100 баллов)
      CASE WHEN ni.work_title ILIKE '%' || search_query || '%' THEN 100.0
      ELSE 0.0 END
      +
      -- 2. Совпадение с синонимами (80 баллов)
      CASE WHEN EXISTS (
        SELECT 1 FROM synonym_matches sm 
        WHERE ni.work_title ILIKE '%' || sm.term || '%'
      ) THEN 80.0
      ELSE 0.0 END
      +
      -- 3. Полнотекстовый поиск (40 баллов)
      COALESCE(ts_rank(ni.search_text, plainto_tsquery('russian', search_query)) * 40.0, 0.0)
      +
      -- 4. Триграммное сходство для опечаток (20 баллов)
      COALESCE(similarity(ni.work_title, search_query) * 20.0, 0.0)
      +
      -- 5. Бонус за совпадение категории (10 баллов)
      CASE WHEN EXISTS (
        SELECT 1 FROM synonym_matches sm 
        WHERE ni.work_title ILIKE '%' || sm.category || '%'
      ) THEN 10.0
      ELSE 0.0 END
    ) as relevance_score,
    -- Тип совпадения
    CASE 
      WHEN ni.work_title ILIKE '%' || search_query || '%' THEN 'exact'
      WHEN EXISTS (
        SELECT 1 FROM synonym_matches sm 
        WHERE ni.work_title ILIKE '%' || sm.term || '%'
      ) THEN 'synonym'
      WHEN ni.search_text @@ plainto_tsquery('russian', search_query) THEN 'fulltext'
      WHEN ni.work_title % search_query THEN 'fuzzy'
      ELSE 'other'
    END as match_type,
    -- Какой синоним сработал
    COALESCE(
      (SELECT sm.term FROM synonym_matches sm 
       WHERE ni.work_title ILIKE '%' || sm.term || '%' 
       LIMIT 1),
      search_query
    ) as matched_synonym
  FROM norm_items ni
  WHERE 
    -- Прямое совпадение
    ni.work_title ILIKE '%' || search_query || '%'
    -- Или полнотекстовый поиск
    OR ni.search_text @@ plainto_tsquery('russian', search_query)
    -- Или триграммное сходство (для опечаток)
    OR ni.work_title % search_query
    -- Или совпадение с синонимами
    OR EXISTS (
      SELECT 1 FROM synonym_matches sm 
      WHERE ni.work_title ILIKE '%' || sm.term || '%'
    )
  ORDER BY relevance_score DESC
  LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION semantic_search_norm_items IS 'Умный поиск работ с учётом синонимов, опечаток и полнотекстового поиска (рабочая версия с price_field)';

-- =====================================================
-- Откат завершен - вернулись к рабочей версии!
-- =====================================================
