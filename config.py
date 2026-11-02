import os

# Токен бота из Discord Developer Portal (discord.com/developers)
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")

# Настройки сервера (можно поменять под каждого покупателя)
GUILD_NAME = os.getenv("GUILD_NAME", "Мой сервер")
WELCOME_CHANNEL = os.getenv("WELCOME_CHANNEL", "приветствие")  # имя канала для приветствий
TICKET_CATEGORY = os.getenv("TICKET_CATEGORY", "тикеты")     # категория для тикетов
SUPPORT_ROLE = os.getenv("SUPPORT_ROLE", "Поддержка")        # роль поддержки в тикетах
WELCOME_ROLE = os.getenv("WELCOME_ROLE", "")                 # автороль новичку (пусто = нет)
LOG_CHANNEL = os.getenv("LOG_CHANNEL", "логи")               # канал логов действий

# Экономика
DAILY_REWARD = int(os.getenv("DAILY_REWARD", "500"))
CURRENCY = os.getenv("CURRENCY", "монет")
