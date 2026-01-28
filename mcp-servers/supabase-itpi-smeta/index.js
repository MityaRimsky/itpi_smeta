#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { createClient } from "@supabase/supabase-js";

// Получаем переменные окружения
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error("❌ Ошибка: SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY должны быть установлены");
  process.exit(1);
}

// Создаем клиент Supabase
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// Создаем MCP сервер
const server = new Server(
  {
    name: "supabase-itpi-smeta",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Регистрируем инструменты
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "itpi_list_tables",
        description: "Получить список всех таблиц в схеме public (ITPI проект)",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "itpi_execute_sql",
        description: "Выполнить SQL запрос к базе данных через PostgREST (ITPI проект)",
        inputSchema: {
          type: "object",
          properties: {
            table: {
              type: "string",
              description: "Имя таблицы",
            },
            select: {
              type: "string",
              description: 'Поля для выборки (например: "*" или "id,name,email")',
              default: "*",
            },
            filter: {
              type: "string",
              description: 'Фильтр в формате PostgREST (например: "id=eq.123")',
            },
            order: {
              type: "string",
              description: 'Сортировка (например: "created_at.desc")',
            },
            limit: {
              type: "number",
              description: "Ограничение количества записей",
            },
          },
          required: ["table"],
        },
      },
      {
        name: "itpi_list_users",
        description: "Получить список пользователей из auth.users (ITPI проект)",
        inputSchema: {
          type: "object",
          properties: {
            limit: {
              type: "number",
              description: "Максимальное количество пользователей (по умолчанию 50)",
              default: 50,
            },
          },
          required: [],
        },
      },
      {
        name: "itpi_get_user",
        description: "Получить информацию о конкретном пользователе по ID (ITPI проект)",
        inputSchema: {
          type: "object",
          properties: {
            user_id: {
              type: "string",
              description: "UUID пользователя",
            },
          },
          required: ["user_id"],
        },
      },
      {
        name: "itpi_execute_migration",
        description: "Выполнить SQL миграцию через функцию exec_migration (ITPI проект)",
        inputSchema: {
          type: "object",
          properties: {
            sql: {
              type: "string",
              description: "SQL код миграции для выполнения",
            },
          },
          required: ["sql"],
        },
      },
    ],
  };
});

// Обработчик вызовов инструментов
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "itpi_list_tables": {
        const { data, error } = await supabase.rpc("exec_migration", {
          sql_query: `
            SELECT 
              schemaname,
              tablename,
              tableowner
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
          `,
        });

        if (error) throw error;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      case "itpi_execute_sql": {
        const { table, select = "*", filter, order, limit } = args;

        let query = supabase.from(table).select(select);

        if (filter) {
          const [column, operator, value] = filter.split(/[=.]/);
          query = query.filter(column, operator, value);
        }

        if (order) {
          const [column, direction] = order.split(".");
          query = query.order(column, { ascending: direction !== "desc" });
        }

        if (limit) {
          query = query.limit(limit);
        }

        const { data, error } = await query;

        if (error) throw error;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      case "itpi_list_users": {
        const { limit = 50 } = args;

        const { data, error } = await supabase.auth.admin.listUsers({
          page: 1,
          perPage: limit,
        });

        if (error) throw error;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      case "itpi_get_user": {
        const { user_id } = args;

        const { data, error } = await supabase.auth.admin.getUserById(user_id);

        if (error) throw error;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      case "itpi_execute_migration": {
        const { sql } = args;

        const { data, error } = await supabase.rpc("exec_migration", {
          sql_query: sql,
        });

        if (error) throw error;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                { success: true, message: "Миграция выполнена успешно", result: data },
                null,
                2
              ),
            },
          ],
        };
      }

      default:
        throw new Error(`Неизвестный инструмент: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              error: error.message,
              details: error.details || error.hint || null,
            },
            null,
            2
          ),
        },
      ],
      isError: true,
    };
  }
});

// Запускаем сервер
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("✅ Supabase ITPI Smeta MCP сервер запущен");
}

main().catch((error) => {
  console.error("❌ Ошибка запуска сервера:", error);
  process.exit(1);
});
