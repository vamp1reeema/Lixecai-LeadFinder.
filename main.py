import asyncio
import logging
import os
import re
import aiohttp
from bs4 import BeautifulSoup

from config import BOT_TOKEN, BOT_CHAT_ID, SETTINGS
from database import connect, get_last_id, set_last_id
from filters import find_keyword, lead_rejection_reason
from notifier import send_lead, send_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
SOURCE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def extract_messages(page_html, source):
    """Extract posts from Telegram's public web preview."""
    soup = BeautifulSoup(page_html, "html.parser")
    found = []
    for item in soup.select("[data-post]"):
        post = item.get("data-post", "")
        match = re.fullmatch(re.escape(source) + r"/(\d+)", post)
        if not match:
            continue
        text_node = item.select_one(".tgme_widget_message_text")
        message_text = text_node.get_text(" ", strip=True) if text_node else ""
        found.append((int(match.group(1)), message_text))

    unique = {}
    for message_id, message_text in found:
        if message_id not in unique or (not unique[message_id] and message_text):
            unique[message_id] = message_text
    return sorted(unique.items(), key=lambda x: x[0])


async def fetch_source_messages(http, source, limit):
    """Fetch several Telegram preview pages so busy channels do not lose posts."""
    collected = {}
    before = None
    page_count = max(1, min(5, (limit + 19) // 20 + 1))

    for page_number in range(page_count):
        url = f"https://t.me/s/{source}"
        if before is not None:
            url += f"?before={before}"

        async with http.get(url, allow_redirects=True) as response:
            content_type = response.headers.get("Content-Type", "unknown")
            final_url = str(response.url)
            redirect_chain = [
                f"{item.status} -> {item.url}" for item in response.history
            ]
            if response.status != 200:
                raise RuntimeError(
                    f"HTTP {response.status} при чтении {source}; "
                    f"final_url={final_url}; redirects={redirect_chain}"
                )
            page = await response.text()

        if page_number == 0:
            log_page_diagnostics(
                page, source, content_type, final_url, redirect_chain
            )

        page_messages = extract_messages(page, source)
        if not page_messages:
            break

        previous_count = len(collected)
        for message_id, message_text in page_messages:
            if message_id not in collected or (not collected[message_id] and message_text):
                collected[message_id] = message_text

        oldest_id = min(message_id for message_id, _ in page_messages)
        if len(collected) == previous_count or oldest_id <= 1:
            break
        before = oldest_id

        if len(collected) >= limit:
            break

    return sorted(collected.items(), key=lambda item: item[0])[-limit:]


def log_page_diagnostics(page, source, content_type, final_url, redirect_chain):
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
    final_path = response_path = final_url.split("?", 1)[0].rstrip("/")
    expected_path = f"https://t.me/s/{source}"
    if final_path == expected_path:
        page_kind = "telegram_preview_path"
    elif final_path.rstrip("/").endswith("/" + source):
        page_kind = "channel_landing_or_redirect"
    else:
        page_kind = "unexpected_redirect_or_page"

    logging.info(
        "Диагностика %s: content-type=%s, bytes=%s, requested=%s, final_url=%s, "
        "redirects=%s, page_kind=%s, title=%r, data-post=%s, message_nodes=%s, "
        "wrappers=%s, text_nodes=%s, markers=%s",
        source, content_type, len(page.encode("utf-8")),
        expected_path, final_url, redirect_chain or "none", page_kind, title[:160],
        len(data_posts), len(message_nodes), len(wrappers), len(text_nodes),
        markers or "none"
    )
    if not data_posts:
        excerpt = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:350]
        logging.info("Фрагмент ответа %s: %r", source, excerpt or page[:350])


async def scan_source(http, conn, source, test_mode=False):
    stats = {"checked": 0, "leads": 0, "errors": 0, "matches": 0}
    if not isinstance(source, str) or not SOURCE_RE.fullmatch(source):
        logging.warning("Пропущен некорректный username источника: %r", source)
        stats["errors"] += 1
        return stats

    limit = max(1, int(SETTINGS.get("scan_limit_per_source", 40)))
    try:
        messages = await fetch_source_messages(http, source, limit)
    except Exception:
        logging.exception("Не удалось получить публикации источника %s", source)
        stats["errors"] += 1
        return stats
    if not messages:
        logging.warning("Для %s не извлечено ни одного поста", source)
        stats["errors"] += 1
        return stats

    logging.info(
        "Источник %s: извлечено постов=%s, текстовых=%s",
        source, len(messages), sum(bool(text.strip()) for _, text in messages)
    )
    last_id = get_last_id(conn, source)
    if test_mode:
        # Test mode deliberately re-checks the latest posts and never changes
        # the saved cursor, so the normal scanner's state remains untouched.
        selected_messages = messages[-limit:]
        logging.info("ТЕСТ: %s — повторно проверяем последние %s постов без изменения базы",
                     source, len(selected_messages))
    else:
        selected_messages = [m for m in messages if m[0] > last_id][-limit:]
        logging.info("Источник %s: новых постов для проверки: %s",
                     source, len(selected_messages))

    stats["checked"] = len(selected_messages)
    for message_id, message_text in selected_messages:
        keyword = find_keyword(message_text, SETTINGS.get("keywords", []))
        rejection_reason = lead_rejection_reason(
            message_text,
            SETTINGS.get("ignore_words", [])
        )
        is_spam = rejection_reason is not None
        if keyword:
            stats["matches"] += 1
            logging.info(
                "%s Совпадение: %s/%s keyword=%r spam=%s text=%r",
                "ТЕСТ:" if test_mode else "",
                source, message_id, keyword, rejection_reason or "пропущено фильтром", message_text[:240]
            )
        if keyword and not is_spam:
            if test_mode:
                # Dry-run: count eligible leads, but never send duplicate Telegram alerts.
                stats["leads"] += 1
                logging.info(
                    "ТЕСТ: подходящая заявка (НЕ ОТПРАВЛЯЮ): %s/%s keyword=%r text=%r",
                    source, message_id, keyword, message_text[:500]
                )
            else:
                try:
                    await send_lead(
                        http, BOT_TOKEN, BOT_CHAT_ID, source, message_id, message_text, keyword
                    )
                    stats["leads"] += 1
                    logging.info("Уведомление отправлено: %s/%s", source, message_id)
                except Exception:
                    stats["errors"] += 1
                    logging.exception("Не удалось отправить уведомление; остановка источника")
                    return stats

        if not test_mode:
            set_last_id(conn, source, message_id)
    return stats


async def run():
    test_mode = os.getenv("TEST_MODE", "").strip().lower() in ("1", "true", "yes", "on")
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
            logging.info("РЕЖИМ: %s", "ТЕСТОВЫЙ (база не изменяется)" if test_mode else "ОБЫЧНЫЙ")
            total = {"checked": 0, "leads": 0, "errors": 0, "matches": 0}
            for source in sources:
                try:
                    result = await scan_source(http, conn, source, test_mode=test_mode)
                    for key in total:
                        total[key] += result[key]
                except Exception:
                    total["errors"] += 1
                    logging.exception("Ошибка при проверке источника %s", source)

            lead_count_label = (
                "подходящих заявок (без отправки)" if test_mode
                else "уведомлений отправлено"
            )
            logging.info(
                "Итог сканирования: проверено=%s, совпадений по ключам=%s, "
                "%s=%s, ошибок=%s",
                total["checked"], total["matches"], lead_count_label,
                total["leads"], total["errors"]
            )
            try:
                await send_status(
                    http, BOT_TOKEN, BOT_CHAT_ID, len(sources),
                    total["checked"], total["leads"], total["errors"],
                    test_mode=test_mode, matches=total["matches"]
                )
                logging.info("Отчёт о сканировании отправлен в Telegram")
            except Exception:
                logging.exception(
                    "Не удалось отправить отчёт в Telegram. Проверь BOT_TOKEN и BOT_CHAT_ID."
                )
                raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(run())
