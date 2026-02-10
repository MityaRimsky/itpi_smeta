"""
Точка входа для запуска бота
"""

import sys
import os
import logging
from loguru import logger

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import SmetaBot


# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
# Создаем директорию для логов если её нет
os.makedirs("logs", exist_ok=True)

logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="DEBUG"
)

# Снижаем шум сетевых библиотек, оставляя наши прикладные логи.
for noisy_logger in ("httpx", "httpcore", "telegram.ext._utils.networkloop"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def main():
    """Главная функция"""
    try:
        logger.info("=" * 50)
        logger.info("Запуск Telegram бота для расчета смет")
        logger.info("=" * 50)

        # Создаем и запускаем бота
        bot = SmetaBot()
        bot.run()

    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
