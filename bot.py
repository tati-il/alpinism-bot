import os
import csv
import logging
import requests
import re
import base64
from datetime import date
from serpapi import GoogleSearch
from io import StringIO

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

# ============================================================
# GITHUB — читаем ВСЕ файлы и сохраняем новый
# ============================================================

def get_github_files():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error getting files: {e}")
        return []

def load_all_known_companies():
    """Читаем ВСЕ CSV файлы и собираем все известные email и сайты"""
    all_known = set()

    try:
        files = get_github_files()
        csv_files = [
            f for f in files
            if f["name"].endswith(".csv") and "requirements" not in f["name"]
        ]

        print(f"Found {len(csv_files)} CSV files in repository")

        headers = {"Authorization": f"token {GITHUB_TOKEN}"}

        for file in csv_files:
            try:
                response = requests.get(file["download_url"], headers=headers)
                if response.status_code != 200:
                    continue

                content = response.content.decode("utf-8-sig", errors="ignore")
                print(f"Reading file: {file['name']}")

                for delimiter in [",", ";"]:
                    try:
                        reader = csv.DictReader(StringIO(content), delimiter=delimiter)
                        rows = list(reader)
                        if not rows:
                            continue

                        for row in rows:
                            for key, value in row.items():
                                val = (value or "").strip().lower()
                                # Собираем email
                                if "@" in val and "." in val:
                                    all_known.add(val)
                                # Собираем домен сайта
                                if "http" in val:
                                    domain = re.sub(r'https?://(www\.)?', '', val).split("/")[0]
                                    if domain:
                                        all_known.add(domain)
                        break
                    except:
                        continue

            except Exception as e:
                print(f"Error reading {file['name']}: {e}")

    except Exception as e:
        print(f"Error loading companies: {e}")

    print(f"Total known entries from all files: {len(all_known)}")
    return all_known

def save_csv_to_github(filename, csv_content):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }
        content = base64.b64encode(csv_content.encode("utf-8-sig")).decode("utf-8")
        payload = {
            "message": f"Add companies {date.today()}",
            "content": content,
        }
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"Saved {filename} to GitHub")
        else:
            print(f"Error saving: {response.status_code}")
    except Exception as e:
        print(f"Error saving CSV: {e}")

# ============================================================
# КЛЮЧЕВЫЕ СЛОВА — только иврит
# ============================================================

COMPANY_KEYWORDS = [
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
    "חברת ניהול מודיעין",
    "חברת ניהול כפר סבא",
    "חברת ניהול רעננה",
    "חברת ניהול אילת",
]

SKIP_DOMAINS = [
    "b144", "d30", "yellow", "jobmaster", "wikipedia",
    "ynet", "calcalist", "haaretz", "maariv", "walla",
    "midrag", "pro.co.il", "easy.co.il", "dapei",
    "google.com", "facebook.com", "instagram.com",
    "linkedin.com", "twitter.com", "youtube.com",
    "stips", "rotter", "tapuz",
]

ISRAEL_DOMAINS = [".co.il", ".org.il", ".net.il", ".ac.il", ".gov.il"]

ARTICLE_TITLE_WORDS = [
    "רשימה", "המלצות", "מחירים", "מחיר", "כמה עולה",
    "השוואה", "איך לבחור", "מדריך", "טיפים", "כתבה",
    "פורטל", "מאמר", "ויקי",
    "דרושים", "משרות", "דרוש", "דרושה",
    "קורס", "קורסים", "הכשרה", "לימודים", "סמינר",
]

ARTICLE_URL_SIGNS = [
    "/blog/", "/news/", "/article/", "/post/",
    "/category/", "/tag/", "?p=", "wiki",
    "/jobs/", "/career/", "/משרות/", "/דרושים/",
    "/קורס/", "/course/", "/courses/",
]

