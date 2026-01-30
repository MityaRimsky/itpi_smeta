-- Миграция 005: Коэффициенты из СБЦ ИГДИ 2004
-- Общие указания, пункты 8, 15 и приложения

-- Получаем ID документа
DO $$
DECLARE
    v_doc_id UUID;
BEGIN
    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    
    IF v_doc_id IS NULL THEN
        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден. Сначала выполните миграцию 004_norm_docs.sql';
    END IF;

    -- Удаляем существующие коэффициенты для этого документа
    DELETE FROM norm_coeffs WHERE doc_id = v_doc_id;

    -- ========================================
    -- ГОРНЫЕ И ВЫСОКОГОРНЫЕ РАЙОНЫ (Таблица 1)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'MOUNTAIN_1500_1700', 'Горный и высокогорный район с абсолютными высотами от 1500 до 1700 м', 1.10, 'field', 
     '{"altitude_min": 1500, "altitude_max": 1700}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'MOUNTAIN_1700_2000', 'Горный и высокогорный район с абсолютными высотами от 1700 до 2000 м', 1.15, 'field',
     '{"altitude_min": 1700, "altitude_max": 2000}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'MOUNTAIN_2000_3000', 'Горный и высокогорный район с абсолютными высотами от 2000 до 3000 м', 1.20, 'field',
     '{"altitude_min": 2000, "altitude_max": 3000}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'MOUNTAIN_OVER_3000', 'Горный и высокогорный район с абсолютными высотами свыше 3000 м', 1.25, 'field',
     '{"altitude_min": 3000}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- СПЕЦИАЛЬНЫЙ РЕЖИМ ТЕРРИТОРИИ (п.8в)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'SPECIAL_REGIME_1_25', 'Спецрежим территории (пограничные районы, полигоны, аэродромы, действующие стройплощадки, экологически вредные территории)', 1.25, 'field',
     '{"type": "special_regime", "description": "Территории со специальным режимом"}'::jsonb,
     '{"section": "п.8в", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- РАДИОАКТИВНОСТЬ (п.8в)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'RADIATION_1_25', 'Районы с радиоактивностью более 1 мЗв/год (0.1 бэр/год) - минимальный коэффициент', 1.25, 'field',
     '{"radiation_min": 1.0, "unit": "мЗв/год"}'::jsonb,
     '{"section": "п.8в", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'RADIATION_1_50', 'Районы с радиоактивностью более 1 мЗв/год (0.1 бэр/год) - максимальный коэффициент', 1.50, 'field',
     '{"radiation_min": 1.0, "unit": "мЗв/год", "note": "в зависимости от уровня радиоактивности"}'::jsonb,
     '{"section": "п.8в", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- НОЧНОЕ ВРЕМЯ (п.8в)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'NIGHT_TIME_1_35', 'Работы в ночное время (с 22 часов до 6 часов)', 1.35, 'field',
     '{"time_start": "22:00", "time_end": "06:00"}'::jsonb,
     '{"section": "п.8в", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- НЕБЛАГОПРИЯТНЫЙ ПЕРИОД ГОДА (Таблица 2, п.8г)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'UNFAVORABLE_4_5_5', 'Неблагоприятный период 4-5.5 месяцев', 1.20, 'field',
     '{"unfavorable_months_min": 4.0, "unfavorable_months_max": 5.5}'::jsonb,
     '{"table": 2, "section": "п.8г", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'UNFAVORABLE_6_7_5', 'Неблагоприятный период 6-7.5 месяцев', 1.30, 'field',
     '{"unfavorable_months_min": 6.0, "unfavorable_months_max": 7.5}'::jsonb,
     '{"table": 2, "section": "п.8г", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'UNFAVORABLE_8_9_5', 'Неблагоприятный период 8-9.5 месяцев', 1.40, 'field',
     '{"unfavorable_months_min": 8.0, "unfavorable_months_max": 9.5}'::jsonb,
     '{"table": 2, "section": "п.8г", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- РАЙОННЫЕ КОЭФФИЦИЕНТЫ (Таблица 3, п.8д)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'REGION_K_1_05', 'Районный коэффициент к зарплате 1.05', 1.05, 'total',
     '{"salary_coeff": 1.05}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_15', 'Районный коэффициент к зарплате 1.15', 1.08, 'total',
     '{"salary_coeff": 1.15}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_20', 'Районный коэффициент к зарплате 1.20', 1.10, 'total',
     '{"salary_coeff": 1.20}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_25', 'Районный коэффициент к зарплате 1.25', 1.13, 'total',
     '{"salary_coeff": 1.25}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_30', 'Районный коэффициент к зарплате 1.30', 1.15, 'total',
     '{"salary_coeff": 1.30}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_40', 'Районный коэффициент к зарплате 1.40', 1.20, 'total',
     '{"salary_coeff": 1.40}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_50', 'Районный коэффициент к зарплате 1.50', 1.25, 'total',
     '{"salary_coeff": 1.50}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_60', 'Районный коэффициент к зарплате 1.60', 1.30, 'total',
     '{"salary_coeff": 1.60}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_70', 'Районный коэффициент к зарплате 1.70', 1.35, 'total',
     '{"salary_coeff": 1.70}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_80', 'Районный коэффициент к зарплате 1.80', 1.40, 'total',
     '{"salary_coeff": 1.80}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_1_90', 'Районный коэффициент к зарплате 1.90', 1.45, 'total',
     '{"salary_coeff": 1.90}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb),
    
    (v_doc_id, 'REGION_K_2_00', 'Районный коэффициент к зарплате 2.00', 1.50, 'total',
     '{"salary_coeff": 2.00}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ, Приложение 3"}'::jsonb);

    -- ========================================
    -- КРАЙНИЙ СЕВЕР (п.8е)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'FAR_NORTH_1_50', 'Районы Крайнего Севера', 1.50, 'total',
     '{"region_type": "far_north"}'::jsonb,
     '{"section": "п.8е", "note": "ОУ, Приложение 5"}'::jsonb),
    
    (v_doc_id, 'FAR_NORTH_EQUIV_1_25', 'Местности, приравненные к районам Крайнего Севера', 1.25, 'total',
     '{"region_type": "far_north_equivalent"}'::jsonb,
     '{"section": "п.8е", "note": "ОУ, Приложение 5"}'::jsonb),
    
    (v_doc_id, 'SOUTH_REGIONS_1_15', 'Южные районы Иркутской области, Красноярского края, Дальнего Востока, Архангельской и Читинской областей, Республик Бурятия, Карелия, Коми', 1.15, 'total',
     '{"region_type": "south_regions"}'::jsonb,
     '{"section": "п.8е", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- ПОЛЕВЫЕ РАБОТЫ БЕЗ ДОВОЛЬСТВИЯ (п.14)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'NO_FIELD_ALLOWANCE_0_85', 'Полевые работы без выплаты полевого довольствия или командировочных', 0.85, 'field',
     '{"allowance": false}'::jsonb,
     '{"section": "п.14", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'FIELD_ALLOWANCE_CAMERAL_1_15', 'Камеральная обработка в экспедиционных условиях с выплатой полевого довольствия', 1.15, 'office',
     '{"allowance": true, "conditions": "expedition"}'::jsonb,
     '{"section": "п.14", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- ДОПОЛНИТЕЛЬНЫЕ РАБОТЫ (п.15)
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref) VALUES
    (v_doc_id, 'INTERMEDIATE_MATERIALS_1_10', 'Выдача промежуточных материалов изысканий', 1.10, 'total',
     '{"work_type": "intermediate_materials"}'::jsonb,
     '{"section": "п.15а", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'CLASSIFIED_MATERIALS_1_10', 'Камеральные работы с материалами ограниченного пользования', 1.10, 'office',
     '{"work_type": "classified"}'::jsonb,
     '{"section": "п.15б", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'ARTIFICIAL_LIGHTING_1_15', 'Полевые работы с искусственным освещением отсчетных устройств', 1.15, 'field',
     '{"work_type": "artificial_lighting"}'::jsonb,
     '{"section": "п.15в", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'COLOR_PLAN_1_10', 'Составление плана подземных и надземных сооружений в цвете (красках)', 1.10, 'office',
     '{"work_type": "color_plan"}'::jsonb,
     '{"section": "п.15г", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'COMPUTER_TECH_1_20', 'Камеральные и картографические работы с применением компьютерных технологий', 1.20, 'office',
     '{"work_type": "computer_technology"}'::jsonb,
     '{"section": "п.15д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'DUAL_FORMAT_1_75', 'Картографические работы с составлением планов в двух видах: на магнитном и бумажном носителях', 1.75, 'office',
     '{"work_type": "dual_format"}'::jsonb,
     '{"section": "п.15е", "note": "ОУ"}'::jsonb);

    RAISE NOTICE 'Успешно добавлено коэффициентов: %', (SELECT COUNT(*) FROM norm_coeffs WHERE doc_id = v_doc_id);
END $$;

-- Проверка
SELECT 
    code,
    name,
    value,
    apply_to,
    conditions->>'type' as condition_type,
    source_ref->>'section' as section
FROM norm_coeffs 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
ORDER BY code;
