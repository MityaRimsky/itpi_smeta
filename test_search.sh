#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Загружаем переменные окружения
if [ -f "mcp-servers/supabase-itpi-smeta/.env" ]; then
    export $(cat mcp-servers/supabase-itpi-smeta/.env | grep -v '^#' | xargs)
else
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    exit 1
fi

echo -e "${BLUE}🔍 Тестирование умного поиска через MCP сервер${NC}"
echo "═══════════════════════════════════════════════════"

# Проверяем доступность Supabase
echo -e "\n${YELLOW}📡 Проверка подключения к Supabase...${NC}"
health_check=$(curl -s -o /dev/null -w "%{http_code}" "${SUPABASE_URL}/rest/v1/" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}")

if [ "$health_check" = "200" ]; then
    echo -e "${GREEN}✅ Supabase доступен${NC}"
else
    echo -e "${RED}❌ Supabase недоступен (HTTP $health_check)${NC}"
    exit 1
fi

# Тест 1: Получение списка таблиц
echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Тест 1: Список таблиц в базе${NC}"
echo -e "${YELLOW}📝 Запрос к itpi_list_tables${NC}"

result=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/itpi_list_tables" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json")

echo -e "${GREEN}✅ Результат:${NC}"
echo "$result" | jq -r '.' 2>/dev/null || echo "$result"

# Тест 2: Статистика по таблицам
echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Тест 2: Количество записей в norm_items${NC}"
echo -e "${YELLOW}📝 Запрос к itpi_execute_sql${NC}"

result=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/itpi_execute_sql" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "table": "norm_items",
        "select": "id,work_title,unit,price",
        "limit": 5
    }')

echo -e "${GREEN}✅ Первые 5 записей:${NC}"
echo "$result" | jq -r '.' 2>/dev/null || echo "$result"

# Тест 3: Поиск через функцию search_norm_items
echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Тест 3: Поиск 'геодезия' через функцию${NC}"
echo -e "${YELLOW}📝 Прямой вызов функции search_norm_items${NC}"

# Создаём временную функцию-обёртку для вызова search_norm_items
result=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/itpi_execute_sql" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "table": "norm_items",
        "select": "work_title,unit,price",
        "filter": "work_title.ilike.*геодез*",
        "limit": 5
    }')

echo -e "${GREEN}✅ Результаты поиска:${NC}"
echo "$result" | jq -r '.' 2>/dev/null || echo "$result"

# Тест 4: Проверка синонимов
echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Тест 4: Проверка таблицы синонимов${NC}"
echo -e "${YELLOW}📝 Запрос к work_synonyms${NC}"

result=$(curl -s "${SUPABASE_URL}/rest/v1/work_synonyms?select=main_term,synonyms,category&limit=3" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}")

echo -e "${GREEN}✅ Синонимы в базе:${NC}"
echo "$result" | jq -r '.' 2>/dev/null || echo "$result"

# Тест 5: Поиск "съемка"
echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Тест 5: Поиск 'съемка'${NC}"
echo -e "${YELLOW}📝 Поиск топографических съёмок${NC}"

result=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/itpi_execute_sql" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "table": "norm_items",
        "select": "work_title,unit,price",
        "filter": "work_title.ilike.*съем*",
        "limit": 5
    }')

echo -e "${GREEN}✅ Результаты:${NC}"
echo "$result" | jq -r '.' 2>/dev/null || echo "$result"

# Тест 6: Статистика всех таблиц
echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Тест 6: Общая статистика базы${NC}"

for table in "norm_docs" "norm_items" "norm_addons" "norm_coeffs" "work_synonyms"; do
    echo -e "\n${YELLOW}📊 Таблица: $table${NC}"
    
    # Получаем заголовки и тело ответа
    response=$(curl -s -D - "${SUPABASE_URL}/rest/v1/${table}?select=count" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Prefer: count=exact")
    
    # Извлекаем количество из заголовка content-range
    count=$(echo "$response" | grep -i "content-range:" | grep -o '/[0-9]*' | tr -d '/')
    
    if [ -n "$count" ]; then
        echo -e "${GREEN}  ✅ Записей: $count${NC}"
    else
        echo -e "${RED}  ❌ Не удалось получить количество${NC}"
        echo -e "${YELLOW}  Ответ сервера:${NC}"
        echo "$response" | head -5
    fi
done

echo -e "\n${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Тестирование завершено!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"

echo -e "\n${BLUE}💡 Для полноценного тестирования функции search_norm_items${NC}"
echo -e "${BLUE}   используйте MCP сервер через Claude Desktop${NC}"
