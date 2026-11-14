import html

async def send_lead(session, token, chat_id, chat_title, message, keyword):
    text = (message.message or "").strip()
    excerpt = text[:1200] + ("…" if len(text) > 1200 else "")
    username = getattr(message.chat, "username", None)
    if username:
        link = f"https://t.me/{username}/{message.id}"
    else:
        raw_id = str(message.chat_id)
        link = f"https://t.me/c/{raw_id[4:]}/{message.id}" if raw_id.startswith("-100") else ""

    lines = [
        "🔎 <b>Найден потенциальный клиент</b>",
        f"💬 <b>Чат:</b> {html.escape(chat_title or 'Без названия')}",
        f"🎯 <b>Совпадение:</b> {html.escape(keyword)}",
        "",
        html.escape(excerpt)
    ]
    if link:
        lines += ["", f'<a href="{html.escape(link, quote=True)}">Открыть сообщение</a>']

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with session.post(url, json={
        "chat_id": chat_id, "text": "\n".join(lines),
        "parse_mode": "HTML", "disable_web_page_preview": True
    }) as response:
        result = await response.json()
        if response.status != 200 or not result.get("ok"):
            raise RuntimeError(f"Telegram Bot API error: {result}")
