-- Миграция 009: Дополнительные работы и расширенные синонимы
-- Таблица 4: Внутренний транспорт
-- Таблица 5: Внешний транспорт
-- Расширенные синонимы для улучшения поиска

DO $$
DECLARE
    v_doc_id UUID;
BEGIN
    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    
    IF v_doc_id IS NULL THEN
        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден';
    END IF;

    -- ========================================
    -- ТАБЛИЦА 4: Внутренний транспорт (процентные надбавки)
    -- ========================================
    
    -- Расходы по внутреннему транспорту в зависимости от расстояния и стоимости работ
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price, params, source_ref) VALUES
    (v_doc_id, 4, '§1', 'Расходы по внутреннему транспорту при расстоянии до 5 км', '%', 8.75,
     '{"distance_km": "до 5", "cost_range": "до 75000", "percent": 8.75}'::jsonb,
     '{"table": 4, "row": 1, "note": "При стоимости работ до 75 тыс.руб"}'::jsonb),
    
    (v_doc_id, 4, '§2', 'Расходы по внутреннему транспорту при расстоянии 5-10 км', '%', 11.25,
     '{"distance_km": "5-10", "cost_range": "до 75000", "percent": 11.25}'::jsonb,
     '{"table": 4, "row": 2, "note": "При стоимости работ до 75 тыс.руб"}'::jsonb),
    
    (v_doc_id, 4, '§3', 'Расходы по внутреннему транспорту при расстоянии 10-15 км', '%', 13.75,
     '{"distance_km": "10-15", "cost_range": "до 75000", "percent": 13.75}'::jsonb,
     '{"table": 4, "row": 3, "note": "При стоимости работ до 75 тыс.руб"}'::jsonb),
    
    (v_doc_id, 4, '§4', 'Расходы по внутреннему транспорту при расстоянии 15-20 км', '%', 16.25,
     '{"distance_km": "15-20", "cost_range": "до 75000", "percent": 16.25}'::jsonb,
     '{"table": 4, "row": 4, "note": "При стоимости работ до 75 тыс.руб"}'::jsonb),
    
    (v_doc_id, 4, '§5', 'Расходы по внутреннему транспорту при расстоянии 20-30 км', '%', 18.75,
     '{"distance_km": "20-30", "cost_range": "до 75000", "percent": 18.75}'::jsonb,
     '{"table": 4, "row": 5, "note": "При стоимости работ до 75 тыс.руб"}'::jsonb);

    -- ========================================
    -- ТАБЛИЦА 5: Внешний транспорт (процентные надбавки)
    -- ========================================
    
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price, params, source_ref) VALUES
    (v_doc_id, 5, '§1', 'Расходы по внешнему транспорту при расстоянии 25-100 км, продолжительность до 1 мес', '%', 14.0,
     '{"distance_km": "25-100", "duration_months": "до 1", "percent": 14.0}'::jsonb,
     '{"table": 5, "row": 1, "note": "Продолжительность изысканий до 1 месяца"}'::jsonb),
    
    (v_doc_id, 5, '§2', 'Расходы по внешнему транспорту при расстоянии 100-300 км, продолжительность до 1 мес', '%', 19.6,
     '{"distance_km": "100-300", "duration_months": "до 1", "percent": 19.6}'::jsonb,
     '{"table": 5, "row": 2, "note": "Продолжительность изысканий до 1 месяца"}'::jsonb),
    
    (v_doc_id, 5, '§3', 'Расходы по внешнему транспорту при расстоянии 300-500 км, продолжительность до 1 мес', '%', 25.2,
     '{"distance_km": "300-500", "duration_months": "до 1", "percent": 25.2}'::jsonb,
     '{"table": 5, "row": 3, "note": "Продолжительность изысканий до 1 месяца"}'::jsonb),
    
    (v_doc_id, 5, '§4', 'Расходы по внешнему транспорту при расстоянии 500-1000 км, продолжительность до 1 мес', '%', 30.8,
     '{"distance_km": "500-1000", "duration_months": "до 1", "percent": 30.8}'::jsonb,
     '{"table": 5, "row": 4, "note": "Продолжительность изысканий до 1 месяца"}'::jsonb),
    
    (v_doc_id, 5, '§5', 'Расходы по внешнему транспорту при расстоянии 1000-2000 км, продолжительность 2 мес', '%', 32.2,
     '{"distance_km": "1000-2000", "duration_months": "2", "percent": 32.2}'::jsonb,
     '{"table": 5, "row": 5, "note": "Продолжительность изысканий 2 месяца"}'::jsonb),
    
    (v_doc_id, 5, '§6', 'Расходы по внешнему транспорту при расстоянии свыше 2000 км, продолжительность 2 мес', '%', 39.2,
     '{"distance_km": "свыше 2000", "duration_months": "2", "percent": 39.2}'::jsonb,
     '{"table": 5, "row": 6, "note": "Продолжительность изысканий 2 месяца"}'::jsonb);

    RAISE NOTICE 'Успешно добавлено дополнительных работ: %', 
        (SELECT COUNT(*) FROM norm_items WHERE doc_id = v_doc_id AND table_no IN (4, 5));
