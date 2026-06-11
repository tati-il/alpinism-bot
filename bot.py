import os
import logging
import requests
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

KEYWORDS_RU = [
    "промышленный альпинизм Израиль",
    "промышленный альпинист",
    "работа на верёвках",
    "работы на высоте",
    "течёт крыша",
    "герметизация швов",
    "герметизация крыши",
    "ремонт фасада",
    "мойка окон снаружи",
    "монтаж на высоте",
    "демонтаж на высоте",
    "высотные работы",
]

KEYWORDS_HE = [
    "עבודות בגובה",
    "פועל גובה",
    "ניקוי חלונות",
    "תיקון גג",
    "גג דולף",
    "איטום גג",
    "תיקון חזית",
    "עבודות חבלים",
    "התקנה בגובה",
    "צביעת חזית",
    "ניקוי גג",
    "אלפיניזם תעשייתי",
    "תחזוקה בגובה",
]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def main():
    send_message("🔍 Начинаю ежедневный поиск клиентов...")
    results = []
    all_keywords = KEYWORDS_RU + KEYWORDS_HE

    with DDGS() as ddgs:
        for keyword in all_keywords:
            try:
                for r in ddgs.text(keyword, max_results=2):
                    results.append(f"🔎 {keyword}\n📌 {r['title']}\n🔗 {r['href']}")
            except Exception as e:
                logging.error(f"Error: {e}")

    if results:
        send_message(f"✅ Найдено результатов: {len(results)}")
        for result in results[:15]:
            send_message(result)
    else:
        send_message("❌ Ничего не найдено сегодня.")

if __name__ == "__main__":
    main()
