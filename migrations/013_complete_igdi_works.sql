-- =====================================================
-- Полный набор работ ИГДИ 2004 из реальных смет
-- =====================================================
-- Источники:
-- 1. Смета НИПИГАЗ (PDF) - 92 га пром.предприятие
-- 2. Смета Новые ресурсы (XLSX) - 12 га смешанная территория
-- =====================================================

DO $$
DECLARE
    doc_igdi_id uuid;
BEGIN
    -- Получаем ID документа СБЦ на ИГДИ 2004
    SELECT id INTO doc_igdi_id FROM norm_docs WHERE code = 'СБЦ-ИГДИ-2004';
    
    IF doc_igdi_id IS NULL THEN
        INSERT INTO norm_docs (code, title, version, base_date)
        VALUES ('СБЦ-ИГДИ-2004', 'Сборник базовых цен на инженерно-геодезические изыскания для строительства', '2004', '2001-01-01')
        RETURNING id INTO doc_igdi_id;
    END IF;

    -- =====================================================
    -- ТАБЛИЦА 8: Опорные геодезические сети
    -- =====================================================
    
    -- Плановая опорная сеть (полевые работы)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 8, 'п. 3',
        'Создание плановой опорной геодезической сети 2 разряда',
        'пункт',
        6426.00, NULL,
        jsonb_build_object(
            'category', 'II',
            'network_type', 'плановая',
            'class', '2 разряд',
            'work_type', 'полевые'
        ),
        jsonb_build_object('table', 8, 'row', 3, 'note', 'прим. 2')
    ) ON CONFLICT DO NOTHING;
    
    -- Плановая опорная сеть (камеральные работы)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 8, 'п. 3',
        'Создание плановой опорной геодезической сети 2 разряда (камеральные работы)',
        'пункт',
        NULL, 2538.00,
        jsonb_build_object(
            'category', 'II',
            'network_type', 'плановая',
            'class', '2 разряд',
            'work_type', 'камеральные'
        ),
        jsonb_build_object('table', 8, 'row', 3)
    ) ON CONFLICT DO NOTHING;
    
    -- Высотная опорная сеть (полевые работы)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 8, 'п. 4',
        'Создание высотной опорной геодезической сети IV класса',
        'пункт',
        1897.00, NULL,
        jsonb_build_object(
            'category', 'II',
            'network_type', 'высотная',
            'class', 'IV класс',
            'work_type', 'полевые'
        ),
        jsonb_build_object('table', 8, 'row', 4)
    ) ON CONFLICT DO NOTHING;
    
    -- Высотная опорная сеть (камеральные работы)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 8, 'п. 4',
        'Создание высотной опорной геодезической сети IV класса (камеральные работы)',
        'пункт',
        NULL, 428.00,
        jsonb_build_object(
            'category', 'II',
            'network_type', 'высотная',
            'class', 'IV класс',
            'work_type', 'камеральные'
        ),
        jsonb_build_object('table', 8, 'row', 4)
    ) ON CONFLICT DO NOTHING;

    -- =====================================================
    -- ТАБЛИЦА 9: Топографические планы
    -- =====================================================
    
    -- Топоплан 1:500 промпредприятие (полевые) - уже есть в 012
    -- Добавляем вариант для незастроенной территории
    
    -- Топоплан 1:500 незастроенная территория (полевые)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 9, 'п. 5',
        'Создание инженерно-топографического плана м-ба 1:500, высота сечения рельефа 0,5м (незастроенная территория) со съемкой подземных коммуникаций',
        'га',
        2432.00, NULL,
        jsonb_build_object(
            'scale', '1:500',
            'category', 'II',
            'territory', 'незастроенная',
            'relief_section', '0.5м',
            'underground_survey', true,
            'work_type', 'полевые'
        ),
        jsonb_build_object('table', 9, 'row', 5, 'note', 'прим. 4, незастроенная территория')
    ) ON CONFLICT DO NOTHING;
    
    -- Топоплан 1:500 незастроенная территория (камеральные)
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 9, 'п. 5',
        'Создание инженерно-топографического плана м-ба 1:500 сечение рельефа 0,5 (незастроенная территория, составление плана в цвете с применением компьютерных технологий)',
        'га',
        NULL, 589.00,
        jsonb_build_object(
            'scale', '1:500',
            'category', 'II',
            'territory', 'незастроенная',
            'relief_section', '0.5м',
            'color_plan', true,
            'computer_tech', true,
            'work_type', 'камеральные'
        ),
        jsonb_build_object('table', 9, 'row', 5, 'note', 'ОУ 15д, г, незастроенная территория')
    ) ON CONFLICT DO NOTHING;

    -- =====================================================
    -- ТАБЛИЦА 48: Привязка скважин
    -- =====================================================
    
    INSERT INTO norm_items (
        doc_id, table_no, section, work_title, unit,
        price_field, price_office, params, source_ref
    ) VALUES (
        doc_igdi_id, 48, 'п. 1',
        'Планово-высотная привязка геологических скважин (до 50 м между скважинами)',
        'скважина',
        111.00, NULL,
        jsonb_build_object(
            'category', 'II',
            'distance', 'до 50 м',
            'work_type', 'полевые'
        ),
        jsonb_build_object('table', 48, 'row', 1)
    ) ON CONFLICT DO NOTHING;

    -- =====================================================
    -- Добавляем синонимы для поиска
    -- =====================================================
    
    -- Синонимы для опорных сетей
    INSERT INTO search_synonyms (term, synonyms, category) VALUES
    ('плановая сеть', ARRAY['плановая опорная сеть', 'ОГС плановая', 'геодезическая сеть плановая', 'триангуляция'], 'геодезия'),
    ('высотная сеть', ARRAY['высотная опорная сеть', 'ОГС высотная', 'нивелирная сеть', 'нивелирование'], 'геодезия'),
    ('опорная сеть', ARRAY['ОГС', 'опорная геодезическая сеть', 'геодезическая основа'], 'геодезия'),
    ('привязка скважин', ARRAY['привязка геологических скважин', 'планово-высотная привязка', 'привязка выработок'], 'геодезия'),
    ('незастроенная территория', ARRAY['незастроенная', 'открытая местность', 'поле', 'пустырь'], 'территория')
    ON CONFLICT (term) DO UPDATE SET synonyms = EXCLUDED.synonyms;

    RAISE NOTICE 'Работы ИГДИ 2004 успешно добавлены';
