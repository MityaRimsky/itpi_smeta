-- Миграция 007: Базовые расценки из СБЦ ИГДИ 2004
-- Таблица 8: Создание планово-высотных опорных геодезических сетей
-- Таблица 9: Создание инженерно-топографических планов (основные позиции)

-- Получаем ID документа
DO $$
DECLARE
    v_doc_id UUID;
BEGIN
    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    
    IF v_doc_id IS NULL THEN
        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден. Сначала выполните миграцию 004_norm_docs.sql';
    END IF;

    -- Удаляем существующие расценки для этого документа
    DELETE FROM norm_items WHERE doc_id = v_doc_id;

    -- ========================================
    -- ТАБЛИЦА 8: Планово-высотные опорные геодезические сети
    -- ========================================
    
    -- Плановая опорная сеть 4 класса
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 8, '§1', 'Плановая опорная сеть 4 класс', 'пункт', 12740, 4979, 
     '{"category": "I"}'::jsonb,
     '{"table": 8, "row": 1, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 8, '§1', 'Плановая опорная сеть 4 класс', 'пункт', 14423, 5651,
     '{"category": "II"}'::jsonb,
     '{"table": 8, "row": 1, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 8, '§1', 'Плановая опорная сеть 4 класс', 'пункт', 16640, 6484,
     '{"category": "III"}'::jsonb,
     '{"table": 8, "row": 1, "note": "Категория сложности III"}'::jsonb);

    -- Плановая опорная сеть 1 разряда
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 8, '§2', 'Плановая опорная сеть 1 разряд', 'пункт', 8407, 3313,
     '{"category": "I"}'::jsonb,
     '{"table": 8, "row": 2, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 8, '§2', 'Плановая опорная сеть 1 разряд', 'пункт', 9172, 3599,
     '{"category": "II"}'::jsonb,
     '{"table": 8, "row": 2, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 8, '§2', 'Плановая опорная сеть 1 разряд', 'пункт', 10008, 3912,
     '{"category": "III"}'::jsonb,
     '{"table": 8, "row": 2, "note": "Категория сложности III"}'::jsonb);

    -- Плановая опорная сеть 2 разряда
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 8, '§3', 'Плановая опорная сеть 2 разряд', 'пункт', 5983, 2360,
     '{"category": "I"}'::jsonb,
     '{"table": 8, "row": 3, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 8, '§3', 'Плановая опорная сеть 2 разряд', 'пункт', 6426, 2538,
     '{"category": "II"}'::jsonb,
     '{"table": 8, "row": 3, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 8, '§3', 'Плановая опорная сеть 2 разряд', 'пункт', 6897, 2705,
     '{"category": "III"}'::jsonb,
     '{"table": 8, "row": 3, "note": "Категория сложности III"}'::jsonb);

    -- Высотная опорная сеть IV класса
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 8, '§4', 'Высотная опорная сеть IV класс', 'пункт', 1418, 378,
     '{"category": "I"}'::jsonb,
     '{"table": 8, "row": 4, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 8, '§4', 'Высотная опорная сеть IV класс', 'пункт', 1897, 428,
     '{"category": "II"}'::jsonb,
     '{"table": 8, "row": 4, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 8, '§4', 'Высотная опорная сеть IV класс', 'пункт', 2463, 485,
     '{"category": "III"}'::jsonb,
     '{"table": 8, "row": 4, "note": "Категория сложности III"}'::jsonb);

    -- ========================================
    -- ТАБЛИЦА 9: Инженерно-топографические планы
    -- ========================================
    
    -- Масштаб 1:500, сечение 0,25 м
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§1', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, незастроенная территория', 'га', 1989, 493,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "незастроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 1, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§2', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, незастроенная территория', 'га', 2578, 700,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "незастроенная", "category": "II"}'::jsonb,
     '{"table": 9, "row": 2, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 9, '§3', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, незастроенная территория', 'га', 3402, 859,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "незастроенная", "category": "III"}'::jsonb,
     '{"table": 9, "row": 3, "note": "Категория сложности III"}'::jsonb);

    -- Масштаб 1:500, сечение 0,25 м, застроенная территория
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§1', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, застроенная территория', 'га', 2518, 870,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "застроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 1, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§2', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, застроенная территория', 'га', 3481, 1269,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "застроенная", "category": "II"}'::jsonb,
     '{"table": 9, "row": 2, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 9, '§3', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, застроенная территория', 'га', 4991, 1692,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "застроенная", "category": "III"}'::jsonb,
     '{"table": 9, "row": 3, "note": "Категория сложности III"}'::jsonb);

    -- Масштаб 1:500, сечение 0,25 м, промпредприятие
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§1', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, действующее промышленное предприятие', 'га', 3352, 1436,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "промпредприятие", "category": "I"}'::jsonb,
     '{"table": 9, "row": 1, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§2', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, действующее промышленное предприятие', 'га', 4524, 2093,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "промпредприятие", "category": "II"}'::jsonb,
     '{"table": 9, "row": 2, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 9, '§3', 'Создание инженерно-топографического плана М 1:500, сечение 0,25м, действующее промышленное предприятие', 'га', 6488, 2793,
     '{"scale": "1:500", "contour_interval": 0.25, "territory_type": "промпредприятие", "category": "III"}'::jsonb,
     '{"table": 9, "row": 3, "note": "Категория сложности III"}'::jsonb);

    -- Масштаб 1:500, сечение 0,5 м (примеры)
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§5', 'Создание инженерно-топографического плана М 1:500, сечение 0,5м, незастроенная территория', 'га', 1723, 418,
     '{"scale": "1:500", "contour_interval": 0.5, "territory_type": "незастроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 4, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§5', 'Создание инженерно-топографического плана М 1:500, сечение 0,5м, незастроенная территория', 'га', 2432, 589,
     '{"scale": "1:500", "contour_interval": 0.5, "territory_type": "незастроенная", "category": "II"}'::jsonb,
     '{"table": 9, "row": 5, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 9, '§5', 'Создание инженерно-топографического плана М 1:500, сечение 0,5м, застроенная территория', 'га', 2233, 737,
     '{"scale": "1:500", "contour_interval": 0.5, "territory_type": "застроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 4, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§5', 'Создание инженерно-топографического плана М 1:500, сечение 0,5м, застроенная территория', 'га', 3284, 1067,
     '{"scale": "1:500", "contour_interval": 0.5, "territory_type": "застроенная", "category": "II"}'::jsonb,
     '{"table": 9, "row": 5, "note": "Категория сложности II"}'::jsonb);

    -- Масштаб 1:1000
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§10', 'Создание инженерно-топографического плана М 1:1000, сечение 0,5м, незастроенная территория', 'га', 936, 234,
     '{"scale": "1:1000", "contour_interval": 0.5, "territory_type": "незастроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 10, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§10', 'Создание инженерно-топографического плана М 1:1000, сечение 0,5м, застроенная территория', 'га', 1676, 543,
     '{"scale": "1:1000", "contour_interval": 0.5, "territory_type": "застроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 10, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§10', 'Создание инженерно-топографического плана М 1:1000, сечение 0,5м, промпредприятие', 'га', 2429, 1011,
     '{"scale": "1:1000", "contour_interval": 0.5, "territory_type": "промпредприятие", "category": "I"}'::jsonb,
     '{"table": 9, "row": 10, "note": "Категория сложности I"}'::jsonb);

    -- Масштаб 1:2000
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§16', 'Создание инженерно-топографического плана М 1:2000, сечение 0,5м, незастроенная территория', 'га', 408, 91,
     '{"scale": "1:2000", "contour_interval": 0.5, "territory_type": "незастроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 16, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§16', 'Создание инженерно-топографического плана М 1:2000, сечение 0,5м, застроенная территория', 'га', 1366, 460,
     '{"scale": "1:2000", "contour_interval": 0.5, "territory_type": "застроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 16, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§16', 'Создание инженерно-топографического плана М 1:2000, сечение 0,5м, промпредприятие', 'га', 1777, 759,
     '{"scale": "1:2000", "contour_interval": 0.5, "territory_type": "промпредприятие", "category": "I"}'::jsonb,
     '{"table": 9, "row": 16, "note": "Категория сложности I"}'::jsonb);

    -- Масштаб 1:5000
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§25', 'Создание инженерно-топографического плана М 1:5000, сечение 0,5м, незастроенная территория', 'га', 228, 50,
     '{"scale": "1:5000", "contour_interval": 0.5, "territory_type": "незастроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 25, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§25', 'Создание инженерно-топографического плана М 1:5000, сечение 0,5м, застроенная территория', 'га', 798, 248,
     '{"scale": "1:5000", "contour_interval": 0.5, "territory_type": "застроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 25, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§25', 'Создание инженерно-топографического плана М 1:5000, сечение 0,5м, промпредприятие', 'га', 1037, 425,
     '{"scale": "1:5000", "contour_interval": 0.5, "territory_type": "промпредприятие", "category": "I"}'::jsonb,
     '{"table": 9, "row": 25, "note": "Категория сложности I"}'::jsonb);

    -- Масштаб 1:10000
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 9, '§40', 'Создание инженерно-топографического плана М 1:10000, сечение 1,0м, незастроенная территория', 'га', 121, 26,
     '{"scale": "1:10000", "contour_interval": 1.0, "territory_type": "незастроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 40, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§40', 'Создание инженерно-топографического плана М 1:10000, сечение 1,0м, застроенная территория', 'га', 424, 129,
     '{"scale": "1:10000", "contour_interval": 1.0, "territory_type": "застроенная", "category": "I"}'::jsonb,
     '{"table": 9, "row": 40, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 9, '§40', 'Создание инженерно-топографического плана М 1:10000, сечение 1,0м, промпредприятие', 'га', 551, 226,
     '{"scale": "1:10000", "contour_interval": 1.0, "territory_type": "промпредприятие", "category": "I"}'::jsonb,
     '{"table": 9, "row": 40, "note": "Категория сложности I"}'::jsonb);

    RAISE NOTICE 'Успешно добавлено расценок: %', (SELECT COUNT(*) FROM norm_items WHERE doc_id = v_doc_id);
END $$;

-- Проверка
SELECT 
    table_no,
    section,
    work_title,
    unit,
    price_field,
    price_office,
    params->>'scale' as scale,
    params->>'category' as category,
    params->>'territory_type' as territory
FROM norm_items 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
ORDER BY table_no, section
LIMIT 20;
