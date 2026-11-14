import asyncio
import logging
import aiohttp
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import API_ID, API_HASH, SESSION, BOT_TOKEN, BOT_CHAT_ID, SETTINGS
from database import connect, get_last_id, set_last_id
from filters import find_keyword, looks_like_spam
from notifier import send_lead

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def run():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    conn = connect()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram-сессия недействительна. Создай новую TELEGRAM_SESSION.")

        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as http:
            dialogs = await client.get_dialogs()
            logging.info("Доступно диалогов: %s", len(dialogs))
            for dialog in dialogs:
                if not (dialog.is_group or dialog.is_channel):
                    continue
                entity = dialog.entity
                chat_id = int(entity.id)
                last_id = get_last_id(conn, chat_id)
                title = dialog.name or str(chat_id)
                messages = []
                try:
                    async for msg in client.iter_messages(
                        entity, limit=int(SETTINGS.get("scan_limit_per_chat", 100)),
                        min_id=last_id, reverse=True
                    ):
                        if msg and not msg.out:
                            messages.append(msg)

                    for msg in messages:
                        keyword = find_keyword(msg.message or "", SETTINGS.get("keywords", []))
                        if keyword and not looks_like_spam(
                            msg.message or "", SETTINGS.get("ignore_words", []),
                            int(SETTINGS.get("min_message_length", 20))
                        ):
                            try:
                                await send_lead(http, BOT_TOKEN, BOT_CHAT_ID, title, msg, keyword)
                                logging.info("Отправлено уведомление: %s", title)
                            except Exception:
                                logging.exception("Не удалось отправить уведомление; повторим при следующем запуске")
                                break
                        set_last_id(conn, chat_id, msg.id)
                except Exception:
                    logging.exception("Ошибка чтения чата: %s", title)
    finally:
        await client.disconnect()
        conn.close()

if __name__ == "__main__":
    asyncio.run(run())
