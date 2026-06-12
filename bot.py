import os
import csv
import logging
import requests
import re
from datetime import date
from serpapi import GoogleSearch
from io import StringIO

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

# ============================================================
# МОДУЛЬ А — Сбор базы управляющих компаний
# ============================================================

COMPANY_KEYWORDS = [
    "חברת ניהול בניינים",
    "חברת אחזקה בניינים",
    "אחזקת מבנים ישראל",
    "ניהול ועד בית",
    "מנהל אחזקה",
    "ניהול מבנים",
    "Facility Management Israel",
    "Property Management Israel",
    "Building Management Israel",
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

SKIP_DOMAINS = [
    "b144", "d30", "yellow", "jobmaster", "wikipedia",
    "ynet", "calcalist", "haaretz", "maariv", "walla",
    "midrag", "pro.co.il", "easy.co.il", "dapei",
    "google.com", "facebook.com", "instagram.com",
    "linkedin.com", "twitter.com",
]

def extract_phone(text):
    phones = re.findall(r'0\d[\d\-]{7,10}', text)
    return phones[0].replace("-", "") if phones else ""

def extract_email(text):
    emails = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,4}', text)
    # фильтруем мусорные email
    skip = ["example", "test", "spam", "noreply", "no-reply"]
    for email in emails:
        if not any(s in email.lower() for s in skip):
            return email
    return ""

def extract_city(text):
    cities = [
        "תל אביב", "ירושלים", "חיפה", "ראשון לציון",
        "נתניה", "אשדוד", "פתח תקווה", "רמת גן", "באר שבע",
        "חולון", "בת ים", "בני ברק", "רחובות", "אשקלון",
        "הרצליה", "כפר סבא", "רעננה", "מודיעין", "אילת",
    ]
    for city in cities:
        if city in text:
            return city
    return ""

def scrape_contact_page(base_url):
    """Этап 2 — заходим на сайт и ищем контакты"""
    phone = ""
    email = ""

    # Пробуем страницы контактов
    contact_paths = ["", "/contact", "/contacts", "/צור-קשר", "/about", "/about-us"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for path in contact_paths:
        try:
            url = base_url.rstrip("/") + path
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code != 200:
                continue

            text = response.text

            # Извлекаем телефон
            if not phone:
                found_phones = re.findall(r'0\d[\d\-]{7,10}', text)
                if found_phones:
                    phone = found_phones[0].replace("-", "")

            # Извлекаем email
            if not email:
                found_emails = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,4}', text)
                skip = ["example", "test", "spam", "noreply", "no-reply", "sentry", "wix"]
                for e in found_emails:
                    if not any(s in e.lower() for s in skip):
                        email = e
                        break

            # Если нашли оба — достаточно
            if phone and email:
                break

        except Exception as e:
            print(f"Scrape error {base_url}{path}: {e}")
            continue

    return phone, email

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

                if any(s in link.lower() for s in SKIP_DOMAINS):
                    continue

                # Этап 1 — из сниппета
                phone = extract_phone(snippet + " " + title)
                email = extract_email(snippet + " " + title)
                city = extract_city(snippet + " " + title)

                # Этап 2 — заходим на сайт если не нашли контакты
                if not phone or not email:
                    scraped_phone, scraped_email = scrape_contact_page(link)
                    if not phone:
                        phone = scraped_phone
                    if not email:
                        email = scraped_email

                # Город из сниппета или из текста сайта
                if not city:
                    city = extract_city(title)

                companies.append({
                    "Название": title,
                    "Телефон": phone,
                    "Email": email,
                    "Сайт": link,
                    "Город": city,
                    "Источник": keyword,
                    "Дата": str(date.today()),
                })

        except Exception as e:
            print(f"Company error '{keyword}': {e}")

    return companies

def send_companies_csv(companies):
    if not companies:
        send_message("🏢 Модуль А: Новых компаний не найдено.")
        return

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Название", "Телефон", "Email", "Сайт", "Город", "Источник", "Дата"
    ])
    writer.writeheader()
    writer.writerows(companies)
    csv_content = output.getvalue()

    filename = f"companies_{date.today()}.csv"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {"document": (filename, csv_content.encode("utf-8-sig"), "text/csv")}
    data = {
        "chat_id": CHAT_ID,
        "caption": (
            f"🏢 МОДУЛЬ А — Управляющие компании\n"
            f"📊 Найдено: {len(companies)}\n"
            f"📞 С телефоном: {sum(1 for c in companies if c['Телефон'])}\n"
            f"📧 С email: {sum(1 for c in companies if c['Email'])}\n"
            f"📅 Дата: {date.today()}"
        )
    }
    requests.post(url, data=data, files=files)

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
    send_message("🚀 Запускаю сбор базы...\n⏳ Займёт 3-5 минут (захожу на каждый сайт)")

    companies = search_companies()
    send_companies_csv(companies)

    send_message("✅ Готово! Открой файл в Excel.")

if __name__ == "__main__":
    main()
