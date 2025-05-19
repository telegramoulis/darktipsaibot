import os
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Load .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

user_scan_times = {}

# Airtable fetch
def get_airtable_record(country):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}"
    }

    today = datetime.utcnow().strftime("%-m/%-d/%Y")  # Airtable format (e.g. 5/19/2025)
    params = {
        "filterByFormula": f"AND(country='{country}', date=DATETIME_PARSE('{today}', 'M/D/YYYY'))"
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if "records" in data and data["records"]:
        return data["records"][0]["fields"]
    return {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fields = get_airtable_record("Greece")  # default content on /start
    photo = fields.get("Photo", [None])[0]['url'] if "Photo" in fields else None
    text = fields.get("intro_text", "Welcome to the bot!")

    keyboard = [[InlineKeyboardButton("🚀 Tap START to access group and activate bot", callback_data="start_bot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if photo:
        await update.message.reply_photo(photo=photo, caption=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# After Start
async def start_bot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fields = get_airtable_record("Greece")
    text = fields.get("after_start_text", "Let's continue!")

    keyboard = [
        [InlineKeyboardButton("📢 Join Main Group", url="https://t.me/YourMainGroup")],
        [InlineKeyboardButton("🤖 Start AI Bot", callback_data="activate_ai")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(text, reply_markup=reply_markup)

# AI Bot Start
async def activate_ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fields = get_airtable_record("Greece")
    photo = fields.get("Photo", [None])[0]['url'] if "Photo" in fields else None
    text = fields.get("main_text", "Here's your feed for today.")

    keyboard = [[InlineKeyboardButton("🔗 CONNECT", callback_data="connect")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if photo:
        await query.message.reply_photo(photo=photo, caption=text, reply_markup=reply_markup)
    else:
        await query.message.reply_text(text, reply_markup=reply_markup)

# Country Selection
async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🇦🇱 Albania", callback_data="scan_Albania")],
        [InlineKeyboardButton("🇬🇷 Greece", callback_data="scan_Greece")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("SELECT COUNTRY TO SCAN:", reply_markup=reply_markup)

# Scan Country
async def scan_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country = query.data.split("_")[1]
    user_id = query.from_user.id

    now = datetime.utcnow()
    last_scan = user_scan_times.get(user_id)
    if last_scan and (now - last_scan).total_seconds() < 16 * 3600:
        remaining = 16 * 3600 - (now - last_scan).total_seconds()
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await query.message.reply_text(f"⏳ You can scan again in {hours}h {minutes}m.")
        return

    user_scan_times[user_id] = now

    fields = get_airtable_record(country)
    msg = fields.get("scan_message", "Act fast before the glitch is gone.")
    final = fields.get("scan_final_text", "SCAN READY ✅")

    await query.message.reply_text(msg)
    await query.message.reply_text(final)

    keyboard = [[InlineKeyboardButton("🔁 SCAN AGAIN", callback_data="connect")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Ready to scan again?", reply_markup=reply_markup)

# Start Bot App
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(start_bot_callback, pattern="^start_bot$"))
app.add_handler(CallbackQueryHandler(activate_ai_callback, pattern="^activate_ai$"))
app.add_handler(CallbackQueryHandler(connect_callback, pattern="^connect$"))
app.add_handler(CallbackQueryHandler(scan_country, pattern="^scan_"))

if __name__ == "__main__":
    app.run_polling()
