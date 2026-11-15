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


VACANCY_PATTERNS = [
    r"\bв команду\b",
    r"\b(ищем|требуется|требуются|приглашаем)\b.{0,70}\b(сотрудник|специалист|разработчик|инженер|тестировщик|менеджер|дизайнер|qa|программист)\b",
    r"\b(вакансия|вакансии|зарплата|оклад|заработная плата)\b",
    r"\b(требования к кандидату|обязанности кандидата|опыт работы от|коммерческий опыт|полный день|гибкий график)\b",
    r"\b(ищу работу|ищу вакансию|рассмотрю предложения о работе)\b",
]

PROMO_PATTERNS = [
    r"\bузнать больше\b",
    r"\bбольше проектов в нашем боте\b",
    r"\bподдержи(те)? наш канал\b",
    r"\bподпишись(те)?\b",
    r"\bпереходи(те)? в бот\b",
    r"\bнаши проекты в боте\b",
]

BUYER_INTENT_PATTERNS = [
    r"\b(мне нужен|нам нужен|нужен|нужна|нужно|нужны)\b",
    r"\b(ищу|ищем)\b.{0,100}\b(исполнител|фрилансер|человек|специалист|разработчик|дизайнер)\w*\b",
    r"\bкто (может|сможет|умеет)\b",
    r"\b(подскажите|посоветуйте)\b.{0,100}\b(исполнител|разработчик|дизайнер|сделать|создать)\w*\b",
    r"\b(хочу заказать|хотим заказать|готов(а|ы) оплатить|бюджет на разработку)\b",
    r"\b(кто возьмется|кто возьмётся)\b",
]


def _matches_any(text, patterns):
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def lead_rejection_reason(text, ignore_words, min_length=20):
    normalized = normalize(text)
    if len(normalized) < min_length:
        return "короткое сообщение"
    ignored = next(
        (normalize(word) for word in ignore_words if normalize(word) in normalized),
        None
    )
    if ignored:
        return f"стоп-слово: {ignored}"
    if _matches_any(normalized, VACANCY_PATTERNS):
        return "вакансия или поиск сотрудника"
    if _matches_any(normalized, PROMO_PATTERNS):
        return "реклама или агрегатор"
    if not _matches_any(normalized, BUYER_INTENT_PATTERNS):
        return "нет явного намерения заказать услугу"
    return None


def looks_like_spam(text, ignore_words, min_length=20):
    return lead_rejection_reason(text, ignore_words, min_length) is not None
