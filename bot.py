import os
import logging
import requests
from serpapi import GoogleSearch

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

KEYWORDS = [
    "עבודות בגובה",
    "תיקון גג",
    "промышленный альпинизм Израиль",
    "протечка крыши Израиль",
]

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": text})
        print(f"Telegram response: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    # Проверка переменных
    print(f"BOT_TOKEN exists: {bool(BOT_TOKEN)}")
    print(f"CHAT_ID: {CHAT_ID}")
    print(f"SERPAPI_KEY exists: {bool(SERPAPI_KEY)}")

    send_message("🔧 ДЕБАГ: Бот запущен")
    send_message(f"🔧 CHAT_ID: {CHAT_ID}")
    send_message(f"🔧 SERPAPI_KEY есть: {bool(SERPAPI_KEY)}")

    results = []

    for keyword in KEYWORDS:
        try:
            send_message(f"🔍 Ищу: {keyword}")
            params = {
                "q": keyword,
                "api_key": SERPAPI_KEY,
                "num": 2,
                "gl": "il",
            }
            search = GoogleSearch(params)
            data = search.get_dict()

            # Дебаг ответа
            print(f"Keys in response: {list(data.keys())}")
            organic = data.get("organic_results", [])
            send_message(f"🔧 Найдено для '{keyword}': {len(organic)} результатов")

            for r in organic:
                results.append(f"🔎 {keyword}\n📌 {r.get('title')}\n🔗 {r.get('link')}")

        except Exception as e:
            send_message(f"❌ Ошибка для '{keyword}': {str(e)}")
            print(f"Error: {e}")

    send_message(f"✅ Итого найдено: {len(results)}")
    for result in results:
        send_message(result)

if __name__ == "__main__":
    main()
