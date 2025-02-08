import logging

from telebot import TeleBot
from telebot.types import BotCommand

from config import *

sync_bot = TeleBot(token=LogConfig.TELEGRAM_TOKEN)

logging.basicConfig(level=logging.INFO)

def set_bot_commands_sync():
    commands = [
        BotCommand("start", "Initialize the bot"),
        BotCommand("help", "Display manual"),
    ]
    global sync_bot
    sync_bot.set_my_commands(commands)

def send_telegram_message(message, user_id=None, error=False):
    try:
        if not user_id:
            user_id = ConnectionsConfig.CHAT_ID

        max_length = 4000
        short_text = message if len(message) <= max_length else message[:2000] + "\n...\n" + message[-2000:]

        sync_bot.send_message(chat_id=user_id, text=short_text, parse_mode="Markdown" if not error else None)
    except Exception as e:
        print(f"Failed to send message: {e} | user_id {user_id}")

def log(msg, user=None):
    if not BacktestConfig.enabled and RealTimeConfig.notify:
        send_telegram_message(msg, user)

    logging.info(msg)

def log_error(msg):
    if not BacktestConfig.enabled and RealTimeConfig.notify:
        send_telegram_message(msg, error=True)

    logging.error(f"[Error] {msg}")
