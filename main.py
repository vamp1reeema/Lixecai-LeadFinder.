import asyncio
import logging
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
    """Extract posts from Telegram's public web preview."""
    soup = BeautifulSoup(page_html, "html.parser")
    found = []

    # Telegram puts data-post on .tgme_widget_message, not necessarily
    # on the surrounding .tgme_widget_message_wrap element.
    for item in soup.select("[data-post]"):
        post = item.get("data-post", "")
        match = re.fullmatch(re.escape(source) + r"/(\d+)", post)
        if not match:
            continue

        text_node = item.select_one(".tgme_widget_message_text")
        if text_node:
            message_text = text_node.get_text(" ", strip=True)
        else:
            message_text = ""

        # Keep textless posts too so media-only posts do not block the
        # cursor forever. They cannot match lead keywords.
        found.append((int(match.group(1)), message_text))

    # A few layouts may put data-post on a wrapper; avoid duplicate IDs.
    unique = {}
    for message_id, message_text in found:
        if message_id not in unique or (not unique[message_id] and message_text):
            unique[message_id] = message_text
    return sorted(unique.items(), key=lambda x: x[0])


def log_page_diagnostics(page, source, content_type):
    soup = BeautifulSoup(page, "html.parser")
    title_node = soup.title
    title = title_node.get_text(" ", strip=True) if title_node else "(no title)"
    data_posts = soup.select("[data-post]")
    wrappers = soup.select(".tgme_widget_message_wrap")
    message_nodes = soup.select(".tgme_widget_message")
    text_nodes = soup.select(".tgme_widget_message_text")
    lowered = page.lower()
    markers = [
        marker for marker in ("captcha", "too many requests", "unavailable",
                              "not found", "unsupported", "cloudflare")
        if marker in lowered
    ]
    logging.info(
        "Диагностика %s: content-type=%s, bytes=%s, title=%r, "
        "data-post=%s, message_nodes=%s, wrappers=%s, text_nodes=%s, markers=%s",
        source, content_type, len(page.encode("utf-8")), title[:160],
        len(data_posts), len(message_nodes), len(wrappers), len(text_nodes),
        markers or "none"
    )
    if not data_posts:
        excerpt = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:350]
        logging.info("Фрагмент ответа %s: %r", source, excerpt or page[:350])


async def scan_source(http, conn, source):
    if not isinstance(source, str) or not SOURCE_RE.fullmatch(source):
        logging.warning("Пропущен некорректный username источника: %r", source)
        return

    url = f"https://t.me/s/{source}"
    async with http.get(url) as response:
        content_type = response.headers.get("Content-Type", "unknown")
        if response.status != 200:
            logging.warning("Источник %s недоступен: HTTP %s", source, response.status)
            return
        page = await response.text()

    log_page_diagnostics(page, source, content_type)
    messages = extract_messages(page, source)
    if not messages:
        logging.warning(
            "Для %s не извлечено ни одного поста; курсор не изменён",
            source
        )
        return

    logging.info(
        "Источник %s: извлечено постов=%s, текстовых=%s",
        source, len(messages), sum(bool(text.strip()) for _, text in messages)
    )
    last_id = get_last_id(conn, source)
    limit = max(1, int(SETTINGS.get("scan_limit_per_source", 40)))
    new_messages = [m for m in messages if m[0] > last_id][-limit:]
    logging.info("Источник %s: новых постов для проверки: %s", source, len(new_messages))

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
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8"
    }
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
