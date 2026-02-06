-- Миграция 015: Дополнительные коэффициенты и надбавки для полного соответствия сметам
-- Добавляет надбавки-строки для удорожаний, регистрацию/ИСОГД, колонку category

-- Получаем ID документа
DO $$
DECLARE
    v_doc_id UUID;
BEGIN
    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    
    IF v_doc_id IS NULL THEN
        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден';
    END IF;

    -- ========================================
    -- НАДБАВКИ-СТРОКИ ДЛЯ УДОРОЖАНИЙ (выводятся отдельными строками в смете)
    -- ========================================
    
    -- Удаляем если уже есть
    DELETE FROM norm_addons WHERE doc_id = v_doc_id AND code LIKE 'SEASONAL_ADDON%';
    DELETE FROM norm_addons WHERE doc_id = v_doc_id AND code LIKE 'REGIONAL_ADDON%';
    DELETE FROM norm_addons WHERE doc_id = v_doc_id AND code LIKE 'MOUNTAIN_ADDON%';
    DELETE FROM norm_addons WHERE doc_id = v_doc_id AND code LIKE 'INTERMEDIATE_MATERIALS_ADDON%';
    
    -- Сезонные надбавки (табл.2, п.8г) - как отдельные строки
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'SEASONAL_ADDON_4_5_5', 'Удорожание полевых работ за счет сезонного коэффициента (4-5.5 мес)', 'percent', 0.20, '%', 'field',
     '{"unfavorable_months_min": 4.0, "unfavorable_months_max": 5.5}'::jsonb,
     '{"table": 2, "section": "п.8г", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'SEASONAL_ADDON_6_7_5', 'Удорожание полевых работ за счет сезонного коэффициента (6-7.5 мес)', 'percent', 0.30, '%', 'field',
     '{"unfavorable_months_min": 6.0, "unfavorable_months_max": 7.5}'::jsonb,
     '{"table": 2, "section": "п.8г", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'SEASONAL_ADDON_8_9_5', 'Удорожание полевых работ за счет сезонного коэффициента (8-9.5 мес)', 'percent', 0.40, '%', 'field',
     '{"unfavorable_months_min": 8.0, "unfavorable_months_max": 9.5}'::jsonb,
     '{"table": 2, "section": "п.8г", "note": "ОУ"}'::jsonb);

    -- Районные надбавки (табл.3, п.8д) - как отдельные строки
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'REGIONAL_ADDON_1_05', 'Удорожание за счет районного коэффициента к зарплате 1.05', 'percent', 0.05, '%', 'subtotal',
     '{"salary_coeff": 1.05}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_15', 'Удорожание за счет районного коэффициента к зарплате 1.15', 'percent', 0.08, '%', 'subtotal',
     '{"salary_coeff": 1.15}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_20', 'Удорожание за счет районного коэффициента к зарплате 1.20', 'percent', 0.10, '%', 'subtotal',
     '{"salary_coeff": 1.20}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_30', 'Удорожание за счет районного коэффициента к зарплате 1.30', 'percent', 0.15, '%', 'subtotal',
     '{"salary_coeff": 1.30}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_40', 'Удорожание за счет районного коэффициента к зарплате 1.40', 'percent', 0.20, '%', 'subtotal',
     '{"salary_coeff": 1.40}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_50', 'Удорожание за счет районного коэффициента к зарплате 1.50', 'percent', 0.25, '%', 'subtotal',
     '{"salary_coeff": 1.50}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_60', 'Удорожание за счет районного коэффициента к зарплате 1.60', 'percent', 0.30, '%', 'subtotal',
     '{"salary_coeff": 1.60}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_70', 'Удорожание за счет районного коэффициента к зарплате 1.70', 'percent', 0.35, '%', 'subtotal',
     '{"salary_coeff": 1.70}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_1_80', 'Удорожание за счет районного коэффициента к зарплате 1.80', 'percent', 0.40, '%', 'subtotal',
     '{"salary_coeff": 1.80}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'REGIONAL_ADDON_2_00', 'Удорожание за счет районного коэффициента к зарплате 2.00', 'percent', 0.50, '%', 'subtotal',
     '{"salary_coeff": 2.00}'::jsonb,
     '{"table": 3, "section": "п.8д", "note": "ОУ"}'::jsonb);

    -- Горные надбавки (табл.1, п.8а) - как отдельные строки
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'MOUNTAIN_ADDON_1500_1700', 'Удорожание за горные районы (1500-1700 м)', 'percent', 0.10, '%', 'field',
     '{"altitude_min": 1500, "altitude_max": 1700}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'MOUNTAIN_ADDON_1700_2000', 'Удорожание за горные районы (1700-2000 м)', 'percent', 0.15, '%', 'field',
     '{"altitude_min": 1700, "altitude_max": 2000}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'MOUNTAIN_ADDON_2000_3000', 'Удорожание за горные районы (2000-3000 м)', 'percent', 0.20, '%', 'field',
     '{"altitude_min": 2000, "altitude_max": 3000}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'MOUNTAIN_ADDON_OVER_3000', 'Удорожание за горные районы (свыше 3000 м)', 'percent', 0.25, '%', 'field',
     '{"altitude_min": 3000}'::jsonb,
     '{"table": 1, "section": "п.8а", "note": "ОУ"}'::jsonb);

    -- Промежуточные материалы (п.15а) - как надбавка
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'INTERMEDIATE_MATERIALS_ADDON', 'Выдача промежуточных материалов изысканий (п.15а)', 'percent', 0.10, '%', 'field_plus_office',
     '{"intermediate_materials": true}'::jsonb,
     '{"section": "п.15а", "note": "ОУ"}'::jsonb);

    -- Крайний Север надбавки (п.8е) - как отдельные строки
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'FAR_NORTH_ADDON', 'Удорожание за районы Крайнего Севера', 'percent', 0.50, '%', 'subtotal',
     '{"region_type": "far_north"}'::jsonb,
     '{"section": "п.8е", "note": "ОУ, Приложение 5"}'::jsonb),
    
    (v_doc_id, 'FAR_NORTH_EQUIV_ADDON', 'Удорожание за местности, приравненные к Крайнему Северу', 'percent', 0.25, '%', 'subtotal',
     '{"region_type": "far_north_equivalent"}'::jsonb,
     '{"section": "п.8е", "note": "ОУ, Приложение 5"}'::jsonb),
    
    (v_doc_id, 'SOUTH_REGIONS_ADDON', 'Удорожание за южные районы Сибири и Дальнего Востока', 'percent', 0.15, '%', 'subtotal',
     '{"region_type": "south_regions"}'::jsonb,
     '{"section": "п.8е", "note": "ОУ"}'::jsonb);

    -- Спецрежим территории (п.8в) - как надбавка
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'SPECIAL_REGIME_ADDON', 'Удорожание за спецрежим территории', 'percent', 0.25, '%', 'field',
     '{"special_regime": true}'::jsonb,
     '{"section": "п.8в", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- РЕГИСТРАЦИЯ / ИСОГД (табл.80, 81)
    -- ========================================
    
    -- Удаляем если уже есть (по table_no)
    DELETE FROM norm_items WHERE doc_id = v_doc_id AND table_no IN (80, 81);
    
    -- Регистрация в органах архитектуры (табл.80)
    INSERT INTO norm_items (doc_id, work_title, unit, price_field, price_office, table_no, section, params) VALUES
    (v_doc_id, 'Регистрация инженерно-топографических планов в органах архитектуры (до 1 га)', 'объект', 0, 850, 80, '§1',
     '{"area_max": 1, "work_type": "registration"}'::jsonb),
    
    (v_doc_id, 'Регистрация инженерно-топографических планов в органах архитектуры (1-5 га)', 'объект', 0, 1200, 80, '§2',
     '{"area_min": 1, "area_max": 5, "work_type": "registration"}'::jsonb),
    
    (v_doc_id, 'Регистрация инженерно-топографических планов в органах архитектуры (5-25 га)', 'объект', 0, 1700, 80, '§3',
     '{"area_min": 5, "area_max": 25, "work_type": "registration"}'::jsonb),
    
    (v_doc_id, 'Регистрация инженерно-топографических планов в органах архитектуры (свыше 25 га)', 'объект', 0, 2500, 80, '§4',
     '{"area_min": 25, "work_type": "registration"}'::jsonb);

    -- Передача данных в ИСОГД (табл.81)
    INSERT INTO norm_items (doc_id, work_title, unit, price_field, price_office, table_no, section, params) VALUES
    (v_doc_id, 'Передача данных в ИСОГД (до 1 га)', 'объект', 0, 650, 81, '§1',
     '{"area_max": 1, "work_type": "isogd"}'::jsonb),
    
    (v_doc_id, 'Передача данных в ИСОГД (1-5 га)', 'объект', 0, 950, 81, '§2',
     '{"area_min": 1, "area_max": 5, "work_type": "isogd"}'::jsonb),
    
    (v_doc_id, 'Передача данных в ИСОГД (5-25 га)', 'объект', 0, 1350, 81, '§3',
     '{"area_min": 5, "area_max": 25, "work_type": "isogd"}'::jsonb),
    
    (v_doc_id, 'Передача данных в ИСОГД (свыше 25 га)', 'объект', 0, 1900, 81, '§4',
     '{"area_min": 25, "work_type": "isogd"}'::jsonb);

    RAISE NOTICE 'Успешно добавлено надбавок: %', 
        (SELECT COUNT(*) FROM norm_addons WHERE doc_id = v_doc_id AND code LIKE '%_ADDON%');
    RAISE NOTICE 'Успешно добавлено работ регистрации/ИСОГД: %', 
        (SELECT COUNT(*) FROM norm_items WHERE doc_id = v_doc_id AND table_no IN (80, 81));
END $$;

-- ========================================
-- ДОБАВИТЬ КОЛОНКУ CATEGORY В ESTIMATE_LINES
-- ========================================

-- Добавляем колонку если не существует
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'estimate_lines' AND column_name = 'category'
    ) THEN
        ALTER TABLE estimate_lines ADD COLUMN category VARCHAR(10);
        RAISE NOTICE 'Колонка category добавлена в estimate_lines';
    ELSE
        RAISE NOTICE 'Колонка category уже существует в estimate_lines';
    END IF;
END $$;

-- Обновляем существующие записи из params->category (если колонка params существует)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'estimate_lines' AND column_name = 'params'
    ) THEN
        UPDATE estimate_lines 
        SET category = params->>'category' 
        WHERE params->>'category' IS NOT NULL AND category IS NULL;
        RAISE NOTICE 'Обновлены записи estimate_lines из params->category';
    ELSE
        RAISE NOTICE 'Колонка params не существует в estimate_lines, пропускаем обновление';
    END IF;
END $$;

-- Проверка добавленных надбавок
SELECT 
    code,
    name,
    calc_type,
    value,
    base_type,
    source_ref->>'section' as section
FROM norm_addons 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
  AND code LIKE '%_ADDON%'
ORDER BY code;
