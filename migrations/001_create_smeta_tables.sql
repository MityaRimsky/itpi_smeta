-- ============================================================================
-- МИГРАЦИЯ: Создание структуры БД для системы расчета смет
-- Версия: 1.0
-- Дата: 2024-01-28
-- Описание: Базовые таблицы для хранения нормативов, смет и расчетов
-- ============================================================================

-- Включаем расширение для полнотекстового поиска
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- 1. ТАБЛИЦА: norm_docs - Реестр нормативных документов
-- ============================================================================
CREATE TABLE IF NOT EXISTS norm_docs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL,  -- SBC_IGDI_2004
    title text NOT NULL,  -- "СБЦ Инженерно-геодезические изыскания… 2004"
    version text,  -- "2004"
    base_date date,  -- 2001-01-01 (базисный уровень цен)
    source_name text,  -- "PDF/RTF файл"
    description text,  -- Дополнительное описание
    is_active boolean DEFAULT true,  -- Активен ли документ
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE norm_docs IS 'Реестр нормативных документов (СБЦ, расценки)';
COMMENT ON COLUMN norm_docs.code IS 'Уникальный код документа';
COMMENT ON COLUMN norm_docs.base_date IS 'Базисный уровень цен (обычно 01.01.2001)';

-- ============================================================================
-- 2. ТАБЛИЦА: norm_items - Расценки (основные строки таблиц СБЦ)
-- ============================================================================
CREATE TABLE IF NOT EXISTS norm_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id uuid NOT NULL REFERENCES norm_docs(id) ON DELETE CASCADE,
    
    -- Идентификация расценки
    table_no int,  -- Номер таблицы (например 9)
    section text,  -- §5 или пусто
    work_title text NOT NULL,  -- Нормативное наименование работы
    
    -- Единица измерения и цены
    unit text NOT NULL,  -- га, км, пункт, проверка, м и т.д.
    price numeric(14,2),  -- Если одна цена
    price_field numeric(14,2),  -- Если отдельно полевые работы
    price_office numeric(14,2),  -- Если отдельно камеральные работы
    
    -- Параметры и условия применения
    params jsonb DEFAULT '{}'::jsonb,  -- масштаб/категория/диапазоны "до/свыше"
    notes text,  -- Примечание к строке
    source_ref jsonb DEFAULT '{}'::jsonb,  -- Для обоснования: { "table":9, "note":3, "ou":"п.8в" }
    
    -- Полнотекстовый поиск
    search_text tsvector,  -- Автоматически заполняется триггером
    
    -- Популярность (для комбинированного поиска)
    usage_count int DEFAULT 0,  -- Сколько раз использовалась
    popularity_score int DEFAULT 0,  -- Рейтинг популярности
    
    -- Метаданные
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE norm_items IS 'Расценки из нормативных документов';
COMMENT ON COLUMN norm_items.work_title IS 'Название работы для поиска';
COMMENT ON COLUMN norm_items.params IS 'JSON с параметрами: масштаб, категория, высота сечения и т.д.';
COMMENT ON COLUMN norm_items.search_text IS 'Полнотекстовый поиск по названию и параметрам';
COMMENT ON COLUMN norm_items.usage_count IS 'Счетчик использования для определения популярности';

