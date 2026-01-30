-- =====================================================
-- Добавление работ из реальной сметы в БД
-- =====================================================
-- Источник: Смета на строительство производства этилбензола
-- СБЦ на ИГДИ 2004 г., СБЦ на ИГИ и ИЭИ 1999 г.
-- =====================================================

-- Получаем ID документа СБЦ на ИГДИ 2004
DO $$
DECLARE
    doc_igdi_id uuid;
    doc_igi_id uuid;
BEGIN
    -- Создаем документ СБЦ на ИГДИ 2004 если его нет
    INSERT INTO norm_docs (code, title, version, base_date)
    VALUES ('СБЦ-ИГДИ-2004', 'Сборник базовых цен на инженерно-геодезические изыскания для строительства', '2004', '2001-01-01')
    ON CONFLICT (code) DO NOTHING
    RETURNING id INTO doc_igdi_id;
    
    -- Если документ уже существовал, получаем его ID
    IF doc_igdi_id IS NULL THEN
        SELECT id INTO doc_igdi_id FROM norm_docs WHERE code = 'СБЦ-ИГДИ-2004';
    END IF;
    
    -- Создаем документ СБЦ на ИГИ 1999 если его нет
    INSERT INTO norm_docs (code, title, version, base_date)
    VALUES ('СБЦ-ИГИ-1999', 'Сборник базовых цен на инженерно-геологические изыскания для строительства', '1999', '2001-01-01')
    ON CONFLICT (code) DO NOTHING
    RETURNING id INTO doc_igi_id;
    
    IF doc_igi_id IS NULL THEN
        SELECT id INTO doc_igi_id FROM norm_docs WHERE code = 'СБЦ-ИГИ-1999';
    END IF;

    -- =====================================================
    -- СМЕТА 1: ИГДИ (Инженерно-геодезические изыскания)
    -- =====================================================
    
    -- 1. Создание инженерно-топографического плана 1:500 (полевые работы)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 9, 'п. 5',
        'Создание инженерно-топографического плана м-ба 1:500, высота сечения рельефа 0,5м со съемкой подземных коммуникаций, с эскизами опор',
        'га',
        4632.00, NULL,
        jsonb_build_object(
            'scale', '1:500',
            'category', 'II',
            'territory', 'промпредприятие',
            'relief_section', '0.5м',
            'underground_survey', true,
            'sketch_supports', true
        ),
        jsonb_build_object(
            'table', 9,
            'row', 5,
            'note', 'II категория сложности, промышленное предприятие, с подземными коммуникациями'
        )
    ) ON CONFLICT DO NOTHING;
    
    -- 2. Создание инженерно-топографического плана 1:500 (камеральные работы)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 9, 'п. 5',
        'Создание инженерно-топографического плана м-ба 1:500 сечение рельефа 0,5 (составление плана в цвете с применением компьютерных технологий)',
        'га',
        NULL, 2558.00,
        jsonb_build_object(
            'scale', '1:500',
            'category', 'II',
            'territory', 'промпредприятие',
            'relief_section', '0.5м',
            'underground_survey', true,
            'sketch_supports', true,
            'color_plan', true,
            'computer_tech', true,
            'work_type', 'камеральные'
        ),
        jsonb_build_object(
            'table', 9,
            'row', 5,
            'note', 'Камеральные работы, составление плана в цвете'
        )
    ) ON CONFLICT DO NOTHING;
    
    -- 3. Инженерные изыскания трасс железных дорог III-IV категории (полевые)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 12, 'п. 2',
        'Инженерные изыскания трасс железных дорог III-IV категории',
        'км',
        25902.00, NULL,
        jsonb_build_object(
            'category', 'III-IV',
            'complexity', 'II',
            'object_type', 'железная дорога'
        ),
        jsonb_build_object(
            'table', 12,
            'row', 2,
            'note', 'II категория сложности'
        )
    ) ON CONFLICT DO NOTHING;
    
    -- 4. Инженерные изыскания трасс железных дорог III-IV категории (камеральные)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 12, 'п. 2',
        'Инженерные изыскания трасс железных дорог III-IV категории (камеральные работы)',
        'км',
        NULL, 8196.00,
        jsonb_build_object(
            'category', 'III-IV',
            'complexity', 'II',
            'object_type', 'железная дорога',
            'work_type', 'камеральные'
        ),
        jsonb_build_object(
            'table', 12,
            'row', 2,
            'note', 'Камеральные работы, II категория сложности'
        )
    ) ON CONFLICT DO NOTHING;
    
    -- 5. Стоимость проверки полноты планов в эксплуатирующих организациях
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 75, 'прим. 3',
        'Стоимость проверки полноты планов в эксплуатирующих организациях',
        'служба',
        NULL, 480.00,
        jsonb_build_object(
            'work_type', 'камеральные'
        ),
        jsonb_build_object(
            'table', 75,
            'note', 'Проверка полноты планов'
        )
    ) ON CONFLICT DO NOTHING;
    
    -- 6. Выдача координат и высот исходных пунктов
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 81, 'п. 2, п. 3',
        'Выдача координат и высот исходных пунктов',
        'пункт',
        NULL, 160.00,
        jsonb_build_object(
            'work_type', 'камеральные'
        ),
        jsonb_build_object(
            'table', 81,
            'row', '2-3',
            'note', 'Выдача координат и высот'
        )
    ) ON CONFLICT DO NOTHING;

    -- =====================================================
    -- СМЕТА 2: ИГИ (Инженерно-геологические изыскания)
    -- =====================================================
    
    -- 1. Инженерно-геологическая рекогносцировка
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igi_id, 9, '§1',
        'Инженерно-геологическая рекогносцировка III категория сложности при хорошей проходимости',
        'км',
        28.30, NULL,
        jsonb_build_object(
            'category', 'III',
            'passability', 'хорошая'
        ),
        jsonb_build_object(
            'table', 9,
            'section', '§1',
            'note', 'III категория сложности'
        )
    ) ON CONFLICT DO NOTHING;
    
    -- 2. Маршрутные наблюдения
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igi_id, 10, '§4',
        'Маршрутные наблюдения',
        'км',
        16.30, NULL,
        jsonb_build_object(
            'category', 'III'
        ),
        jsonb_build_object(
            'table', 10,
            'section', '§4'
        )
    ) ON CONFLICT DO NOTHING;
    
    -- 3. Описание точек наблюдений
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igi_id, 11, '§1',
        'Описание точек наблюдений',
        'точка',
        10.20, NULL,
        jsonb_build_object(),
        jsonb_build_object(
            'table', 11,
            'section', '§1'
        )
    ) ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Работы из сметы успешно добавлены в БД';
END $$;

-- Обновляем поисковый индекс для новых работ
UPDATE norm_items 
SET search_text = to_tsvector('russian', work_title)
WHERE search_text IS NULL;

COMMENT ON TABLE norm_items IS 'Нормативные расценки на изыскательские работы (обновлено: добавлены работы из реальной сметы)';
