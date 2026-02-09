-- Миграция 016: Унификация документа СБЦ ИГДИ 2004 и исправление K1 для табл. 8
-- 1) Перенос всех записей из "СБЦ-ИГДИ-2004" в "SBC_IGDI_2004"
-- 2) Добавление K1_T8_NOTE2 (спутниковые системы для плановых опорных сетей)
-- 3) Нормализация conditions.table_no для табличных коэффициентов

DO $$
DECLARE
    v_new_id UUID;
    v_old_id UUID;
BEGIN
    SELECT id INTO v_new_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';
    SELECT id INTO v_old_id FROM norm_docs WHERE code = 'СБЦ-ИГДИ-2004';

    IF v_new_id IS NULL AND v_old_id IS NOT NULL THEN
        UPDATE norm_docs SET code = 'SBC_IGDI_2004' WHERE id = v_old_id;
        v_new_id := v_old_id;
    ELSIF v_new_id IS NOT NULL AND v_old_id IS NOT NULL THEN
        UPDATE norm_items  SET doc_id = v_new_id WHERE doc_id = v_old_id;
        UPDATE norm_coeffs SET doc_id = v_new_id WHERE doc_id = v_old_id;
        UPDATE norm_addons SET doc_id = v_new_id WHERE doc_id = v_old_id;
        DELETE FROM norm_docs WHERE id = v_old_id;
    END IF;

    IF v_new_id IS NULL THEN
        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден. Сначала выполните миграцию 004_norm_docs.sql';
    END IF;

    -- K1 для табл. 8 (прим. 2): применение спутниковых систем
    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, conditions, source_ref, exclusive_group)
    VALUES (
        v_new_id,
        'K1_T8_NOTE2',
        'Применение спутниковых систем при создании плановой опорной сети',
        1.30,
        'price',
        '{"table_no": 8, "note": 2, "use_satellite": true}'::jsonb,
        '{"table": 8, "note": 2, "section": "прим. 2"}'::jsonb,
        'K1_T8_NOTE2'
    ) ON CONFLICT DO NOTHING;

    -- Нормализация conditions.table_no для табличных коэффициентов
    UPDATE norm_coeffs
    SET conditions = jsonb_set(
        COALESCE(conditions, '{}'::jsonb),
        '{table_no}',
        to_jsonb((source_ref->>'table')::int),
        true
    )
    WHERE doc_id = v_new_id
      AND apply_to = 'price'
      AND (conditions->>'table_no' IS NULL OR conditions->>'table_no' = '')
      AND source_ref ? 'table';

    RAISE NOTICE 'Документ и табличные коэффициенты унифицированы';
END $$;