-- ============================================================================
-- 3. ТАБЛИЦА: norm_addons - Добавочные начисления
-- ============================================================================
CREATE TABLE IF NOT EXISTS norm_addons (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id uuid NOT NULL REFERENCES norm_docs(id) ON DELETE CASCADE,
    
    -- Идентификация
    code text NOT NULL,  -- ORG_LIQ_6PCT, PLAN_CHECK_480, INTERNAL_TRANSPORT_T4
    name text NOT NULL,  -- Человекочитаемое название
    
    -- Тип расчета
    calc_type text NOT NULL CHECK (calc_type IN ('fixed', 'per_unit', 'percent')),
    value numeric(14,6) NOT NULL,  -- 480 для fixed/per_unit, 0.06 для percent
    unit text,  -- "руб", "организация", "%"
    
    -- К чему применяется
    base_type text NOT NULL CHECK (base_type IN ('field', 'office', 'field_plus_office', 'field_plus_internal', 'subtotal')),
    
    -- Условия применения
    conditions jsonb DEFAULT '{}'::jsonb,  -- { "table":4, "distance_band":"10-15" }
    source_ref jsonb DEFAULT '{}'::jsonb,  -- Ссылка на источник
    
    -- Метаданные
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE norm_addons IS 'Добавочные начисления (фиксированные, за единицу, проценты)';
COMMENT ON COLUMN norm_addons.calc_type IS 'Тип расчета: fixed (фикс), per_unit (за ед.), percent (%)';
COMMENT ON COLUMN norm_addons.base_type IS 'К чему применяется: полевые, камеральные, сумма и т.д.';

-- ============================================================================
-- 4. ТАБЛИЦА: norm_coeffs - Коэффициенты (множители)
-- ============================================================================
CREATE TABLE IF NOT EXISTS norm_coeffs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id uuid NOT NULL REFERENCES norm_docs(id) ON DELETE CASCADE,
    
    -- Идентификация
    code text NOT NULL,  -- SPECIAL_REGIME_1_25, MOUNTAIN_1_15
    name text NOT NULL,  -- "Спецрежим территории 1.25 (25%)"
    
    -- Значение коэффициента
    value numeric(12,6) NOT NULL,  -- 1.25
    
    -- К чему применяется
    apply_to text NOT NULL CHECK (apply_to IN ('field', 'office', 'total', 'price')),
    
    -- Взаимоисключающие группы
    exclusive_group text,  -- Если есть взаимоисключающие коэффициенты
    
    -- Условия применения
    conditions jsonb DEFAULT '{}'::jsonb,  -- Когда применять
    source_ref jsonb DEFAULT '{}'::jsonb,  -- Ссылка на источник
    
    -- Метаданные
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE norm_coeffs IS 'Коэффициенты-множители для расчета стоимости';
COMMENT ON COLUMN norm_coeffs.apply_to IS 'К чему применяется: field (полевые), office (камеральные), total (итог)';
COMMENT ON COLUMN norm_coeffs.exclusive_group IS 'Группа взаимоисключающих коэффициентов';

-- ============================================================================
-- 5. ТАБЛИЦА: projects - Проекты (группировка смет)
-- ============================================================================
CREATE TABLE IF NOT EXISTS projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Основная информация
    title text NOT NULL,  -- "Строительство производства этилбензола..."
    code text,  -- Код проекта
    customer text,  -- Заказчик (АО "НИПИГАЗ")
    contractor text,  -- Подрядчик (ООО "ИТПИ")
    
    -- Статус и метаданные
    status text DEFAULT 'draft' CHECK (status IN ('draft', 'in_progress', 'completed', 'archived')),
    description text,
    
    -- Аудит
    created_by uuid,  -- Ссылка на auth.users
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE projects IS 'Проекты для группировки смет';
COMMENT ON COLUMN projects.status IS 'Статус проекта: draft, in_progress, completed, archived';

-- ============================================================================
-- 6. ТАБЛИЦА: estimates - Шапка сметы
-- ============================================================================
CREATE TABLE IF NOT EXISTS estimates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid REFERENCES projects(id) ON DELETE SET NULL,
    
    -- Основная информация
    title text NOT NULL,  -- "Смета №1 ИГДИ"
    estimate_number text,  -- "Смета 1"
    work_type text,  -- "Инженерно-геодезические изыскания"
    
    -- Нормативная база
    doc_id uuid NOT NULL REFERENCES norm_docs(id),  -- Какой норматив применяем
    currency text DEFAULT 'RUB',
    
    -- Статус
    status text DEFAULT 'draft' CHECK (status IN ('draft', 'final', 'approved', 'archived')),
    
    -- Метаданные проекта
    meta jsonb DEFAULT '{}'::jsonb,  -- заказчик/объект/район/год и т.п.
    
    -- Итоговые суммы (обновляются при пересчете)
    total_field numeric(14,2) DEFAULT 0,  -- Итого полевые работы
    total_office numeric(14,2) DEFAULT 0,  -- Итого камеральные работы
    total_base numeric(14,2) DEFAULT 0,  -- Итого базовая стоимость
    total_with_coeffs numeric(14,2) DEFAULT 0,  -- С учетом коэффициентов
    total_final numeric(14,2) DEFAULT 0,  -- Итоговая стоимость
    
    -- Аудит
    created_by uuid,  -- Ссылка на auth.users
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE estimates IS 'Шапка сметы (документ)';
COMMENT ON COLUMN estimates.meta IS 'JSON с метаданными: заказчик, объект, район, год и т.п.';
COMMENT ON COLUMN estimates.total_final IS 'Итоговая стоимость с учетом всех коэффициентов и надбавок';

-- ============================================================================
-- 7. ТАБЛИЦА: estimate_lines - Строки сметы
-- ============================================================================
CREATE TABLE IF NOT EXISTS estimate_lines (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    estimate_id uuid NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    
    -- Порядок и группировка
    line_no int NOT NULL,  -- Номер строки (1..N)
    section_name text,  -- Название раздела (опционально)
    
    -- Ввод пользователя
    raw_input text,  -- Как ввёл сметчик (для истории)
    
    -- Привязка к норме
    norm_item_id uuid REFERENCES norm_items(id),  -- Выбранная расценка
    title text NOT NULL,  -- Отображаемое название строки
    unit text NOT NULL,  -- Единица измерения
    qty numeric(14,3) NOT NULL DEFAULT 1,  -- Объем работ
    
    -- Базовые цены
    price_field numeric(14,2),  -- Базовая цена полевых работ
    price_office numeric(14,2),  -- Базовая цена камеральных работ
    base_cost_field numeric(14,2),  -- qty * price_field
    base_cost_office numeric(14,2),  -- qty * price_office
    
    -- Параметры строки
    line_params jsonb DEFAULT '{}'::jsonb,  -- масштаб/категория/дистанция и т.п.
    
    -- Применённые коэффициенты и надбавки
    applied_coeffs jsonb DEFAULT '[]'::jsonb,  -- [{"code":"K1", "value":1.25, "base":"field"}]
    applied_addons jsonb DEFAULT '[]'::jsonb,  -- [{"code":"ORG_LIQ", "value":0.06}]
    
    -- Детальная раскладка расчета
    calc_breakdown jsonb DEFAULT '{}'::jsonb,  -- Промежуточные суммы, базы для %
    
    -- Итоговая стоимость строки
    cost_field_final numeric(14,2),  -- Полевые с коэффициентами
    cost_office_final numeric(14,2),  -- Камеральные с коэффициентами
    cost_total numeric(14,2),  -- Итого по строке
    
    -- Обоснование
    justification text,  -- Человекочитаемое обоснование (табл/пункт/примечание)
    confidence numeric(5,4),  -- Уверенность подбора нормы (0..1)
    
    -- Метаданные
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE estimate_lines IS 'Строки сметы с расчетами и обоснованиями';
COMMENT ON COLUMN estimate_lines.raw_input IS 'Исходный ввод пользователя для истории';
COMMENT ON COLUMN estimate_lines.calc_breakdown IS 'Детальная раскладка: базы, проценты, промежуточные суммы';
COMMENT ON COLUMN estimate_lines.confidence IS 'Уверенность AI в подборе нормы (0-1)';

-- ============================================================================
-- 8. ТАБЛИЦА: estimate_templates - Шаблоны смет
-- ============================================================================
CREATE TABLE IF NOT EXISTS estimate_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Основная информация
    name text NOT NULL,  -- "ИГДИ стандартный", "ИГИ с бурением"
    description text,
    work_type text,  -- "Инженерно-геодезические изыскания"
    doc_id uuid REFERENCES norm_docs(id),  -- Базовый норматив
    
    -- Популярность
    usage_count int DEFAULT 0,
    is_public boolean DEFAULT false,  -- Доступен всем или только создателю
    
    -- Аудит
    created_by uuid,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE estimate_templates IS 'Шаблоны смет для быстрого создания';
COMMENT ON COLUMN estimate_templates.is_public IS 'Публичный шаблон (доступен всем) или приватный';

-- ============================================================================
-- 9. ТАБЛИЦА: template_sections - Разделы шаблонов
-- ============================================================================
CREATE TABLE IF NOT EXISTS template_sections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id uuid NOT NULL REFERENCES estimate_templates(id) ON DELETE CASCADE,
    
    -- Структура
    section_no int NOT NULL,  -- Порядковый номер раздела
    section_name text NOT NULL,  -- "1. Полевые работы"
    
    -- Строки раздела
    norm_item_id uuid REFERENCES norm_items(id),
    title text NOT NULL,
    unit text NOT NULL,
    default_qty numeric(14,3),  -- Объем по умолчанию
    
    -- Параметры по умолчанию
    default_params jsonb DEFAULT '{}'::jsonb,
    
    -- Метаданные
    created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE template_sections IS 'Разделы и строки шаблонов смет';
COMMENT ON COLUMN template_sections.default_qty IS 'Объем работ по умолчанию (можно изменить при создании сметы)';

-- ============================================================================
-- 10. ТАБЛИЦА: inflation_indices - Индексы изменения стоимости
-- ============================================================================
CREATE TABLE IF NOT EXISTS inflation_indices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Период
    period_year int NOT NULL,
    period_quarter int CHECK (period_quarter BETWEEN 1 AND 4),
    period_month int CHECK (period_month BETWEEN 1 AND 12),
    
    -- Индекс
    index_value numeric(10,4) NOT NULL,  -- 5.83, 66.38 и т.д.
    
    -- Тип работ
    work_type text,  -- "ИГДИ", "ИГИ", "все"
    region text,  -- Регион (если региональный индекс)
    
    -- Источник
    source_document text,  -- "Письмо Минстроя России от 07.03.2024 N 13023-ИФ/09"
    
    -- Метаданные
    created_at timestamptz DEFAULT now(),
    
    -- Уникальность по периоду и типу работ
    UNIQUE(period_year, period_quarter, work_type, region)
);

COMMENT ON TABLE inflation_indices IS 'Индексы изменения сметной стоимости изыскательских работ';
COMMENT ON COLUMN inflation_indices.index_value IS 'Коэффициент пересчета (например, 5.83 для 2024 Q1)';

-- ============================================================================
-- 11. ТАБЛИЦА: regional_coeffs - Районные коэффициенты
-- ============================================================================
CREATE TABLE IF NOT EXISTS regional_coeffs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- География
    region_name text NOT NULL,  -- "Республика Татарстан"
    region_code text,  -- "RU-TA"
    
    -- Коэффициенты
    salary_coeff numeric(5,2) NOT NULL,  -- 1.15 (к зарплате)
    estimate_coeff numeric(5,2) NOT NULL,  -- 1.08 (к итогу сметы)
    
    -- Тип территории
    territory_type text,  -- "Приравненные к районам Крайнего Севера"
    
    -- Источник
    source_document text,  -- "ОУ п.8 д, Табл. 3 п.5 (прил. 4)"
    
    -- Метаданные
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    
    UNIQUE(region_code)
);

