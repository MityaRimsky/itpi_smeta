-- Таблица пользователей Telegram для доступа к боту
CREATE TABLE IF NOT EXISTS telegram_users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name text,
    last_name text,
    username text,
    telegram_id bigint NOT NULL UNIQUE,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS telegram_users_username_uq
    ON telegram_users (lower(username))
    WHERE username IS NOT NULL;

