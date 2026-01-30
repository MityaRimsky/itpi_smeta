#!/bin/bash

# Скрипт для применения миграций к Supabase ITPI
# Использование: ./apply_migration.sh [путь_к_миграции]

# Загружаем переменные окружения
if [ -f .env.supabase ]; then
    export $(cat .env.supabase | grep -v '^#' | xargs)
fi

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Проверяем наличие psql
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ psql не найден. Установите PostgreSQL client.${NC}"
    exit 1
fi

# Определяем файл миграции
MIGRATION_FILE="${1}"

if [ -z "$MIGRATION_FILE" ]; then
    echo -e "${RED}❌ Укажите файл миграции${NC}"
    echo -e "${YELLOW}Использование: ./apply_migration.sh путь/к/миграции.sql${NC}"
    exit 1
fi

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}❌ Файл миграции не найден: $MIGRATION_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📝 Применяем миграцию: $MIGRATION_FILE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# Проверяем SSH туннель
if ! lsof -i :$DB_PORT > /dev/null 2>&1; then
    echo -e "${RED}❌ SSH туннель не активен на порту $DB_PORT${NC}"
    echo -e "${YELLOW}Запустите туннель: ssh itpi${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} SSH туннель активен"
echo ""

# Применяем миграцию через psql
echo -e "${YELLOW}Выполняем SQL...${NC}"
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --pset pager=off \
    -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Миграция успешно применена!${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Ошибка при применении миграции${NC}"
    echo ""
    echo -e "${YELLOW}💡 Альтернативные методы:${NC}"
    echo -e "   1. Через MCP сервер (рекомендуется):"
    echo -e "      ${BLUE}itpi_execute_migration${NC}"
    echo ""
    echo -e "   2. Через SSH + Docker:"
    echo -e "      ${BLUE}ssh root@147.45.143.147 \"docker exec supabase-db psql -U postgres -d postgres -f /path/to/migration.sql\"${NC}"
    echo ""
    exit 1
fi
