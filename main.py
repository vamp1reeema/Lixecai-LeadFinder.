import asyncio
import logging
import os
import re
import aiohttp
from bs4 import BeautifulSoup

from config import BOT_TOKEN, BOT_CHAT_ID, SETTINGS
from database import connect, get_last_id, set_last_id, get_flag, set_flag
from filters import find_keyword, looks_like_spam
from notifier import send_lead, send_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
SOURCE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")

def extract_messages(page_html, source):
    soup = BeautifulSoup(page_html, "html.parser")
    found = []
    for item in soup.select(".tgme_widget_message_wrap"):
        post = item.get("data-post", "")
        match = re.fullmatch(re.escape(source) + r"/(\d+)", post)
        if not match:
            continue
        text_node = item.select_one(".tgme_widget_message_text")
        if not text_node:
            continue
        message_text = text_node.get_text(" ", strip=True)
        found.append((int(match.group(1)), message_text))
    return sorted(found, key=lambda x: x[0])

async def scan_source(http, conn, source):
    if not isinstance(source, str) or not SOURCE_RE.fullmatch(source):
        logging.warning("Пропущен некорректный username источника: %r", source)
        return

    url = f"https://t.me/s/{source}"
    async with http.get(url) as response:
        if response.status != 200:
            logging.warning("Источник %s недоступен: HTTP %s", source, response.status)
            return
        page = await response.text()

    messages = extract_messages(page, source)
    if not messages:
        logging.info("Публичная страница %s не вернула доступных сообщений", source)
        return

    logging.info("Источник %s: получено сообщений: %s", source, len(messages))
    last_id = get_last_id(conn, source)
    limit = int(SETTINGS.get("scan_limit_per_source", 40))
    new_messages = [m for m in messages if m[0] > last_id][-limit:]
    logging.info("Источник %s: новых сообщений для проверки: %s", source, len(new_messages))

    for message_id, message_text in new_messages:
        keyword = find_keyword(message_text, SETTINGS.get("keywords", []))
        if keyword and not looks_like_spam(
            message_text,
            SETTINGS.get("ignore_words", []),
            int(SETTINGS.get("min_message_length", 20))
        ):
            try:
                await send_lead(
                    http, BOT_TOKEN, BOT_CHAT_ID, source, message_id, message_text, keyword
                )
                logging.info("Уведомление отправлено: %s/%s", source, message_id)
            except Exception:
                logging.exception("Не удалось отправить уведомление; остановка источника")
                return
        set_last_id(conn, source, message_id)

async def run():
    conn = connect()
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LixecaiLeadFinder/1.0)"}
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as http:
            sources = SETTINGS.get("public_sources", [])
            logging.info("Публичных источников в списке: %s", len(sources))
            if get_flag(conn, "telegram_status_sent") != "true":
                await send_status(http, BOT_TOKEN, BOT_CHAT_ID, len(sources))
                set_flag(conn, "telegram_status_sent", "true")
                logging.info("Одноразовое сообщение о подключении успешно отправлено в Telegram")
            for source in sources:
                try:
                    await scan_source(http, conn, source)
                except Exception:
                    logging.exception("Ошибка при проверке источника %s", source)
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(run())