END $$;

-- =====================================================
-- Добавляем коэффициенты из смет
-- =====================================================

DO $$
DECLARE
    doc_igdi_id uuid;
BEGIN
    SELECT id INTO doc_igdi_id FROM norm_docs WHERE code = 'СБЦ-ИГДИ-2004';

    -- Коэффициент для промышленного предприятия (К1 = 1.75)
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'TERRITORY_INDUSTRIAL_1_75',
        'Территория промышленного предприятия',
        1.75,
        'price',
        jsonb_build_object('territory', 'промпредприятие'),
        jsonb_build_object('table', 9, 'note', 'прим. 4')
    ) ON CONFLICT DO NOTHING;
    
    -- Коэффициент для незастроенной территории (К1 = 1.2)
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'TERRITORY_UNDEVELOPED_1_2',
        'Незастроенная территория',
        1.20,
        'price',
        jsonb_build_object('territory', 'незастроенная'),
        jsonb_build_object('table', 9, 'note', 'прим. 4')
    ) ON CONFLICT DO NOTHING;
    
    -- Коэффициент для подземных коммуникаций (К2 = 1.3)
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'UNDERGROUND_SURVEY_1_3',
        'Съемка подземных коммуникаций',
        1.30,
        'price',
        jsonb_build_object('underground_survey', true),
        jsonb_build_object('table', 9, 'note', 'прим. 4')
    ) ON CONFLICT DO NOTHING;
    
    -- Коэффициент для эскизов опор (К3 = 1.1)
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'SKETCH_SUPPORTS_1_1',
        'Эскизирование опор',
        1.10,
        'price',
        jsonb_build_object('sketch_supports', true),
        jsonb_build_object('table', 9, 'note', 'прим. 5')
    ) ON CONFLICT DO NOTHING;
    
    -- Коэффициент для обновления (К = 0.5)
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'UPDATE_0_5',
        'Обновление топоплана',
        0.50,
        'price',
        jsonb_build_object('update', true),
        jsonb_build_object('table', 9, 'note', 'прим. 3')
    ) ON CONFLICT DO NOTHING;
    
    -- Коэффициент для цветного плана (К = 1.2)
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'COLOR_PLAN_1_2',
        'Составление плана в цвете',
        1.20,
        'price',
        jsonb_build_object('color_plan', true),
        jsonb_build_object('ou', '15д')
    ) ON CONFLICT DO NOTHING;
    
    -- Коэффициент для компьютерных технологий (К = 1.1)
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'COMPUTER_TECH_1_1',
        'Применение компьютерных технологий',
        1.10,
        'price',
        jsonb_build_object('computer_tech', true),
        jsonb_build_object('ou', '15г')
    ) ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Коэффициенты ИГДИ 2004 успешно добавлены';
