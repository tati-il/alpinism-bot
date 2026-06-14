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

COMPANY_KEYWORDS = [
    # עברית
    "חברת ניהול בניינים",
    "חברת אחזקה בניינים",
    "אחזקת מבנים ישראל",
    "ניהול ועד בית",
    "מנהל אחזקה",
    "ניהול מבנים",
    "חברת ניהול תל אביב",
    "חברת ניהול ירושלים",
    "חברת ניהול חיפה",
    "חברת ניהול ראשון לציון",
    "חברת ניהול נתניה",
    "חברת ניהול אשדוד",
    "חברת ניהול פתח תקווה",
    "חברת ניהול רמת גן",
    "חברת ניהול באר שבע",
    "חברת ניהול חולון",
    "חברת ניהול בת ים",
    "חברת ניהול הרצליה",
    "חברת ניהול רחובות",
    # רוסית
    "управляющая компания Израиль",
    "обслуживание зданий Израиль",
    "управление недвижимостью Израиль",
]

# Домены которые нужно пропустить
SKIP_DOMAINS = [
    "b144", "d30", "yellow", "jobmaster", "wikipedia",
    "ynet", "calcalist", "haaretz", "maariv", "walla",
    "midrag", "pro.co.il", "easy.co.il", "dapei",
    "google.com", "facebook.com", "instagram.com",
    "linkedin.com", "twitter.com", "youtube.com",
    "stips", "rotter", "tapuz",
]

# Израильские домены
ISRAEL_DOMAINS = [".co.il", ".org.il", ".net.il", ".ac.il", ".gov.il"]

ARTICLE_TITLE_WORDS = [
    "רשימה", "המלצות", "מחירים", "מחיר", "כמה עולה",
    "השוואה", "איך לבחור", "מדריך", "טיפים", "כתבה",
    "פורטל", "מאמר", "ויקי",
    "лучшие", "топ", "рейтинг",
    "דרושים", "משרות", "דרוש", "דרושה",
    "вакансии", "требуется",
]

ARTICLE_URL_SIGNS = [
    "/blog/", "/news/", "/article/", "/post/",
    "/category/", "/tag/", "?p=", "wiki",
    "/jobs/", "/career/", "/משרות/", "/דרושים/",
]

def is_real_company(title, link):
    title_lower = title.lower()
    link_lower = link.lower()

    # Только израильские домены
    if not any(d in link_lower for d in ISRAEL_DOMAINS):
        return False

    if any(s in link_lower for s in SKIP_DOMAINS):
        return False

    if any(w in title_lower for w in ARTICLE_TITLE_WORDS):
        return False

    if any(s in link_lower for s in ARTICLE_URL_SIGNS):
        return False

    return True

def extract_phone(text):
    phones = re.findall(r'0\d[\d\-]{7,10}', text)
    return phones[0].replace("-", "") if phones else ""

def extract_email(text):
    emails = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,4}', text)
    skip = ["example", "test", "spam", "noreply", "no-reply", "sentry", "wix", "wordpress"]
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
        "Тель-Авив", "Иерусалим", "Хайфа", "Нетания",
    ]
    for city in cities:
        if city in text:
            return city
    return ""

def scrape_contact_page(base_url):
    phone = ""
    email = ""
    contact_paths = ["", "/contact", "/contacts", "/צור-קשר", "/about", "/אודות"]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for path in contact_paths:
        try:
            url = base_url.rstrip("/") + path
            response = requests.get(url, headers=headers, timeout=7)
            if response.status_code != 200:
                continue
            text = response.text
            if not phone:
                found = re.findall(r'0\d[\d\-]{7,10}', text)
                if found:
                    phone = found[0].replace("-", "")
            if not email:
                found = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,4}', text)
                skip = ["example", "test", "spam", "noreply", "sentry", "wix", "wordpress"]
                for e in found:
                    if not any(s in e.lower() for s in skip):
                        email = e
                        break
            if phone and email:
                break
        except:
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
                "lr": "lang_iw|lang_ru",
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

                if not is_real_company(title, link):
                    continue

                phone = extract_phone(snippet + " " + title)
                email = extract_email(snippet + " " + title)
                city = extract_city(snippet + " " + title + " " + keyword)

                if not phone or not email:
                    scraped_phone, scraped_email = scrape_contact_page(link)
                    if not phone:
                        phone = scraped_phone
                    if not email:
                        email = scraped_email

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
            print(f"Error '{keyword}': {e}")

    return companies

def send_companies_csv(companies):
    if not companies:
        send_message("🏢 Новых компаний не найдено.")
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
            f"🏢 Управляющие компании Израиля\n"
            f"📊 Найдено компаний: {len(companies)}\n"
            f"📞 С телефоном: {sum(1 for c in companies if c['Телефон'])}\n"
            f"📧 С email: {sum(1 for c in companies if c['Email'])}\n"
            f"📅 {date.today()}"
        )
    }
    requests.post(url, data=data, files=files)

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    send_message("🚀 Запускаю сбор базы...\n⏳ Займёт 3-5 минут")
    companies = search_companies()
    send_companies_csv(companies)
    send_message("✅ Готово! Открой файл в Excel.")

if __name__ == "__main__":
    main()
