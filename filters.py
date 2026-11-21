import re


def normalize(text):
    text = (text or "").lower().replace("ё", "е")
    return re.sub(r"\s+", " ", text).strip()


def find_keyword(text, keywords):
    normalized = normalize(text)
    for keyword in keywords:
        key = normalize(keyword)
        if key and key in normalized:
            return keyword
    return None


# Hiring posts are not customer requests, even when they mention bots or websites.
VACANCY_PATTERNS = [
    r"\bв команду\b",
    r"\b(ищем|требуется|требуются|приглашаем)\b.{0,70}\b(сотрудник|специалист|разработчик|инженер|тестировщик|менеджер|дизайнер|qa|программист)\b",
    r"\b(вакансия|вакансии|зарплата|оклад|заработная плата)\b",
    r"\b(требования к кандидату|обязанности кандидата|опыт работы от|коммерческий опыт|полный день|гибкий график)\b",
    r"\b(ищу работу|ищу вакансию|рассмотрю предложения о работе)\b",
    r"\b(senior|middle|junior)\s+(backend|frontend|full[- ]?stack|python|php|java|разработчик|developer)\b",
    r"\b(от 1|от 2|от 3|минимум 1|минимум 2)\s+лет\s+(коммерческого\s+)?опыта\b",
    r"\b(ищем|нанимаем)\b.{0,100}\b(в команду|на работу|на позицию)\b",
]

ROUNDUP_PATTERNS = [
    r"\b(подборка|дайджест|список)\s+(заказов|проектов|вакансий|заявок)\b",
    r"\bзаказы\s+в\s+категории\b",
    r"\b(топ|10|пять|несколько)\s+(заказов|проектов|вакансий)\b",
    r"\b\d+[.)]\s*.{0,100}https?://(?:u\.)?habr\.com\b",
    r"\bсмотрите\s+(все\s+)?заказы\b",
]

SELF_PROMO_PATTERNS = [
    r"\b(я\s+)?(делаю|создаю|разрабатываю|собираю|верстаю)\b.{0,70}\b(сайт|сайты|лендинг|лендинги|бот|боты)\b",
    r"\b(предлагаю услуги|оказываю услуги|возьму в работу|беру в работу|ищу проекты|ищу клиентов)\b",
    r"\b(мои услуги|мое портфолио|моё портфолио|мои кейсы)\b.{0,100}\b(сайт|лендинг|разработ|дизайн|бот)\w*",
    r"\b(разработчик|веб[- ]дизайнер|фрилансер)\b.{0,80}\b(свободен|свободна|ищу клиентов|готов к заказам|беру заказы)\b",
]

PROMO_PATTERNS = [
    r"\bузнать больше\b",
    r"\bбольше проектов в нашем боте\b",
    r"\bподдержи(те)? наш канал\b",
    r"\bподпишись(те)?\b",
    r"\bпереходи(те)? в бот\b",
    r"\bнаши проекты в боте\b",
]

# Reject clearly advanced product/backend work, but do not reject a lead
# merely because it mentions CRM/ERP/1C as optional context.
COMPLEX_SCOPE_PATTERNS = [
    (r"\b(кошелек|кошелёк|платежн\w+ система|эквайринг|прием платежей|приём платежей)\b", "платежная система или кошелек"),
    (r"\b(крипто|криптовалют|бирж\w+|трейдинг|prediction market|polymarket)\b", "крипто- или торговый функционал"),
    (r"\b(vpn[- ]?сервис|vpn[- ]?сервер|продажа подписок|подписочн\w+ сервис)\b", "VPN или система подписок"),
    (r"\b(личный кабинет|регистрац\w+ пользователей|авторизац\w+|логин[- ]парол\w+)\b.{0,120}\b(оплат|заказ|услуг|кошел|crm|модерац|подписк)\w*", "личный кабинет с бизнес-логикой"),
    (r"\b(маркетплейс|агрегатор услуг|система бронирования|бронирован\w+ система)\b", "маркетплейс или система бронирования"),
    (r"\b(интернет-магазин|онлайн-магазин|e-commerce)\b.{0,100}\b(корзин|эквайринг|оплат|checkout|интеграц)\w*", "интернет-магазин с интеграциями или оплатой"),
    (r"\b(видеотрансляц\w+|стриминг|видеохостинг|обработк\w+ видео)\b", "видеосервис"),
    (r"\b(telegram mini app|mini app|мини[- ]приложени\w+)\b", "Telegram Mini App или мини-приложение"),
    (r"\b(crm|erp)\b.{0,70}\b(интеграц|синхронизац|обмен данными|api)\w*|\b(интеграц|синхронизац|обмен данными|api)\w*.{0,70}\b(crm|erp)\b", "интеграция CRM/ERP"),
    (r"\b(интеграц|синхронизац|обмен данными|выгрузк|загрузк)\w*.{0,70}\b(1с|битрикс24)\b|\b(1с|битрикс24)\b.{0,70}\b(интеграц|синхронизац|обмен данными|выгрузк|загрузк)\w*", "интеграция с 1С или Битрикс24"),
    (r"\b(разработать|создать|внедрить|доработать)\s+(свою\s+)?(crm|erp)\b", "разработка CRM/ERP"),
    (r"\b(1с[- ]?битрикс|битрикс|1с)\b.{0,80}\b(разработ|доработ|сайт|интернет-магазин|интеграц|модул|каталог)\w*|\b(разработ|доработ|создан)\w*.{0,80}\b(1с[- ]?битрикс|битрикс|1с)\b", "разработка или доработка на 1С/Битрикс"),
]