VALID_EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "me.com", "mac.com", "protonmail.com",
    "live.com", "msn.com", "aol.com",
    "walla.co.il", "walla.com", "bezeqint.net", "bezeq.net",
    "barak.net.il", "netvision.net.il", "zahav.net.il",
    "012.net.il", "013.net", "014.net", "017.net.il",
    "hot.net.il", "nana.co.il", "smile.net.il",
]

def is_valid_email(email):
    email = email.lower().strip()
    if not re.match(r'^[\w\.\-]+@[\w\.\-]+\.\w{2,}$', email):
        return False
    skip = ["example", "test", "spam", "noreply", "no-reply",
            "sentry", "wix", "wordpress", "schema"]
    if any(s in email for s in skip):
        return False
    domain = email.split("@")[1]
    for valid in VALID_EMAIL_DOMAINS:
        if domain == valid or domain.endswith("." + valid):
            return True
    if re.match(r'.+\.(co\.il|org\.il|net\.il|ac\.il|gov\.il|com|net|org)$', domain):
        return True
    if re.match(r'^\d', domain):
        return False
    return False

def is_real_company(title, link):
    title_lower = title.lower()
    link_lower = link.lower()
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
    emails = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}', text)
    for email in emails:
        if is_valid_email(email):
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
                found = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}', text)
                for e in found:
                    if is_valid_email(e):
                        email = e
                        break
            if phone and email:
                break
        except:
            continue
    return phone, email

def search_companies():
    companies = []
    seen_links = set()

    for keyword in COMPANY_KEYWORDS:
        try:
            params = {
                "q": keyword,
                "api_key": SERPAPI_KEY,
                "num": 5,
                "gl": "il",
                "hl": "iw",
                "lr": "lang_iw",
            }
            search = GoogleSearch(params)
            data = search.get_dict()

            for r in data.get("organic_results", []):
                title = r.get("title", "")
                link = r.get("link", "")
                snippet = r.get("snippet", "")

                if link in seen_links:
                    continue
                seen_links.add(link)

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

                if not email:
                    continue

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

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram error: {e}")

def send_companies_csv(companies):
    if not companies:
        send_message("🏢 Новых компаний на этой неделе не найдено.")
        return

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Название", "Телефон", "Email", "Сайт", "Город", "Источник", "Дата"
    ])
    writer.writeheader()
    writer.writerows(companies)
    csv_content = output.getvalue()

    filename = f"companies_{date.today()}.csv"
    save_csv_to_github(filename, csv_content)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {"document": (filename, csv_content.encode("utf-8-sig"), "text/csv")}
    data = {
        "chat_id": CHAT_ID,
        "caption": (
            f"🆕 НОВЫЕ компании за эту неделю\n"
            f"📊 Найдено новых: {len(companies)}\n"
            f"📞 С телефоном: {sum(1 for c in companies if c['Телефон'])}\n"
            f"📧 С email: {sum(1 for c in companies if c['Email'])}\n"
            f"📅 {date.today()}"
        )
    }
    requests.post(url, data=data, files=files)

def main():
    send_message("🚀 Запускаю еженедельный поиск новых компаний...")

    # Читаем ВСЕ предыдущие файлы
    all_known = load_all_known_companies()
    send_message(f"📂 Загружено из всех файлов: {len(all_known)} известных компаний")

    # Ищем новые компании
    all_companies = search_companies()

    # Оставляем только те которых нет НИ В ОДНОМ предыдущем файле
    new_companies = []
    for company in all_companies:
        email = company["Email"].lower()
        site = re.sub(r'https?://(www\.)?', '', company["Сайт"]).split("/")[0].lower()
        if email not in all_known and site not in all_known:
            new_companies.append(company)

    print(f"Total: {len(all_companies)}, New: {len(new_companies)}")

    send_companies_csv(new_companies)

    send_message(
        f"✅ Готово!\n"
        f"🔍 Всего найдено: {len(all_companies)}\n"
        f"🆕 Новых (не было ни в одном файле): {len(new_companies)}"
    )

if __name__ == "__main__":
    main()
