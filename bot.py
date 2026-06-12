import os
import logging
import requests
from serpapi import GoogleSearch

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

# ============================================================
# МОДУЛЬ А — База управляющих компаний
# ============================================================

COMPANY_KEYWORDS = [
    # иврит
    "חברת ניהול בניינים",
    "חברת אחזקה בניינים",
    "אחזקת מבנים",
    "ניהול ועד בית",
    "מנהל אחזקה",
    "ניהול מבנים",
    # английский
    "Facility Management Israel",
    "Property Management Israel",
    "Building Management Israel",
    # города
    "חברת ניהול תל אביב",
    "חברת ניהול ירושלים",
    "חברת ניהול חיפה",
    "חברת ניהול ראשון לציון",
    "חברת ניהול נתניה",
    "חברת ניהול אשדוד",
    "חברת ניהול פתח תקווה",
    "חברת ניהול רמת גן",
    "חברת ניהול באר שבע",
]

def search_companies():
    companies = []
    seen = set()

    for keyword in COMPANY_KEYWORDS:
        try:
            params = {
                "q": keyword,
                "api_key": SERPAPI_KEY,
                "num": 5,
                "gl": "il",
                "hl": "iw",
            }
            search = GoogleSearch(params)
            data = search.get_dict()

            for r in data.get("organic_results", []):
                title = r.get("title", "")
                link = r.get("link", "")
                snippet = r.get("snippet", "")

                if link in seen:
                    continue
                seen.add(link)

                # Пропускаем каталоги и агрегаторы
                skip = ["b144", "d30", "koneс", "yellow", "jobmaster", "wikipedia"]
                if any(s in link.lower() for s in skip):
                    continue

                # Извлекаем телефон из сниппета
                phone = ""
                import re
                phones = re.findall(r'0\d[\d\-]{7,10}', snippet)
                if phones:
                    phone = phones[0]

                companies.append({
                    "name": title,
                    "phone": phone,
                    "site": link,
                    "snippet": snippet[:100],
                    "keyword": keyword,
                })

        except Exception as e:
            print(f"Company search error: {e}")

    return companies

def send_companies_report(companies):
    if not companies:
        send_message("🏢 Модуль А: Новых компаний не найдено.")
        return

    send_message(f"🏢 МОДУЛЬ А — Управляющие компании\nНайдено: {len(companies)}")

    for i, c in enumerate(companies[:15], 1):
        msg = (
            f"🏢 {i}. {c['name']}\n"
            f"📞 {c['phone'] or 'не найден'}\n"
            f"🌐 {c['site']}\n"
            f"📝 {c['snippet']}\n"
            f"🔎 Запрос: {c['keyword']}"
        )
        send_message(msg)

# ============================================================
# МОДУЛЬ Б — Горячие лиды
# ============================================================

LEAD_KEYWORDS = [
    # Telegram
    'site:t.me "רטיבות"',
    'site:t.me "נזילה"',
    'site:t.me "ועד בית" "שיקום"',
    'site:t.me "גג דולף"',
    'site:t.me "מחפש קבלן"',
    'site:t.me "протечка"',
    'site:t.me "домовой комитет"',

    # Форумы
    'site:rotter.net "רטיבות" "מחפש"',
    'site:rotter.net "שיקום חזית"',
    'site:stips.co.il "רטיבות"',
    'site:stips.co.il "שיקום חזית"',

    # Иврит — проблемы + намерение
    '"ועד בית" "מחפש קבלן"',
    '"ועד בית" "הצעת מחיר" שיקום',
    '"נציגות הבית" "הצעת מחיר"',
    '"רטיבות בבניין" "מחפש"',
    '"נזילה בקיר" "המלצה"',
    '"גג דולף" "מחפש קבלן"',
    '"סדקים בחזית" "תיקון"',
    '"חדירת מים" "פתרון"',
    '"מכרז שיקום חזית"',
    '"מכרז איטום"',
    '"הצעת מחיר שיקום"',
    '"מי מכיר קבלן" איטום',
    '"המלצה על קבלן" שיקום',

    # Русский — проблемы + намерение
    '"домовой комитет" "ищем подрядчика"',
    '"домовой комитет" "ремонт фасада"',
    '"протекает стена" "что делать"',
    '"трещины на фасаде" "ищу"',
    '"нужна герметизация швов"',
    '"посоветуйте подрядчика" фасад',
    '"ищем промышленного альпиниста"',
    '"сырость в квартире" Израиль',
]