COMMENT ON TABLE regional_coeffs IS 'Районные коэффициенты к заработной плате и сметам';
COMMENT ON COLUMN regional_coeffs.salary_coeff IS 'Коэффициент к заработной плате (например, 1.15)';
COMMENT ON COLUMN regional_coeffs.estimate_coeff IS 'Коэффициент к итогу сметы (например, 1.08)';

-- ============================================================================
-- ИНДЕКСЫ для оптимизации запросов
-- ============================================================================

-- Индексы для norm_items (основная таблица для поиска)
CREATE INDEX idx_norm_items_doc_id ON norm_items(doc_id);
CREATE INDEX idx_norm_items_table_no ON norm_items(table_no);
CREATE INDEX idx_norm_items_search_text ON norm_items USING gin(search_text);
CREATE INDEX idx_norm_items_popularity ON norm_items(popularity_score DESC, usage_count DESC);
CREATE INDEX idx_norm_items_work_title_trgm ON norm_items USING gin(work_title gin_trgm_ops);

-- Индексы для estimate_lines
CREATE INDEX idx_estimate_lines_estimate_id ON estimate_lines(estimate_id);
CREATE INDEX idx_estimate_lines_norm_item_id ON estimate_lines(norm_item_id);
CREATE INDEX idx_estimate_lines_line_no ON estimate_lines(estimate_id, line_no);

