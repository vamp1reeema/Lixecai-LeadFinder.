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

def looks_like_spam(text, ignore_words, min_length=20):
    normalized = normalize(text)
    if len(normalized) < min_length:
        return True
    return any(normalize(word) in normalized for word in ignore_words if word)
