# ITPI Smeta

Проект для работы с базой данных ITPI через Supabase.

## 🚀 Возможности

- **MCP сервер** для работы с Supabase ITPI
- **Миграции через psql** с поддержкой SSH туннеля
- **REST API** доступ к базе данных
- Полная совместимость с проектом Shema

## 📁 Структура проекта

```
itpi_smeta/
├── mcp-servers/
│   └── supabase-itpi-smeta/     # MCP сервер для ITPI
│       ├── index.js              # Основной код сервера
│       ├── package.json
│       ├── .env.example          # Пример конфигурации
│       └── README.md             # Документация MCP
├── apply_migration.sh            # Скрипт для применения миграций
├── .env.supabase                 # Конфигурация подключения (не в git)
└── README.md                     # Этот файл
```

## 🔧 Установка

### 1. MCP сервер

```bash
cd mcp-servers/supabase-itpi-smeta
npm install
cp .env.example .env
# Отредактируйте .env с вашими данными
```

### 2. Конфигурация для миграций

```bash
cp .env.supabase.example .env.supabase
# Отредактируйте .env.supabase с вашими данными
```

## 📝 Использование

### Миграции через psql

```bash
# Запустите SSH туннель
ssh itpi

# Примените миграцию
./apply_migration.sh путь/к/миграции.sql
```

### MCP сервер

Доступные инструменты:
- `itpi_list_tables` - Список таблиц
- `itpi_execute_sql` - Выполнение SQL запросов
- `itpi_execute_migration` - Применение миграций
- `itpi_list_users` - Список пользователей
- `itpi_get_user` - Информация о пользователе

## 🔑 Переменные окружения

### .env.supabase
```bash
DB_HOST="localhost"
DB_PORT="55432"
DB_USER="supabase_admin.{TENANT_ID}"
DB_PASSWORD="your_password"
DB_NAME="postgres"
```

### mcp-servers/supabase-itpi-smeta/.env
```bash
SUPABASE_URL="https://itpi.webtm.ru"
SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
```

## 📚 Документация

- [MCP сервер](mcp-servers/supabase-itpi-smeta/README.md)
- [Установка exec_migration](mcp-servers/supabase-itpi-smeta/INSTALL_EXEC_MIGRATION.md)
- [Инструкции по настройке](mcp-servers/supabase-itpi-smeta/SETUP_INSTRUCTIONS.md)

## 🛠️ Требования

- Node.js >= 18
- PostgreSQL client (psql)
- SSH доступ к серверу ITPI

## 📄 Лицензия

MIT
