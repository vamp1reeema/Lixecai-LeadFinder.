"""Запускай локально в Termux. StringSession — секрет, не публикуй её."""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("Telegram API ID: ").strip())
api_hash = input("Telegram API Hash: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\nСкопируй строку ниже напрямую в GitHub Secret TELEGRAM_SESSION.\n")
    print(client.session.save())
    print("\nНе отправляй эту строку в чат и не добавляй её в репозиторий.")
