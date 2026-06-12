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

# Домены которые нужно пропустить
SKIP_DOMAINS = [
    "b144", "d30", "yellow", "jobmaster", "wikipedia",
    "ynet", "calcalist", "haaretz", "maariv", "walla",
    "midrag", "pro.co.il", "easy.co.il", "dapei",
    "google.com/maps", "facebook.com", "instagram.com",
]

def extract_phone(text):
    phones = re.findall(r'0\d[\d\-]{7,10}', text)
    return phones[0] if phones else ""

def extract_email(text):
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return emails[0] if emails else ""

def extract_city(text, title):
    cities = ["תל אביב", "ירושלים", "חיפה", "ראשון לציון",
              "נתניה", "אשדוד", "פתח תקווה", "רמת גן", "באר שבע",
              "חולון", "בת ים", "בני ברק", "רחובות", "אשקלון"]
    for city in cities:
        if city in text or city in title:
            return city
    return ""

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

                # Пропускаем каталоги и новостные сайты
                if any(s in link.lower() for s in SKIP_DOMAINS):
                    continue

                phone = extract_phone(snippet + " " + title)
                email = extract_email(snippet + " " + title)
                city = extract_city(snippet, title)

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

    # Создаём CSV в памяти
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Название", "Телефон", "Email", "Сайт", "Город", "Источник", "Дата"
    ])
    writer.writeheader()
    writer.writerows(companies)
    csv_content = output.getvalue()

    # Отправляем файл в Telegram
    filename = f"companies_{date.today()}.csv"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {"document": (filename, csv_content.encode("utf-8-sig"), "text/csv")}
    data = {
        "chat_id": CHAT_ID,
        "caption": f"🏢 МОДУЛЬ А — Управляющие компании\n📊 Найдено новых: {len(companies)}\n📅 Дата: {date.today()}"
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
    send_message("🚀 Запускаю сбор базы управляющих компаний...")

    companies = search_companies()
    send_companies_csv(companies)

    send_message("✅ Готово! Проверь файл выше.")

if __name__ == "__main__":
    main()
