import html

async def send_status(session, token, chat_id, source_count, checked, leads, errors):
    text = (
        "🟢 <b>Lixecai LeadFinder: сканирование завершено</b>\n"
        f"Источников в настройках: <b>{source_count}</b>\n"
        f"Новых постов проверено: <b>{checked}</b>\n"
        f"Потенциальных заявок отправлено: <b>{leads}</b>\n"
        f"Ошибок источников/отправки: <b>{errors}</b>\n"
        + ("Новых совпадений пока нет." if leads == 0 else "Заявки отправлены выше.")
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with session.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }) as response:
        result = await response.json()
        if response.status != 200 or not result.get("ok"):
            raise RuntimeError(f"Telegram Bot API error: {result}")

async def send_lead(session, token, chat_id, source, message_id, text, keyword):
    excerpt = text[:1200] + ("…" if len(text) > 1200 else "")
    link = f"https://t.me/{source}/{message_id}"
    lines = [
        "🔎 <b>Найдено сообщение с потенциальной заявкой</b>",
        f"💬 <b>Публичный источник:</b> {html.escape(source)}",
        f"🎯 <b>Совпадение:</b> {html.escape(keyword)}",
        "",
        html.escape(excerpt),
        "",
        f'<a href="{link}">Открыть сообщение</a>'
    ]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with session.post(url, json={
        "chat_id": chat_id,
        "text": "\n".join(lines),
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }) as response:
        result = await response.json()
        if response.status != 200 or not result.get("ok"):
            raise RuntimeError(f"Telegram Bot API error: {result}")
