import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request
from threading import Thread

# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))
BASE_URL = os.environ.get("BASE_URL")  # e.g., https://yourapp.up.railway.app
COMMISSION_PERCENT = 30  # user gets 30%
# ============================

# ---------- DATABASE ----------
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

# Users table: id, balance
c.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)""")
# Ads table: id, text, url, reward
c.execute("""CREATE TABLE IF NOT EXISTS ads (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, url TEXT, reward REAL)""")
# Clicks: id, user_id, ad_id
c.execute("""CREATE TABLE IF NOT EXISTS clicks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ad_id INTEGER)""")
# Withdraw requests
c.execute("""CREATE TABLE IF NOT EXISTS withdraw_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending')""")
conn.commit()

# ---------- TELEGRAM BOT ----------
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()
    await update.message.reply_text("✅ সাবস্ক্রাইব হয়ে গেল! /help দিয়ে কমান্ড দেখো।")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "/start - সাবস্ক্রাইব\n"
        "/help - কমান্ড দেখো\n"
        "/ads - বিজ্ঞাপন দেখো\n"
        "/unsub - আনসাবস্ক্রাইব\n"
        "/balance - ব্যালান্স দেখো\n"
        "/withdraw - টাকা চাইতে পারো\n"
    )
    await update.message.reply_text(msg)

async def unsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    await update.message.reply_text("❌ আপনি আনসাবস্ক্রাইব হয়েছেন।")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT balance FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    bal = row[0] if row else 0
    await update.message.reply_text(f"💰 আপনার ব্যালান্স: {bal} BDT")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT balance FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    bal = row[0] if row else 0
    if bal < 50:
        await update.message.reply_text("⚠️ ব্যালান্স খুব কম। অন্তত 50 BDT লাগবে।")
        return
    c.execute("INSERT INTO withdraw_requests (user_id, amount) VALUES (?, ?)", (user_id, bal))
    c.execute("UPDATE users SET balance=0 WHERE id=?", (user_id,))
    conn.commit()
    await update.message.reply_text(f"✅ Withdraw request পাঠানো হলো। Admin approval লাগবে।")

async def ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT id, text, url FROM ads ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    if not rows:
        await update.message.reply_text("কোনো বিজ্ঞাপন নেই।")
        return
    for ad_id, text, url in rows:
        click_url = f"{BASE_URL}/click?user_id={update.effective_user.id}&ad_id={ad_id}"
        button = [[InlineKeyboardButton("🔗 দেখুন", url=click_url)]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(button))

# Admin commands
async def addad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        args = context.args
        reward = float(args[-1])
        url = args[-2]
        text = " ".join(args[:-2])
        c.execute("INSERT INTO ads (text, url, reward) VALUES (?, ?, ?)", (text, url, reward))
        conn.commit()
        await update.message.reply_text("✅ Ad added!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}\nUsage: /addad <text> <url> <reward>")

async def approve_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        req_id = int(context.args[0])
        c.execute("UPDATE withdraw_requests SET status='approved' WHERE id=?", (req_id,))
        conn.commit()
        await update.message.reply_text(f"✅ Withdraw request {req_id} approved.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads")
    ads_count = c.fetchone()[0]
    await update.message.reply_text(f"📊 Users: {users}\n📊 Ads: {ads_count}")

# Register handlers
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("help", help_command))
app_bot.add_handler(CommandHandler("unsub", unsub))
app_bot.add_handler(CommandHandler("balance", balance))
app_bot.add_handler(CommandHandler("withdraw", withdraw))
app_bot.add_handler(CommandHandler("ads", ads))
app_bot.add_handler(CommandHandler("addad", addad))
app_bot.add_handler(CommandHandler("approve_withdraw", approve_withdraw))
app_bot.add_handler(CommandHandler("stats", stats))

# ---------- FLASK SERVER ----------
flask_app = Flask(__name__)

@flask_app.route("/click")
def click():
    try:
        user_id = int(request.args.get("user_id"))
        ad_id = int(request.args.get("ad_id"))
        # check if already clicked
        c.execute("SELECT * FROM clicks WHERE user_id=? AND ad_id=?", (user_id, ad_id))
        if c.fetchone():
            return "Already clicked", 200
        # log click
        c.execute("INSERT INTO clicks (user_id, ad_id) VALUES (?, ?)", (user_id, ad_id))
        # give reward
        c.execute("SELECT reward FROM ads WHERE id=?", (ad_id,))
        reward = c.fetchone()[0]
        commission = reward * COMMISSION_PERCENT / 100
        c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        c.execute("UPDATE users SET balance=balance+? WHERE id=?", (commission, user_id))
        conn.commit()
        return f"Click registered! +{commission} BDT", 200
    except Exception as e:
        return f"Error: {e}", 400

# ---------- RUN BOTH BOT + FLASK ----------
from threading import Thread

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("✅ Bot is running...")
    app_bot.run_polling()

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()