END $$;

-- =====================================================
-- Добавляем прочие расходы (addons)
-- =====================================================

DO $$
DECLARE
    doc_igdi_id uuid;
BEGIN
    SELECT id INTO doc_igdi_id FROM norm_docs WHERE code = 'СБЦ-ИГДИ-2004';

    -- Районный коэффициент 8%
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'REGIONAL_COEFF_8PCT',
        'Удорожание полевых работ за счет районного коэффициента',
        'percent',
        0.08,
        '%',
        'field',
        jsonb_build_object('regional_coeff', 1.15),
        jsonb_build_object('table', 3, 'row', 5, 'note', 'д ОУ')
    ) ON CONFLICT DO NOTHING;
    
    -- Внутренний транспорт 10-15 км = 13.75%
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'INTERNAL_TRANSPORT_10_15KM',
        'Расходы по внутреннему транспорту (10-15 км от базы)',
        'percent',
        0.1375,
        '%',
        'field',
        jsonb_build_object('distance_band', '10-15 км'),
        jsonb_build_object('table', 4, 'row', 4)
    ) ON CONFLICT DO NOTHING;
    
    -- Внутренний транспорт 10-15 км = 8.75% (для больших объемов)
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'INTERNAL_TRANSPORT_10_15KM_LARGE',
        'Расходы по внутреннему транспорту (10-15 км, большие объемы)',
        'percent',
        0.0875,
        '%',
        'field',
        jsonb_build_object('distance_band', '10-15 км', 'volume', 'large'),
        jsonb_build_object('table', 4, 'row', 4)
    ) ON CONFLICT DO NOTHING;
    
    -- Внешний транспорт 1000-2000 км, 1 мес = 36.4%
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'EXTERNAL_TRANSPORT_1000_2000KM_1M',
        'Расходы по внешнему транспорту (1000-2000 км, 1 мес)',
        'percent',
        0.364,
        '%',
        'field_plus_internal',
        jsonb_build_object('distance_band', '1000-2000 км', 'duration', '1 мес'),
        jsonb_build_object('table', 5, 'row', 4)
    ) ON CONFLICT DO NOTHING;
    
    -- Внешний транспорт 1000-2000 км, 2 мес = 32.2%
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'EXTERNAL_TRANSPORT_1000_2000KM_2M',
        'Расходы по внешнему транспорту (1000-2000 км, 2 мес)',
        'percent',
        0.322,
        '%',
        'field_plus_internal',
        jsonb_build_object('distance_band', '1000-2000 км', 'duration', '2 мес'),
        jsonb_build_object('table', 5, 'row', 5)
    ) ON CONFLICT DO NOTHING;
    
    -- Организация и ликвидация 6%
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'ORG_LIQ_6PCT',
        'Расходы на организацию и ликвидацию полевых работ',
        'percent',
        0.06,
        '%',
        'field_plus_internal',
        jsonb_build_object(),
        jsonb_build_object('ou', 'п. 13')
    ) ON CONFLICT DO NOTHING;
    
    -- Спецрежим территории 25%
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'SPECIAL_REGIME_25PCT',
        'Специальный режим территории',
        'percent',
        0.25,
        '%',
        'field',
        jsonb_build_object('special_regime', true),
        jsonb_build_object('ou', 'п. 8 в')
    ) ON CONFLICT DO NOTHING;
    
    -- Выдача промежуточных материалов 10%
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref)
    VALUES (
        doc_igdi_id,
        'INTERIM_MATERIALS_10PCT',
        'Выдача промежуточных материалов изысканий',
        'percent',
        0.10,
        '%',
        'field',
        jsonb_build_object('interim_materials', true),
        jsonb_build_object('ou', 'п. 15 а')
    ) ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Прочие расходы ИГДИ 2004 успешно добавлены';
END $$;

-- =====================================================
-- Добавляем индексы изменения стоимости
-- =====================================================

INSERT INTO inflation_indices (period_year, period_quarter, index_value, work_type, source_document)
VALUES 
    (2024, 1, 5.83, 'ИГДИ', 'Письмо Минстроя России от 07.03.2024 N 13023-ИФ/09'),
    (2025, 3, 6.70, 'ИГДИ', 'Письмо Минстроя РФ № 41280-ИФ/09 от 16.07.2025')
ON CONFLICT (period_year, period_quarter, work_type, region) DO UPDATE 
SET index_value = EXCLUDED.index_value, source_document = EXCLUDED.source_document;

COMMENT ON TABLE norm_items IS 'Нормативные расценки ИГДИ 2004 (обновлено: полный набор из реальных смет)';