# Система оценки
HIGH_VALUE = [
    ("ועד בית", 10), ("נציגות הבית", 10),
    ("חברת ניהול", 10), ("חברת אחזקה", 10),
    ("מנהל אחזקה", 10), ("מפקח בנייה", 10),
    ("מכרז", 10), ("домовой комитет", 10),
    ("управляющая компания", 10),
]
INTENT_WORDS = [
    ("מחפש", 5), ("צריך", 5), ("המלצה", 5),
    ("הצעת מחיר", 5), ("מי מכיר", 5),
    ("ищу", 5), ("нужен", 5), ("нужна", 5),
    ("посоветуйте", 5), ("ищем", 5),
]
PROBLEM_WORDS = [
    ("רטיבות", 3), ("נזילה", 3), ("סדקים", 3),
    ("גג דולף", 3), ("חדירת מים", 3),
    ("протечка", 3), ("сырость", 3), ("трещин", 3),
    ("שיקום", 2), ("איטום", 2), ("фасад", 2),
]

BLACKLIST_DOMAINS = [
    "b144.co.il", "d30.co.il", "yellow.co.il",
    "jobmaster", "wikipedia", "ynet.co.il",
]
BLACKLIST_WORDS = [
    "קטלוג שירותים", "רשימת קבלנים",
    "advertisement", "sponsored",
]

def score_lead(title, snippet, link):
    text = (title + " " + (snippet or "") + " " + link).lower()
    for domain in BLACKLIST_DOMAINS:
        if domain in link.lower():
            return 0
    for word in BLACKLIST_WORDS:
        if word.lower() in text:
            return 0
    score = 0
    for word, pts in HIGH_VALUE:
        if word.lower() in text: score += pts
    for word, pts in INTENT_WORDS:
        if word.lower() in text: score += pts
    for word, pts in PROBLEM_WORDS:
        if word.lower() in text: score += pts
    return score

def search_leads():
    leads = []
    seen = set()

    for keyword in LEAD_KEYWORDS:
        try:
            params = {
                "q": keyword,
                "api_key": SERPAPI_KEY,
                "num": 3,
                "gl": "il",
            }
            search = GoogleSearch(params)
            data = search.get_dict()

            for r in data.get("organic_results", []):
                title = r.get("title", "")
                link = r.get("link", "")
                snippet = r.get("snippet", "")

                if link in seen:
                    continue
                seen.add(link)

                score = score_lead(title, snippet, link)
                if score >= 5:
                    leads.append((score, title, link, snippet[:120]))

        except Exception as e:
            print(f"Lead search error: {e}")

    leads.sort(key=lambda x: x[0], reverse=True)
    return leads

def send_leads_report(leads):
    if not leads:
        send_message("🔥 Модуль Б: Горячих лидов не найдено.")
        return

    send_message(f"🔥 МОДУЛЬ Б — Горячие лиды\nНайдено: {len(leads)}")

    for score, title, link, snippet in leads[:15]:
        stars = "⭐" * min(int(score / 5), 5)
        msg = (
            f"{stars} Рейтинг: {score}\n"
            f"📌 {title}\n"
            f"💬 {snippet}\n"
            f"🔗 {link}"
        )
        send_message(msg)

# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    send_message("🚀 Запускаю ежедневный поиск...")

    # Модуль А — управляющие компании
    companies = search_companies()
    send_companies_report(companies)

    # Модуль Б — горячие лиды
    leads = search_leads()
    send_leads_report(leads)

    send_message("✅ Поиск завершён!")

if __name__ == "__main__":
    main()