-- Индексы для estimates
CREATE INDEX idx_estimates_project_id ON estimates(project_id);
CREATE INDEX idx_estimates_doc_id ON estimates(doc_id);
CREATE INDEX idx_estimates_created_by ON estimates(created_by);
CREATE INDEX idx_estimates_status ON estimates(status);

-- Индексы для projects
CREATE INDEX idx_projects_created_by ON projects(created_by);
CREATE INDEX idx_projects_status ON projects(status);

-- Индексы для шаблонов
CREATE INDEX idx_template_sections_template_id ON template_sections(template_id);
CREATE INDEX idx_estimate_templates_work_type ON estimate_templates(work_type);
CREATE INDEX idx_estimate_templates_public ON estimate_templates(is_public) WHERE is_public = true;

-- Индексы для справочников
CREATE INDEX idx_norm_addons_doc_id ON norm_addons(doc_id);
CREATE INDEX idx_norm_addons_code ON norm_addons(code);
CREATE INDEX idx_norm_coeffs_doc_id ON norm_coeffs(doc_id);
CREATE INDEX idx_norm_coeffs_code ON norm_coeffs(code);

-- Индексы для индексов изменения стоимости
CREATE INDEX idx_inflation_indices_period ON inflation_indices(period_year DESC, period_quarter DESC);
CREATE INDEX idx_inflation_indices_work_type ON inflation_indices(work_type);

