-- Миграция 014: K1 коэффициенты из примечаний к таблицам СБЦ ИГДИ 2004
-- Эти коэффициенты применяются к ценам конкретных таблиц

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
    -- ТАБЛИЦА 9: Создание инженерно-топографических планов
    -- Примечание 4: Съемка подземных коммуникаций трубокабелеискателем
    -- ========================================
    
    -- Удаляем старые записи K1 для табл.9 если есть
    DELETE FROM norm_coeffs WHERE doc_id = v_doc_id AND code LIKE 'K1_T9_%';
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref, exclusive_group) VALUES
    -- Примечание 4: Съемка подземных коммуникаций + составление плана
    (v_doc_id, 'K1_T9_NOTE4_UNBUILT', 
     'Съемка подземных коммуникаций трубокабелеискателем - незастроенная территория', 
     1.20, 'price',
     '{"table_no": 9, "note": 4, "territory_type": "незастроенная", "has_underground_comms": true}'::jsonb,
     '{"table": 9, "note": 4, "section": "прим. 4"}'::jsonb,
     'K1_T9_NOTE4'),
    
    (v_doc_id, 'K1_T9_NOTE4_BUILT', 
     'Съемка подземных коммуникаций трубокабелеискателем - застроенная территория', 
     1.55, 'price',
     '{"table_no": 9, "note": 4, "territory_type": "застроенная", "has_underground_comms": true}'::jsonb,
     '{"table": 9, "note": 4, "section": "прим. 4"}'::jsonb,
     'K1_T9_NOTE4'),
    
    (v_doc_id, 'K1_T9_NOTE4_INDUSTRIAL', 
     'Съемка подземных коммуникаций трубокабелеискателем - территория промпредприятия', 
     1.75, 'price',
     '{"table_no": 9, "note": 4, "territory_type": "промпредприятие", "has_underground_comms": true}'::jsonb,
     '{"table": 9, "note": 4, "section": "прим. 4"}'::jsonb,
     'K1_T9_NOTE4'),

    -- Примечание 5: Детальное обследование колодцев и надземных коммуникаций
    -- с составлением эскизов и разрезов опор и узлов
    (v_doc_id, 'K1_T9_NOTE5_DETAILED', 
     'Детальное обследование колодцев/надземных коммуникаций с эскизами и разрезами', 
     1.30, 'price',
     '{"table_no": 9, "note": 5, "has_detailed_wells_sketches": true}'::jsonb,
     '{"table": 9, "note": 5, "section": "прим. 5"}'::jsonb,
     NULL);

    -- ========================================
    -- ТАБЛИЦА 10: Обновление инженерно-топографических планов
    -- ========================================
    
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref, exclusive_group) VALUES
    (v_doc_id, 'K1_T10_UPDATE', 
     'Обновление существующего инженерно-топографического плана', 
     0.50, 'price',
     '{"table_no": 10, "update_mode": true}'::jsonb,
     '{"table": 10, "section": "табл. 10"}'::jsonb,
     NULL);

    RAISE NOTICE 'Успешно добавлено K1 коэффициентов: %', 
        (SELECT COUNT(*) FROM norm_coeffs WHERE doc_id = v_doc_id AND code LIKE 'K1_%');
END $$;

-- Проверка
SELECT 
    code,
    name,
    value,
    apply_to,
    conditions->>'territory_type' as territory,
    conditions->>'has_underground_comms' as underground,
    source_ref->>'section' as section,
    exclusive_group
FROM norm_coeffs 
WHERE doc_id = (SELECT id FROM norm_docs WHERE code = 'SBC_IGDI_2004')
  AND code LIKE 'K1_%'
ORDER BY code;
