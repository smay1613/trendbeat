import logging

from telebot import TeleBot
from telebot.types import BotCommand

from config import *

# Инициализируем бота
sync_bot = TeleBot(token=LogConfig.TELEGRAM_TOKEN)


def set_bot_commands_sync(self):
    commands = [
        BotCommand("start", "Initialize the bot"),
        BotCommand("help", "Display manual"),
        # BotCommand("strategies", "Show your strategies"),
        # BotCommand("overview", "Get last market overview"),
        # BotCommand("market_overview_on", "Enable market trend analysis updates"),
        # BotCommand("market_overview_off", "Disable market trend analysis updates"),
        # BotCommand("alerts_on", "Turn on trading alerts"),
        # BotCommand("alerts_off", "Turn off trading alerts"),
    ]
    global sync_bot
    sync_bot.set_my_commands(commands)

def send_telegram_message(message, user_id=None):
    try:
        if not user_id:
            user_id = ConnectionsConfig.CHAT_ID

        sync_bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
    except Exception as e:
        print(f"Failed to send message: {e}")

logging.basicConfig(
    filename='bot.log',             # Имя файла для логов
    filemode='a',                   # Режим записи: 'a' — добавление в конец файла, 'w' — перезапись файла
    format='%(asctime)s - %(levelname)s - %(message)s',  # Формат записи
    level=logging.INFO               # Уровень логирования (INFO, DEBUG, WARNING, ERROR, CRITICAL)
)

def log(msg, user=None):
    if not BacktestConfig.enabled and RealTimeConfig.notify:
        send_telegram_message(msg, user)

    if not user:
        logging.info(msg)
        print(msg)
    else:
        logging.info(msg)
        print(f"Log sent to user {user}")
