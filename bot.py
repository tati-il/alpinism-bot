import os
import csv
import logging
import requests
import re
import base64
from datetime import date
from serpapi import GoogleSearch
from io import StringIO, BytesIO

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

MASTER_FILE = "master_companies.xlsx"

def get_file_from_github(filename):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"])
            sha = data["sha"]
            return content, sha
        return None, None
    except Exception as e:
        print(f"Error getting file: {e}")
        return None, None

def load_known_emails_from_master():
    known = set()
    try:
        import pandas as pd
        content, sha = get_file_from_github(MASTER_FILE)
        if not content:
            print("Master file not found")
            return known, None
        df = pd.read_excel(BytesIO(content))
        for _, row in df.iterrows():
            for col in df.columns:
                val = str(row[col]).strip().lower()
                if "@" in val and "." in val and val != "nan":
                    known.add(val)
                if "http" in val:
                    domain = re.sub(r'https?://(www\.)?', '', val).split("/")[0]
                    if domain and domain != "nan":
                        known.add(domain)
        print(f"Loaded {len(known)} known entries from master file")
        return known, sha
    except Exception as e:
        print(f"Error loading master: {e}")
        return known, None

def append_to_master(new_companies):
    try:
        import pandas as pd
        content, sha = get_file_from_github(MASTER_FILE)
        if content:
            df_existing = pd.read_excel(BytesIO(content))
        else:
            df_existing = pd.DataFrame(columns=[
                "שם", "עיר", "מייל", "אתר", "טלפון", "שליחת מייל", "קבלת מענה", "האם נסגרה עסקהחוזה"
            ])

        new_rows = []
        for c in new_companies:
            new_rows.append({
                "שם": c["Название"],
                "עיר": c["Город"],
                "מייל": c["Email"],
                "אתר": c["Сайт"],
                "טלפון": c["Телефон"],
                "שליחת מייל": "",
                "קבלת מענה": "",
                "האם נסגרה עסקהחוזה": "",
            })

        df_new = pd.DataFrame(new_rows)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)

        output = BytesIO()
        df_combined.to_excel(output, index=False)
        output.seek(0)
        file_content = output.read()

        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{MASTER_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }
        encoded = base64.b64encode(file_content).decode("utf-8")
        payload = {
            "message": f"Add {len(new_companies)} new companies {date.today()}",
            "content": encoded,
        }
        if sha:
            payload["sha"] = sha

        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"Master file updated with {len(new_companies)} new companies")
            return True
        else:
            print(f"Error updating master: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error appending to master: {e}")
        return False

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
    "/קורס/", "/course/",
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
        send_message("🏢 Новых компаний не найдено.")
        return

    fieldnames = ["Название", "Телефон", "Email", "Сайт", "Город", "Дата"]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(companies)
    csv_content = output.getvalue()

    filename = f"new_companies_{date.today()}.csv"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {"document": (filename, csv_content.encode("utf-8-sig"), "text/csv")}
    data = {
        "chat_id": CHAT_ID,
        "caption": (
            f"🆕 НОВЫЕ компании\n"
            f"📊 Найдено новых: {len(companies)}\n"
            f"📞 С телефоном: {sum(1 for c in companies if c['Телефон'])}\n"
            f"📧 С email: {sum(1 for c in companies if c['Email'])}\n"
            f"📅 {date.today()}"
        )
    }
    requests.post(url, data=data, files=files)

def main():
    send_message("🚀 Запускаю еженедельный поиск...")

    known, sha = load_known_emails_from_master()
    send_message(f"📂 В главном файле: {len(known)} известных записей")

    all_companies = search_companies()

    new_companies = []
    for company in all_companies:
        email = company["Email"].lower()
        site = re.sub(r'https?://(www\.)?', '', company["Сайт"]).split("/")[0].lower()
        if email not in known and site not in known:
            new_companies.append(company)

    print(f"Total: {len(all_companies)}, New: {len(new_companies)}")

    if new_companies:
        append_to_master(new_companies)
        send_companies_csv(new_companies)
    else:
        send_message("🏢 Новых компаний не найдено.")

    send_message(
        f"✅ Готово!\n"
        f"🔍 Всего найдено: {len(all_companies)}\n"
        f"🆕 Новых: {len(new_companies)}\n"
        f"📊 Добавлено в главный файл"
    )

if __name__ == "__main__":
    main()
