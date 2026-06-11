import os
import logging
import requests
from googlesearch import search

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

KEYWORDS = [
    "промышленный альпинизм Израиль",
    "промышленный альпинист",
    "работы на высоте",
    "течёт крыша",
    "герметизация крыши",
    "ремонт фасада высота",
    "мойка окон снаружи",
    "עבודות בגובה",
    "תיקון גג",
    "גג דולף",
    "איטום גג",
    "תיקון חזית",
    "ניקוי חלונות גובה",
]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def main():
    send_message("🔍 Начинаю ежедневный поиск клиентов...")
    results = []

    for keyword in KEYWORDS:
        try:
            for url in search(keyword, num_results=2, lang="ru"):
                results.append(f"🔎 {keyword}\n🔗 {url}")
        except Exception as e:
            logging.error(f"Error: {e}")

    if results:
        send_message(f"✅ Найдено: {len(results)} результатов")
        for result in results[:15]:
            send_message(result)
    else:
        send_message("❌ Ничего не найдено сегодня.")

if __name__ == "__main__":
    main()