END $$;

-- ========================================
-- РАСШИРЕННЫЕ СИНОНИМЫ ДЛЯ УЛУЧШЕНИЯ ПОИСКА
-- ========================================

-- Обновляем search_text для всех расценок с учетом синонимов
UPDATE norm_items SET search_text = 
    setweight(to_tsvector('russian', coalesce(work_title, '')), 'A') ||
    setweight(to_tsvector('russian', coalesce(unit, '')), 'B') ||
    setweight(to_tsvector('russian', coalesce(section, '')), 'C') ||
    setweight(to_tsvector('russian', coalesce(notes, '')), 'D') ||
    -- Добавляем синонимы для масштабов
    CASE 
        WHEN params->>'scale' = '1:500' THEN to_tsvector('russian', 'масштаб 1:500 пятьсот пятисотый')
        WHEN params->>'scale' = '1:1000' THEN to_tsvector('russian', 'масштаб 1:1000 тысяча тысячный')
        WHEN params->>'scale' = '1:2000' THEN to_tsvector('russian', 'масштаб 1:2000 двухтысячный')
        WHEN params->>'scale' = '1:5000' THEN to_tsvector('russian', 'масштаб 1:5000 пятитысячный')
        WHEN params->>'scale' = '1:10000' THEN to_tsvector('russian', 'масштаб 1:10000 десятитысячный')
        ELSE ''::tsvector
    END ||
    -- Добавляем синонимы для типов территорий
    CASE 
        WHEN params->>'territory_type' = 'незастроенная' THEN to_tsvector('russian', 'незастроенная открытая свободная')
        WHEN params->>'territory_type' = 'застроенная' THEN to_tsvector('russian', 'застроенная городская населенная')
        WHEN params->>'territory_type' = 'промпредприятие' THEN to_tsvector('russian', 'промпредприятие промышленная завод фабрика предприятие')
        ELSE ''::tsvector
    END ||
    -- Добавляем синонимы для категорий сложности
    CASE 
        WHEN params->>'category' = 'I' THEN to_tsvector('russian', 'первая простая легкая')
        WHEN params->>'category' = 'II' THEN to_tsvector('russian', 'вторая средняя')
        WHEN params->>'category' = 'III' THEN to_tsvector('russian', 'третья сложная трудная')
        ELSE ''::tsvector
    END ||
    -- Добавляем синонимы для линейных сооружений
    CASE 
        WHEN work_title ILIKE '%железн%дорог%' THEN to_tsvector('russian', 'железная дорога жд рельсы')
        WHEN work_title ILIKE '%автомобильн%дорог%' THEN to_tsvector('russian', 'автомобильная дорога автодорога шоссе')
        WHEN work_title ILIKE '%трубопровод%' THEN to_tsvector('russian', 'трубопровод труба газопровод нефтепровод')
        WHEN work_title ILIKE '%электропередач%' THEN to_tsvector('russian', 'электропередача лэп линия электропередачи')
        WHEN work_title ILIKE '%связ%' THEN to_tsvector('russian', 'связь кабель телефон')
        ELSE ''::tsvector
    END ||
    -- Добавляем синонимы для типов работ
    CASE 
        WHEN work_title ILIKE '%топографическ%план%' THEN to_tsvector('russian', 'топография топосъемка геодезия план карта')
        WHEN work_title ILIKE '%опорн%сет%' THEN to_tsvector('russian', 'опорная сеть геодезическая триангуляция полигонометрия')
        WHEN work_title ILIKE '%изыскан%' THEN to_tsvector('russian', 'изыскания трассирование проектирование')
        ELSE ''::tsvector
    END
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004');

-- Создаем индекс для быстрого поиска по параметрам
CREATE INDEX IF NOT EXISTS idx_norm_items_params_gin ON norm_items USING gin(params);

-- Создаем индекс для поиска по таблицам
CREATE INDEX IF NOT EXISTS idx_norm_items_table_section ON norm_items(table_no, section);

-- Проверка
SELECT 
    table_no,
    section,
    work_title,
    unit,
    COALESCE(price, price_field) as price,
    params->>'percent' as percent,
    params->>'distance_km' as distance
FROM norm_items 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
AND table_no IN (4, 5)
ORDER BY table_no, section;

-- Статистика по всем загруженным расценкам
SELECT 
    table_no,
    COUNT(*) as count,
    STRING_AGG(DISTINCT section, ', ' ORDER BY section) as sections
FROM norm_items 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
GROUP BY table_no
ORDER BY table_no;

RAISE NOTICE '=== МИГРАЦИИ ЗАВЕРШЕНЫ ===';
RAISE NOTICE 'Всего расценок загружено: %', (SELECT COUNT(*) FROM norm_items WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004'));
