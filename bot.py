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
# РАБОТА С ФАЙЛАМИ ЧЕРЕЗ GITHUB
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

def get_last_csv_file():
    """Находим последний CSV файл с компаниями — любое имя"""
    try:
        files = get_github_files()
        # Ищем все CSV файлы кроме requirements
        csv_files = [
            f for f in files
            if f["name"].endswith(".csv") and "requirements" not in f["name"]
        ]
        if not csv_files:
            return None, None

        # Сортируем по дате последнего обновления и берём последний
        csv_files.sort(key=lambda x: x.get("name", ""), reverse=True)
        last_file = csv_files[0]

        print(f"Found previous file: {last_file['name']}")

        # Читаем содержимое файла
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(last_file["download_url"], headers=headers)
        if response.status_code == 200:
            return last_file["name"], response.content.decode("utf-8-sig", errors="ignore")
        return None, None

    except Exception as e:
        print(f"Error reading last CSV: {e}")
        return None, None

def load_previous_emails(csv_content):
    """Извлекаем все email и сайты из предыдущего файла"""
    known = set()
    if not csv_content:
        return known
    try:
        # Пробуем разные разделители
        for delimiter in [",", ";"]:
            try:
                reader = csv.DictReader(StringIO(csv_content), delimiter=delimiter)
                rows = list(reader)
                if not rows:
                    continue

                for row in rows:
                    # Ищем email в любой колонке
                    for key, value in row.items():
                        val = (value or "").strip().lower()
                        if "@" in val and "." in val:
                            known.add(val)
                        # Ищем сайт
                        if "http" in val:
                            # Берём только домен
                            domain = re.sub(r'https?://(www\.)?', '', val).split("/")[0]
                            if domain:
                                known.add(domain)
                break
            except:
                continue

    except Exception as e:
        print(f"Error parsing CSV: {e}")
    print(f"Loaded {len(known)} known entries from previous file")
    return known

def save_csv_to_github(filename, csv_content):
    """Сохраняем новый CSV файл в GitHub"""
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
            print(f"Error saving: {response.status_code} {response.text}")
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

    # Загружаем последний файл (любое имя)
    last_filename, last_content = get_last_csv_file()
    if last_filename:
        send_message(f"📂 Сравниваю с файлом: {last_filename}")
        previous = load_previous_emails(last_content)
    else:
        send_message("📂 Предыдущего файла нет — первый запуск")
        previous = set()

    # Ищем компании
    all_companies = search_companies()

    # Оставляем только новые
    new_companies = []
    for company in all_companies:
        email = company["Email"].lower()
        site = re.sub(r'https?://(www\.)?', '', company["Сайт"]).split("/")[0].lower()
        if email not in previous and site not in previous:
            new_companies.append(company)

    print(f"Total: {len(all_companies)}, New: {len(new_companies)}")

    send_companies_csv(new_companies)

    send_message(
        f"✅ Готово!\n"
        f"🔍 Всего найдено: {len(all_companies)}\n"
        f"🆕 Новых: {len(new_companies)}"
    )

if __name__ == "__main__":
    main()