-- Индексы для региональных коэффициентов
CREATE INDEX idx_regional_coeffs_region_code ON regional_coeffs(region_code);
CREATE INDEX idx_regional_coeffs_active ON regional_coeffs(is_active) WHERE is_active = true;

-- ============================================================================
-- ТРИГГЕРЫ
-- ============================================================================

-- Триггер для автоматического обновления search_text в norm_items
CREATE OR REPLACE FUNCTION update_norm_items_search_text()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_text := 
        setweight(to_tsvector('russian', COALESCE(NEW.work_title, '')), 'A') ||
        setweight(to_tsvector('russian', COALESCE(NEW.notes, '')), 'B') ||
        setweight(to_tsvector('russian', COALESCE(NEW.params::text, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER norm_items_search_text_update
    BEFORE INSERT OR UPDATE OF work_title, notes, params
    ON norm_items
    FOR EACH ROW
    EXECUTE FUNCTION update_norm_items_search_text();

-- Триггер для обновления популярности norm_items
CREATE OR REPLACE FUNCTION update_norm_item_popularity()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.norm_item_id IS NOT NULL THEN
        UPDATE norm_items 
        SET 
            usage_count = usage_count + 1,
            popularity_score = usage_count + 1,
            updated_at = now()
        WHERE id = NEW.norm_item_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER increment_norm_item_usage
    AFTER INSERT ON estimate_lines
    FOR EACH ROW
    EXECUTE FUNCTION update_norm_item_popularity();

-- Триггер для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Применяем триггер updated_at ко всем таблицам с этим полем
CREATE TRIGGER update_norm_docs_updated_at BEFORE UPDATE ON norm_docs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_norm_items_updated_at BEFORE UPDATE ON norm_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_norm_addons_updated_at BEFORE UPDATE ON norm_addons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_norm_coeffs_updated_at BEFORE UPDATE ON norm_coeffs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_estimates_updated_at BEFORE UPDATE ON estimates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_estimate_lines_updated_at BEFORE UPDATE ON estimate_lines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_estimate_templates_updated_at BEFORE UPDATE ON estimate_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_regional_coeffs_updated_at BEFORE UPDATE ON regional_coeffs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- КОММЕНТАРИИ К СХЕМЕ
-- ============================================================================

COMMENT ON SCHEMA public IS 'Схема для системы расчета смет инженерных изысканий';

-- ============================================================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ============================================================================

-- Вывод информации о созданных объектах
DO $$
BEGIN
    RAISE NOTICE '✅ Миграция 001_create_smeta_tables.sql выполнена успешно';
    RAISE NOTICE '📊 Создано 11 таблиц:';
    RAISE NOTICE '   - norm_docs (нормативные документы)';
    RAISE NOTICE '   - norm_items (расценки)';
    RAISE NOTICE '   - norm_addons (добавочные начисления)';
    RAISE NOTICE '   - norm_coeffs (коэффициенты)';
    RAISE NOTICE '   - projects (проекты)';
    RAISE NOTICE '   - estimates (сметы)';
    RAISE NOTICE '   - estimate_lines (строки смет)';
    RAISE NOTICE '   - estimate_templates (шаблоны)';
    RAISE NOTICE '   - template_sections (разделы шаблонов)';
    RAISE NOTICE '   - inflation_indices (индексы изменения стоимости)';
    RAISE NOTICE '   - regional_coeffs (районные коэффициенты)';
    RAISE NOTICE '🔍 Создано 20+ индексов для оптимизации';
    RAISE NOTICE '⚡ Создано 12 триггеров для автоматизации';
END $$;
