-- Миграция 008: Расценки для линейных сооружений из СБЦ ИГДИ 2004
-- Таблица 12: Изыскания трасс железных и автомобильных дорог
-- Таблица 13: Изыскания трасс магистральных трубопроводов
-- Таблица 15: Изыскания трасс воздушных и подземных линий электропередачи и связи

DO $$
DECLARE
    v_doc_id UUID;
BEGIN
    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    
    IF v_doc_id IS NULL THEN
        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден. Сначала выполните миграцию 004_norm_docs.sql';
    END IF;

    -- ========================================
    -- ТАБЛИЦА 12: Изыскания трасс железных и автомобильных дорог
    -- ========================================
    
    -- Изыскания новых железных и автомобильных дорог I-II технических категорий
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 12, '§1', 'Изыскания новых железных и автомобильных дорог I-II технических категорий', 'км', 16114, 6375,
     '{"category": "I", "road_category": "I-II"}'::jsonb,
     '{"table": 12, "row": 1, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 12, '§1', 'Изыскания новых железных и автомобильных дорог I-II технических категорий', 'км', 27375, 8667,
     '{"category": "II", "road_category": "I-II"}'::jsonb,
     '{"table": 12, "row": 1, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 12, '§1', 'Изыскания новых железных и автомобильных дорог I-II технических категорий', 'км', 61304, 15239,
     '{"category": "III", "road_category": "I-II"}'::jsonb,
     '{"table": 12, "row": 1, "note": "Категория сложности III"}'::jsonb);

    -- Изыскания новых железных и автомобильных дорог III-IV технических категорий
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 12, '§2', 'Изыскания новых железных и автомобильных дорог III-IV технических категорий, подъездные и лесовозные железные дороги', 'км', 15053, 5895,
     '{"category": "I", "road_category": "III-IV"}'::jsonb,
     '{"table": 12, "row": 2, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 12, '§2', 'Изыскания новых железных и автомобильных дорог III-IV технических категорий, подъездные и лесовозные железные дороги', 'км', 25902, 8196,
     '{"category": "II", "road_category": "III-IV"}'::jsonb,
     '{"table": 12, "row": 2, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 12, '§2', 'Изыскания новых железных и автомобильных дорог III-IV технических категорий, подъездные и лесовозные железные дороги', 'км', 59743, 14517,
     '{"category": "III", "road_category": "III-IV"}'::jsonb,
     '{"table": 12, "row": 2, "note": "Категория сложности III"}'::jsonb);

    -- Изыскания автомобильных дорог V технической категории
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 12, '§3', 'Изыскания автомобильных дорог V технической категории', 'км', 13122, 5143,
     '{"category": "I", "road_category": "V"}'::jsonb,
     '{"table": 12, "row": 3, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 12, '§3', 'Изыскания автомобильных дорог V технической категории', 'км', 22841, 7156,
     '{"category": "II", "road_category": "V"}'::jsonb,
     '{"table": 12, "row": 3, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 12, '§3', 'Изыскания автомобильных дорог V технической категории', 'км', 50474, 12169,
     '{"category": "III", "road_category": "V"}'::jsonb,
     '{"table": 12, "row": 3, "note": "Категория сложности III"}'::jsonb);

    -- ========================================
    -- ТАБЛИЦА 13: Изыскания трасс магистральных трубопроводов
    -- ========================================
    
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 13, '§1', 'Изыскания трасс магистральных трубопроводов', 'км', 5790, 3302,
     '{"category": "I"}'::jsonb,
     '{"table": 13, "row": 1, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 13, '§1', 'Изыскания трасс магистральных трубопроводов', 'км', 12076, 5327,
     '{"category": "II"}'::jsonb,
     '{"table": 13, "row": 1, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 13, '§1', 'Изыскания трасс магистральных трубопроводов', 'км', 23432, 8036,
     '{"category": "III"}'::jsonb,
     '{"table": 13, "row": 1, "note": "Категория сложности III"}'::jsonb);

    -- ========================================
    -- ТАБЛИЦА 15: Изыскания трасс воздушных и подземных линий электропередачи и связи
    -- ========================================
    
    -- Воздушные линии электропередачи 0,4-20 кВ
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 15, '§1', 'Изыскания трасс воздушных линий электропередачи 0,4-20 кВ', 'км', 1918, 882,
     '{"category": "I", "voltage": "0.4-20", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 1, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 15, '§1', 'Изыскания трасс воздушных линий электропередачи 0,4-20 кВ', 'км', 4106, 1984,
     '{"category": "II", "voltage": "0.4-20", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 1, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 15, '§1', 'Изыскания трасс воздушных линий электропередачи 0,4-20 кВ', 'км', 7760, 3679,
     '{"category": "III", "voltage": "0.4-20", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 1, "note": "Категория сложности III"}'::jsonb);

    -- Воздушные линии электропередачи 35-110 кВ
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 15, '§2', 'Изыскания трасс воздушных линий электропередачи 35-110 кВ', 'км', 3440, 1599,
     '{"category": "I", "voltage": "35-110", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 2, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 15, '§2', 'Изыскания трасс воздушных линий электропередачи 35-110 кВ', 'км', 7075, 3410,
     '{"category": "II", "voltage": "35-110", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 2, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 15, '§2', 'Изыскания трасс воздушных линий электропередачи 35-110 кВ', 'км', 12624, 6435,
     '{"category": "III", "voltage": "35-110", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 2, "note": "Категория сложности III"}'::jsonb);

    -- Воздушные линии электропередачи 220-500 кВ
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 15, '§3', 'Изыскания трасс воздушных линий электропередачи 220-500 кВ', 'км', 3833, 1734,
     '{"category": "I", "voltage": "220-500", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 3, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 15, '§3', 'Изыскания трасс воздушных линий электропередачи 220-500 кВ', 'км', 7922, 3924,
     '{"category": "II", "voltage": "220-500", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 3, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 15, '§3', 'Изыскания трасс воздушных линий электропередачи 220-500 кВ', 'км', 14251, 7179,
     '{"category": "III", "voltage": "220-500", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 3, "note": "Категория сложности III"}'::jsonb);

    -- Воздушные линии электропередачи 750-1150 кВ
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 15, '§4', 'Изыскания трасс воздушных линий электропередачи 750-1150 кВ', 'км', 3838, 1812,
     '{"category": "I", "voltage": "750-1150", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 4, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 15, '§4', 'Изыскания трасс воздушных линий электропередачи 750-1150 кВ', 'км', 10095, 5074,
     '{"category": "II", "voltage": "750-1150", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 4, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 15, '§4', 'Изыскания трасс воздушных линий электропередачи 750-1150 кВ', 'км', 15970, 8389,
     '{"category": "III", "voltage": "750-1150", "line_type": "воздушная"}'::jsonb,
     '{"table": 15, "row": 4, "note": "Категория сложности III"}'::jsonb);

    -- Воздушные магистральные линии связи
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 15, '§5', 'Изыскания трасс воздушных магистральных линий связи', 'км', 2619, 1140,
     '{"category": "I", "line_type": "воздушная связь"}'::jsonb,
     '{"table": 15, "row": 5, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 15, '§5', 'Изыскания трасс воздушных магистральных линий связи', 'км', 5099, 2431,
     '{"category": "II", "line_type": "воздушная связь"}'::jsonb,
     '{"table": 15, "row": 5, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 15, '§5', 'Изыскания трасс воздушных магистральных линий связи', 'км', 9283, 4463,
     '{"category": "III", "line_type": "воздушная связь"}'::jsonb,
     '{"table": 15, "row": 5, "note": "Категория сложности III"}'::jsonb);

    -- Подземные кабельные линии электропередачи 0,4-20 кВ и связи
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 15, '§6', 'Изыскания трасс подземных кабельных линий электропередачи 0,4-20 кВ и связи', 'км', 4146, 2273,
     '{"category": "I", "voltage": "0.4-20", "line_type": "подземная"}'::jsonb,
     '{"table": 15, "row": 6, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 15, '§6', 'Изыскания трасс подземных кабельных линий электропередачи 0,4-20 кВ и связи', 'км', 7913, 4889,
     '{"category": "II", "voltage": "0.4-20", "line_type": "подземная"}'::jsonb,
     '{"table": 15, "row": 6, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 15, '§6', 'Изыскания трасс подземных кабельных линий электропередачи 0,4-20 кВ и связи', 'км', 13867, 8508,
     '{"category": "III", "voltage": "0.4-20", "line_type": "подземная"}'::jsonb,
     '{"table": 15, "row": 6, "note": "Категория сложности III"}'::jsonb);

    -- Подземные кабельные линии электропередачи 35-220 кВ
    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price_field, price_office, params, source_ref) VALUES
    (v_doc_id, 15, '§7', 'Изыскания трасс подземных кабельных линий электропередачи 35-220 кВ', 'км', 4700, 2507,
     '{"category": "I", "voltage": "35-220", "line_type": "подземная"}'::jsonb,
     '{"table": 15, "row": 7, "note": "Категория сложности I"}'::jsonb),
    
    (v_doc_id, 15, '§7', 'Изыскания трасс подземных кабельных линий электропередачи 35-220 кВ', 'км', 10853, 6048,
     '{"category": "II", "voltage": "35-220", "line_type": "подземная"}'::jsonb,
     '{"table": 15, "row": 7, "note": "Категория сложности II"}'::jsonb),
    
    (v_doc_id, 15, '§7', 'Изыскания трасс подземных кабельных линий электропередачи 35-220 кВ', 'км', 14266, 8892,
     '{"category": "III", "voltage": "35-220", "line_type": "подземная"}'::jsonb,
     '{"table": 15, "row": 7, "note": "Категория сложности III"}'::jsonb);

    RAISE NOTICE 'Успешно добавлено расценок для линейных сооружений: %', 
        (SELECT COUNT(*) FROM norm_items WHERE doc_id = v_doc_id AND table_no IN (12, 13, 15));
END $$;

-- Проверка
SELECT 
    table_no,
    section,
    work_title,
    unit,
    price_field,
    price_office,
    params->>'category' as category,
    params->>'road_category' as road_cat,
    params->>'voltage' as voltage,
    params->>'line_type' as line_type
FROM norm_items 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
AND table_no IN (12, 13, 15)
ORDER BY table_no, section
LIMIT 20;
