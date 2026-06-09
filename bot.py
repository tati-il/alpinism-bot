import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")

KEYWORDS_RU = [
    "промышленный альпинизм",
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
    "утепление фасада",
    "покраска фасада",
    "высотные работы",
]

KEYWORDS_HE = [
    "עבודות בגובה",
    "פועל גובה",
    "ניקוי חלונות",
    "ניקוי חלונות גובה",
    "תיקון גג",
    "גג דולף",
    "איטום גג",
    "איטום חזית",
    "תיקון חזית",
    "עבודות חבלים",
    "התקנה בגובה",
    "פירוק בגובה",
    "צביעת חזית",
    "בידוד חזית",
    "ניקוי גג",
    "אלפיניזם תעשייתי",
    "עבודות סנפלינג",
    "תחזוקה בגובה",
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👷 Привет! Я бот для поиска клиентов по промышленному альпинизму.\n\n"
        "Команды:\n"
        "/search — найти новые запросы\n"
        "/help — помощь"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Ищу клиентов... Это займёт минуту.")
    results = []
    all_keywords = KEYWORDS_RU + KEYWORDS_HE

    with DDGS() as ddgs:
        for keyword in all_keywords:
            try:
                for r in ddgs.text(keyword, max_results=2):
                    results.append(f"🔎 *{keyword}*\n📌 {r['title']}\n🔗 {r['href']}\n")
            except Exception as e:
                logging.error(f"Error searching {keyword}: {e}")

    if results:
        await update.message.reply_text(f"✅ Найдено: {len(results)} результатов\n\nПоказываю первые 15:")
        for result in results[:15]:
            try:
                await update.message.reply_text(result, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(result)
    else:
        await update.message.reply_text("❌ Ничего не найдено. Попробуй позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👷 Бот ищет клиентов на русском и иврите через DuckDuckGo.\n\n"
        "/search — запустить поиск\n"
        "/start — начало"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()

if __name__ == "__main__":
    main()