# A request must be about the service we provide, not merely mention it
# somewhere in a post about hiring a marketer or promoting another product.
SERVICE_TERMS = (
    r"(?:сайт\w*|лендинг\w*|веб[- ]?сайт\w*|"
    r"телеграм[- ]?бот\w*|telegram[- ]?бот\w*|бот\w*|"
    r"автоматизац\w*)"
)

BUYER_INTENT_PATTERNS = [
    r"\b(срочный запрос|есть задача|есть заказ|ищу исполнителя|нужен исполнитель)\b",
    r"\b(мне нужен|нам нужен|нужен|нужна|нужно|нужны)\b",
    r"\b(ищу|ищем)\b.{0,80}\b(исполнител|фрилансер|человек|специалист|разработчик|дизайнер)\w*\b",
    r"\bкто (может|сможет|умеет|сделает)\b",
    r"\b(подскажите|посоветуйте)\b.{0,80}\b(исполнител|разработчик|дизайнер|сделать|создать)\w*\b",
    r"\b(хочу заказать|хотим заказать|готов(а|ы) оплатить|бюджет на разработку)\b",
    r"\b(кто возьмется|кто возьмётся)\b",
    r"\bзаказ\s*#?\s*\d+\b",
    r"\b(нужно|необходимо)\s+(сделать|создать|разработать|сверстать)\b",
    r"\b(создать|сделать|разработать|сверстать|заказать)\s+(сайт|лендинг|телеграм[- ]?бот|telegram[- ]?бот|бот|автоматизац\w*)\b",
    r"\b(разработка|создание|верстка|доработка)\s+(сайта|лендинга|бота|автоматизац\w*)\b",
]


def _has_service_buyer_intent(text):
    # The buyer-intent phrase must be close to the requested service.
    # This avoids incidental mentions in posts about unrelated vacancies.
    sentences = re.split(r"[.!?;\n]+", text)
    service = re.compile(SERVICE_TERMS, re.IGNORECASE)
    for sentence in sentences:
        sentence = sentence.strip()
        service_matches = list(service.finditer(sentence))
        if not service_matches:
            continue
        for pattern in BUYER_INTENT_PATTERNS:
            for intent_match in re.finditer(pattern, sentence, re.IGNORECASE):
                for service_match in service_matches:
                    distance = max(
                        0,
                        service_match.start() - intent_match.end(),
                        intent_match.start() - service_match.end(),
                    )
                    if distance <= 50:
                        return True
    return False


def _matches_any(text, patterns):
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def lead_rejection_reason(text, ignore_words):
    normalized = normalize(text)

    ignored = next(
        (normalize(word) for word in ignore_words if normalize(word) in normalized),
        None
    )
    if ignored:
        return f"стоп-слово: {ignored}"
    if _matches_any(normalized, ROUNDUP_PATTERNS):
        return "подборка нескольких заказов, а не отдельная заявка"
    if _matches_any(normalized, VACANCY_PATTERNS):
        return "вакансия или поиск сотрудника"
    if _matches_any(normalized, PROMO_PATTERNS):
        return "реклама или агрегатор"
    if _matches_any(normalized, SELF_PROMO_PATTERNS):
        return "самореклама исполнителя"

    for pattern, reason in COMPLEX_SCOPE_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return f"слишком сложный проект: {reason}"

    if not _has_service_buyer_intent(normalized):
        return "нет явного намерения заказать услугу"
    return None


def looks_like_spam(text, ignore_words):
    return lead_rejection_reason(text, ignore_words) is not None
