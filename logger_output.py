import logging

from telebot import TeleBot
from config import *

# Инициализируем бота
bot = TeleBot(token=LogConfig.TELEGRAM_TOKEN)

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=UserConfig.CHAT_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        print(f"Failed to send message: {e}")

logging.basicConfig(
    filename='bot.log',             # Имя файла для логов
    filemode='a',                   # Режим записи: 'a' — добавление в конец файла, 'w' — перезапись файла
    format='%(asctime)s - %(levelname)s - %(message)s',  # Формат записи
    level=logging.INFO               # Уровень логирования (INFO, DEBUG, WARNING, ERROR, CRITICAL)
)

def log(msg):
    if not BacktestConfig.enabled and RealTimeConfig.notify:
        send_telegram_message(msg)
    logging.info(msg)
    print(msg)
