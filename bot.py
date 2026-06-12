import os
import logging
import requests
from serpapi import GoogleSearch

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

# ============================================================
# ПОИСКОВЫЕ ЗАПРОСЫ
# Цель: найти ЗАКАЗЧИКОВ, а не подрядчиков
# ============================================================

KEYWORDS = [
    # --- Домовые комитеты ищут подрядчика ---
    '"ועד בית" "מחפש קבלן"',
    '"ועד בית" "הצעת מחיר"',
    '"ועד בית" "שיקום חזית"',
    '"ועד בית" "רטיבות"',
    '"ועד בית" "נזילה"',
    '"נציגות הבית" "שיקום"',
    '"נציגות הבית" "הצעת מחיר"',

    # --- Управляющие компании ---
    '"חברת ניהול" "שיקום חזית"',
    '"חברת ניהול" "הצעת מחיר"',
    '"חברת אחזקה" "שיקום"',
    '"אחזקת מבנים" "מחפש"',
    '"מנהל אחזקה" "שיקום"',

    # --- Тендеры и запросы цен ---
    '"מכרז שיקום חזית"',
    '"מכרז איטום"',
    '"מכרז עבודות גובה"',
    '"הצעת מחיר שיקום"',
    '"הצעת מחיר איטום"',

    # --- Проблемы + намерение ---
    '"רטיבות בבניין" "מחפש"',
    '"רטיבות בדירה" "עזרה"',
    '"נזילה בקיר" "פתרון"',
    '"נזילה בקיר" "המלצה"',
    '"גג דולף" "מחפש קבלן"',
    '"סדקים בחזית" "תיקון"',
    '"טיח מתקלף" "מחפש"',
    '"חדירת מים" "מחפש פתרון"',
    '"שיקום חזית" "הצעת מחיר"',

    # --- Рекомендации ---
    '"מי מכיר קבלן" איטום',
    '"מי מכיר קבלן" שיקום',
    '"המלצה על קבלן" שיקום',
    '"ממליצים על" שיקום חזית',
    '"יש המלצה" עבודות גובה',
    '"זקוק לעזרה" רטיבות',

    # --- Форумы и Telegram ---
    'site:t.me "ועד בית" "שיקום"',
    'site:t.me "רטיבות" "מחפש"',
    'site:t.me "נזילה" "קבלן"',
    'site:rotter.net "ועד בית" "שיקום"',
    'site:rotter.net "רטיבות" "המלצה"',
    'site:stips.co.il "שיקום חזית"',
    'site:stips.co.il "רטיבות"',

    # --- Русскоязычные лиды ---
    '"домовой комитет" "ищем подрядчика"',
    '"домовой комитет" "ремонт фасада"',
    '"управляющая компания" "ремонт фасада"',
    '"ищу подрядчика" фасад Израиль',
    '"нужен ремонт фасада" Израиль',
    '"протекает стена" "что делать"',
    '"трещины на фасаде" "ищу"',
    '"нужна герметизация швов"',
    '"сырость в квартире" Израиль',
    '"посоветуйте подрядчика" фасад',
    '"рекомендации" "ремонт фасада" Израиль',
    '"ищем промышленного альпиниста"',
    'site:t.me "протечка" "фасад"',
    'site:t.me "домовой комитет"',
]

# ============================================================
# СИСТЕМА ОЦЕНКИ ЛИДОВ
# ============================================================

HIGH_VALUE = [
    ("ועד בית", 10),
    ("נציגות הבית", 10),
    ("חברת ניהול", 10),
    ("חברת אחזקה", 10),
    ("מנהל אחזקה", 10),
    ("מפקח בנייה", 10),
    ("מכרז", 10),
    ("домовой комитет", 10),
    ("управляющая компания", 10),
    ("תендер", 10),
]

INTENT_WORDS = [
    ("מחפש", 5),
    ("צריך", 5),
    ("המלצה", 5),
    ("ממליצים", 5),
    ("מי מכיר", 5),
    ("הצעת מחיר", 5),
    ("זקוק", 5),
    ("ищу", 5),
    ("нужен", 5),
    ("нужна", 5),
    ("посоветуйте", 5),
    ("рекомендации", 5),
    ("ищем", 5),
]

PROBLEM_WORDS = [
    ("רטיבות", 3),
    ("נזילה", 3),
    ("סדקים", 3),
    ("גג דולף", 3),
    ("טיח מתקלף", 3),
    ("חדירת מים", 3),
    ("протечка", 3),
    ("сырость", 3),
    ("трещин", 3),
    ("протекает", 3),
    ("фасад", 2),
    ("שיקום", 2),
    ("איטום", 2),
]

# ============================================================
# ЧЕРНЫЙ СПИСОК — сайты конкурентов и каталоги
# ============================================================

BLACKLIST_DOMAINS = [
    "d30.co.il", "koneс.co.il", "b144.co.il",
    "בזק", "yellow pages", "yad2.co.il/services",
    "jobmaster", "alljobs", "gotfriends",
]

BLACKLIST_WORDS = [
    "שירותי עבודות גובה", "חברת עבודות גובה",
    "מחירון", "advertisement", "sponsored",
    "קטלוג", "רשימת קבלנים",
]

# ============================================================
# ЛОГИКА
# ============================================================

def score_lead(title, snippet, link):
    text = (title + " " + (snippet or "") + " " + link).lower()

    # Проверка черного списка
    for domain in BLACKLIST_DOMAINS:
        if domain in link.lower():
            return 0
    for word in BLACKLIST_WORDS:
        if word.lower() in text:
            return 0

    score = 0
    for word, points in HIGH_VALUE:
        if word.lower() in text:
            score += points
    for word, points in INTENT_WORDS:
        if word.lower() in text:
            score += points
    for word, points in PROBLEM_WORDS:
        if word.lower() in text:
            score += points

    return score

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    send_message("🔍 Начинаю поиск лидов...")
    leads = []
    seen_links = set()  # дедупликация

    for keyword in KEYWORDS:
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

                # Пропускаем дубликаты
                if link in seen_links:
                    continue
                seen_links.add(link)

                score = score_lead(title, snippet, link)
                if score >= 5:
                    leads.append((score, title, link, snippet[:120]))

        except Exception as e:
            print(f"Error for '{keyword}': {e}")

    # Сортируем по рейтингу
    leads.sort(key=lambda x: x[0], reverse=True)

    if leads:
        send_message(f"✅ Найдено лидов: {len(leads)}\n🏆 Показываю лучшие (сортировка по рейтингу):")
        for score, title, link, snippet in leads[:20]:
            stars = "⭐" * min(int(score / 5), 5)
            msg = f"{stars} Рейтинг: {score}\n📌 {title}\n💬 {snippet}\n🔗 {link}"
            send_message(msg)
    else:
        send_message("❌ Лидов не найдено сегодня. Попробую завтра.")

if __name__ == "__main__":
    main()
