-- Миграция 006: Добавочные начисления из СБЦ ИГДИ 2004
-- Общие указания, пункты 9-13

-- Получаем ID документа
DO $$
DECLARE
    v_doc_id UUID;
BEGIN
    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    
    IF v_doc_id IS NULL THEN
        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден. Сначала выполните миграцию 004_norm_docs.sql';
    END IF;

    -- Удаляем существующие добавочные начисления для этого документа
    DELETE FROM norm_addons WHERE doc_id = v_doc_id;

    -- ========================================
    -- ВНУТРЕННИЙ ТРАНСПОРТ (Таблица 4, п.9)
    -- ========================================
    -- Расходы по внутреннему транспорту в % от сметной стоимости полевых работ
    -- В зависимости от расстояния от базы и стоимости работ
    
    -- Расстояние до 5 км
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_1_1', 'Внутренний транспорт: до 5 км, стоимость до 75 тыс.руб', 'percent', 0.0875, '%', 'field_plus_internal', 
     '{"distance_max": 5, "cost_max": 75000}'::jsonb,
     '{"table": 4, "row": 1, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_1_2', 'Внутренний транспорт: до 5 км, стоимость 75-150 тыс.руб', 'percent', 0.0750, '%', 'field_plus_internal',
     '{"distance_max": 5, "cost_min": 75000, "cost_max": 150000}'::jsonb,
     '{"table": 4, "row": 1, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_1_3', 'Внутренний транспорт: до 5 км, стоимость 150-300 тыс.руб', 'percent', 0.0625, '%', 'field_plus_internal',
     '{"distance_max": 5, "cost_min": 150000, "cost_max": 300000}'::jsonb,
     '{"table": 4, "row": 1, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_1_4', 'Внутренний транспорт: до 5 км, стоимость 300-750 тыс.руб', 'percent', 0.0500, '%', 'field_plus_internal',
     '{"distance_max": 5, "cost_min": 300000, "cost_max": 750000}'::jsonb,
     '{"table": 4, "row": 1, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_1_5', 'Внутренний транспорт: до 5 км, стоимость свыше 750 тыс.руб', 'percent', 0.0375, '%', 'field_plus_internal',
     '{"distance_max": 5, "cost_min": 750000}'::jsonb,
     '{"table": 4, "row": 1, "section": "п.9", "note": "ОУ"}'::jsonb);

    -- Расстояние 5-10 км
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_2_1', 'Внутренний транспорт: 5-10 км, стоимость до 75 тыс.руб', 'percent', 0.1125, '%', 'field_plus_internal',
     '{"distance_min": 5, "distance_max": 10, "cost_max": 75000}'::jsonb,
     '{"table": 4, "row": 2, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_2_2', 'Внутренний транспорт: 5-10 км, стоимость 75-150 тыс.руб', 'percent', 0.1000, '%', 'field_plus_internal',
     '{"distance_min": 5, "distance_max": 10, "cost_min": 75000, "cost_max": 150000}'::jsonb,
     '{"table": 4, "row": 2, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_2_3', 'Внутренний транспорт: 5-10 км, стоимость 150-300 тыс.руб', 'percent', 0.0875, '%', 'field_plus_internal',
     '{"distance_min": 5, "distance_max": 10, "cost_min": 150000, "cost_max": 300000}'::jsonb,
     '{"table": 4, "row": 2, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_2_4', 'Внутренний транспорт: 5-10 км, стоимость 300-750 тыс.руб', 'percent', 0.0750, '%', 'field_plus_internal',
     '{"distance_min": 5, "distance_max": 10, "cost_min": 300000, "cost_max": 750000}'::jsonb,
     '{"table": 4, "row": 2, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_2_5', 'Внутренний транспорт: 5-10 км, стоимость свыше 750 тыс.руб', 'percent', 0.0625, '%', 'field_plus_internal',
     '{"distance_min": 5, "distance_max": 10, "cost_min": 750000}'::jsonb,
     '{"table": 4, "row": 2, "section": "п.9", "note": "ОУ"}'::jsonb);

    -- Расстояние 10-15 км
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_3_1', 'Внутренний транспорт: 10-15 км, стоимость до 75 тыс.руб', 'percent', 0.1375, '%', 'field_plus_internal',
     '{"distance_min": 10, "distance_max": 15, "cost_max": 75000}'::jsonb,
     '{"table": 4, "row": 3, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_3_2', 'Внутренний транспорт: 10-15 км, стоимость 75-150 тыс.руб', 'percent', 0.1250, '%', 'field_plus_internal',
     '{"distance_min": 10, "distance_max": 15, "cost_min": 75000, "cost_max": 150000}'::jsonb,
     '{"table": 4, "row": 3, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_3_3', 'Внутренний транспорт: 10-15 км, стоимость 150-300 тыс.руб', 'percent', 0.1125, '%', 'field_plus_internal',
     '{"distance_min": 10, "distance_max": 15, "cost_min": 150000, "cost_max": 300000}'::jsonb,
     '{"table": 4, "row": 3, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_3_4', 'Внутренний транспорт: 10-15 км, стоимость 300-750 тыс.руб', 'percent', 0.1000, '%', 'field_plus_internal',
     '{"distance_min": 10, "distance_max": 15, "cost_min": 300000, "cost_max": 750000}'::jsonb,
     '{"table": 4, "row": 3, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_3_5', 'Внутренний транспорт: 10-15 км, стоимость свыше 750 тыс.руб', 'percent', 0.0875, '%', 'field_plus_internal',
     '{"distance_min": 10, "distance_max": 15, "cost_min": 750000}'::jsonb,
     '{"table": 4, "row": 3, "section": "п.9", "note": "ОУ"}'::jsonb);

    -- Расстояние 15-20 км
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_4_1', 'Внутренний транспорт: 15-20 км, стоимость до 75 тыс.руб', 'percent', 0.1625, '%', 'field_plus_internal',
     '{"distance_min": 15, "distance_max": 20, "cost_max": 75000}'::jsonb,
     '{"table": 4, "row": 4, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_4_2', 'Внутренний транспорт: 15-20 км, стоимость 75-150 тыс.руб', 'percent', 0.1500, '%', 'field_plus_internal',
     '{"distance_min": 15, "distance_max": 20, "cost_min": 75000, "cost_max": 150000}'::jsonb,
     '{"table": 4, "row": 4, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_4_3', 'Внутренний транспорт: 15-20 км, стоимость 150-300 тыс.руб', 'percent', 0.1375, '%', 'field_plus_internal',
     '{"distance_min": 15, "distance_max": 20, "cost_min": 150000, "cost_max": 300000}'::jsonb,
     '{"table": 4, "row": 4, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_4_4', 'Внутренний транспорт: 15-20 км, стоимость 300-750 тыс.руб', 'percent', 0.1250, '%', 'field_plus_internal',
     '{"distance_min": 15, "distance_max": 20, "cost_min": 300000, "cost_max": 750000}'::jsonb,
     '{"table": 4, "row": 4, "section": "п.9", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'INTERNAL_TRANSPORT_T4_4_5', 'Внутренний транспорт: 15-20 км, стоимость свыше 750 тыс.руб', 'percent', 0.1125, '%', 'field_plus_internal',
     '{"distance_min": 15, "distance_max": 20, "cost_min": 750000}'::jsonb,
     '{"table": 4, "row": 4, "section": "п.9", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- ВНЕШНИЙ ТРАНСПОРТ (Таблица 5, п.10)
    -- ========================================
    -- Расходы по внешнему транспорту в % от стоимости полевых работ + внутренний транспорт
    
    -- Расстояние 25-100 км
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_1_1', 'Внешний транспорт: 25-100 км, продолжительность до 1 мес', 'percent', 0.1400, '%', 'field_plus_internal',
     '{"distance_min": 25, "distance_max": 100, "duration_max": 1}'::jsonb,
     '{"table": 5, "row": 1, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_1_2', 'Внешний транспорт: 25-100 км, продолжительность 2 мес', 'percent', 0.1150, '%', 'field_plus_internal',
     '{"distance_min": 25, "distance_max": 100, "duration": 2}'::jsonb,
     '{"table": 5, "row": 1, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_1_3', 'Внешний транспорт: 25-100 км, продолжительность 3 мес', 'percent', 0.0910, '%', 'field_plus_internal',
     '{"distance_min": 25, "distance_max": 100, "duration": 3}'::jsonb,
     '{"table": 5, "row": 1, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_1_4', 'Внешний транспорт: 25-100 км, продолжительность 6 мес', 'percent', 0.0450, '%', 'field_plus_internal',
     '{"distance_min": 25, "distance_max": 100, "duration": 6}'::jsonb,
     '{"table": 5, "row": 1, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_1_5', 'Внешний транспорт: 25-100 км, продолжительность 9 мес', 'percent', 0.0350, '%', 'field_plus_internal',
     '{"distance_min": 25, "distance_max": 100, "duration": 9}'::jsonb,
     '{"table": 5, "row": 1, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_1_6', 'Внешний транспорт: 25-100 км, продолжительность 12 мес и более', 'percent', 0.0280, '%', 'field_plus_internal',
     '{"distance_min": 25, "distance_max": 100, "duration_min": 12}'::jsonb,
     '{"table": 5, "row": 1, "section": "п.10", "note": "ОУ"}'::jsonb);

    -- Расстояние 100-300 км
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_2_1', 'Внешний транспорт: 100-300 км, продолжительность до 1 мес', 'percent', 0.1960, '%', 'field_plus_internal',
     '{"distance_min": 100, "distance_max": 300, "duration_max": 1}'::jsonb,
     '{"table": 5, "row": 2, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_2_2', 'Внешний транспорт: 100-300 км, продолжительность 2 мес', 'percent', 0.1540, '%', 'field_plus_internal',
     '{"distance_min": 100, "distance_max": 300, "duration": 2}'::jsonb,
     '{"table": 5, "row": 2, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_2_3', 'Внешний транспорт: 100-300 км, продолжительность 3 мес', 'percent', 0.1270, '%', 'field_plus_internal',
     '{"distance_min": 100, "distance_max": 300, "duration": 3}'::jsonb,
     '{"table": 5, "row": 2, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_2_4', 'Внешний транспорт: 100-300 км, продолжительность 6 мес', 'percent', 0.0620, '%', 'field_plus_internal',
     '{"distance_min": 100, "distance_max": 300, "duration": 6}'::jsonb,
     '{"table": 5, "row": 2, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_2_5', 'Внешний транспорт: 100-300 км, продолжительность 9 мес', 'percent', 0.0480, '%', 'field_plus_internal',
     '{"distance_min": 100, "distance_max": 300, "duration": 9}'::jsonb,
     '{"table": 5, "row": 2, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_2_6', 'Внешний транспорт: 100-300 км, продолжительность 12 мес и более', 'percent', 0.0360, '%', 'field_plus_internal',
     '{"distance_min": 100, "distance_max": 300, "duration_min": 12}'::jsonb,
     '{"table": 5, "row": 2, "section": "п.10", "note": "ОУ"}'::jsonb);

    -- Расстояние 1000-2000 км
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_5_1', 'Внешний транспорт: 1000-2000 км, продолжительность до 1 мес', 'percent', 0.3640, '%', 'field_plus_internal',
     '{"distance_min": 1000, "distance_max": 2000, "duration_max": 1}'::jsonb,
     '{"table": 5, "row": 5, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_5_2', 'Внешний транспорт: 1000-2000 км, продолжительность 2 мес', 'percent', 0.3220, '%', 'field_plus_internal',
     '{"distance_min": 1000, "distance_max": 2000, "duration": 2}'::jsonb,
     '{"table": 5, "row": 5, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_5_3', 'Внешний транспорт: 1000-2000 км, продолжительность 3 мес', 'percent', 0.2800, '%', 'field_plus_internal',
     '{"distance_min": 1000, "distance_max": 2000, "duration": 3}'::jsonb,
     '{"table": 5, "row": 5, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_5_4', 'Внешний транспорт: 1000-2000 км, продолжительность 6 мес', 'percent', 0.1320, '%', 'field_plus_internal',
     '{"distance_min": 1000, "distance_max": 2000, "duration": 6}'::jsonb,
     '{"table": 5, "row": 5, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_5_5', 'Внешний транспорт: 1000-2000 км, продолжительность 9 мес', 'percent', 0.0980, '%', 'field_plus_internal',
     '{"distance_min": 1000, "distance_max": 2000, "duration": 9}'::jsonb,
     '{"table": 5, "row": 5, "section": "п.10", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'EXTERNAL_TRANSPORT_T5_5_6', 'Внешний транспорт: 1000-2000 км, продолжительность 12 мес и более', 'percent', 0.0730, '%', 'field_plus_internal',
     '{"distance_min": 1000, "distance_max": 2000, "duration_min": 12}'::jsonb,
     '{"table": 5, "row": 5, "section": "п.10", "note": "ОУ"}'::jsonb);

    -- ========================================
    -- ОРГАНИЗАЦИЯ И ЛИКВИДАЦИЯ РАБОТ (п.13)
    -- ========================================
    
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'ORG_LIQ_6PCT', 'Организация и ликвидация работ на объекте', 'percent', 0.06, '%', 'field_plus_internal',
     '{}'::jsonb,
     '{"section": "п.13", "note": "ОУ"}'::jsonb);

    -- Коэффициенты к организации и ликвидации (Примечание 1 к п.13)
    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES
    (v_doc_id, 'ORG_LIQ_K_2_5', 'Коэффициент к орг.ликвидации: стоимость до 30 тыс.руб или Крайний Север', 'percent', 0.15, '%', 'field_plus_internal',
     '{"org_liq_coeff": 2.5, "cost_max": 30000, "or_far_north": true}'::jsonb,
     '{"section": "п.13, прим.1", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'ORG_LIQ_K_2_0', 'Коэффициент к орг.ликвидации: стоимость 30-75 тыс.руб', 'percent', 0.12, '%', 'field_plus_internal',
     '{"org_liq_coeff": 2.0, "cost_min": 30000, "cost_max": 75000}'::jsonb,
     '{"section": "п.13, прим.1", "note": "ОУ"}'::jsonb),
    
    (v_doc_id, 'ORG_LIQ_K_1_5', 'Коэффициент к орг.ликвидации: стоимость 75-150 тыс.руб', 'percent', 0.09, '%', 'field_plus_internal',
     '{"org_liq_coeff": 1.5, "cost_min": 75000, "cost_max": 150000}'::jsonb,
     '{"section": "п.13, прим.1", "note": "ОУ"}'::jsonb);

    RAISE NOTICE 'Успешно добавлено добавочных начислений: %', (SELECT COUNT(*) FROM norm_addons WHERE doc_id = v_doc_id);
END $$;

-- Проверка
SELECT 
    code,
    name,
    calc_type,
    value,
    unit,
    base_type,
    conditions->>'distance_min' as dist_min,
    conditions->>'distance_max' as dist_max,
    source_ref->>'table' as table_no,
    source_ref->>'section' as section
FROM norm_addons 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
ORDER BY code
LIMIT 20;
