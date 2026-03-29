import asyncio
import logging
import random
import os
import sqlite3
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 🔐 TOKEN
USER_BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

ADMIN_ID = 6019703915

user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_user = Dispatcher()
dp_admin = Dispatcher()

# 🌐 SERVER (UPTIMEROBOT FIX)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 💾 DATABASE
conn = sqlite3.connect("system.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    created_at TEXT
)
""")

conn.commit()

# 🔧 CONFIG
def set_config(k, v):
    cur.execute("REPLACE INTO config VALUES (?, ?)", (k, v))
    conn.commit()

def get_config(k, d=None):
    cur.execute("SELECT value FROM config WHERE key=?", (k,))
    r = cur.fetchone()
    return r[0] if r else d

def get_user_count():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

# default
if not get_config("active"): set_config("active", "off")
if not get_config("code"): set_config("code", "1234")
if not get_config("winner_count"): set_config("winner_count", "3")

# 🎛 UI BUTTONS
user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎁 Qatnashish")],
        [KeyboardButton(text="📊 Statistika")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟢 Yoqish"), KeyboardButton(text="🔴 O‘chirish")],
        [KeyboardButton(text="🏆 Winner"), KeyboardButton(text="📊 Stat")],
        [KeyboardButton(text="♻️ New Game"), KeyboardButton(text="📜 History")]
    ],
    resize_keyboard=True
)

# ================= USER =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        await message.answer("⛔ <b>Giveaway faol emas</b>", parse_mode="HTML")
        return

    await message.answer(
        "🎁 <b>SUPER GIVEAWAY</b>\n\n"
        "🏆 Sovrinlar tayyor!\n"
        "🔑 Kod yuboring va qatnashing\n\n"
        "⚡ Shoshiling!",
        parse_mode="HTML",
        reply_markup=user_menu
    )

@dp_user.message(lambda m: m.text == "🎁 Qatnashish")
async def join_btn(message: types.Message):
    await message.answer("🔑 Kodni yuboring:")

@dp_user.message(lambda m: m.text == "📊 Statistika")
async def stat_btn(message: types.Message):
    await message.answer(f"👥 {get_user_count()} ta ishtirokchi")

@dp_user.message()
async def join_user(message: types.Message):
    if get_config("active") != "on":
        return

    if message.text.startswith("/"):
        return

    if message.text != get_config("code"):
        await message.answer("❌ Noto‘g‘ri kod")
        return

    user = message.from_user

    if not user.username:
        await message.answer("❌ Username qo‘ying")
        return

    cur.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    if cur.fetchone():
        await message.answer("ℹ️ Siz qatnashgansiz")
        return

    cur.execute("INSERT INTO users VALUES (?, ?, ?)",
        (user.id, user.username, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

    await message.answer("✅ Qo‘shildingiz! Omad 🍀")

    await admin_bot.send_message(
        ADMIN_ID,
        f"➕ @{user.username}\n📊 {get_user_count()} ta"
    )

# ================= ADMIN =================

def admin_only(func):
    async def wrap(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        await func(message)
    return wrap

@dp_admin.message(Command("start"))
@admin_only
async def admin_start(message: types.Message):
    await message.answer(
        "👑 <b>ADMIN PANEL</b>",
        parse_mode="HTML",
        reply_markup=admin_menu
    )

@dp_admin.message(lambda m: m.text == "🟢 Yoqish")
@admin_only
async def on_bot(message: types.Message):
    set_config("active", "on")
    await message.answer("🟢 Bot yoqildi")

@dp_admin.message(lambda m: m.text == "🔴 O‘chirish")
@admin_only
async def off_bot(message: types.Message):
    set_config("active", "off")
    await message.answer("🔴 Bot o‘chirildi")

@dp_admin.message(lambda m: m.text == "📊 Stat")
@admin_only
async def stat_admin(message: types.Message):
    await message.answer(f"👥 {get_user_count()} ta user")

@dp_admin.message(lambda m: m.text == "🏆 Winner")
@admin_only
async def winner(message: types.Message):

    cur.execute("SELECT username FROM winners")
    old = [x[0] for x in cur.fetchall()]

    cur.execute("SELECT username FROM users")
    users = [x[0] for x in cur.fetchall()]

    available = [u for u in users if u not in old]

    count = int(get_config("winner_count"))

    if len(available) < count:
        await message.answer("❌ Yetarli user yo‘q")
        return

    winners = random.sample(available, count)

    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]

    text = "🏆 <b>G‘OLIBLAR</b>\n\n"

    for i, w in enumerate(winners):
        text += f"{medals[i]} @{w}\n"

        cur.execute("INSERT INTO winners(username, created_at) VALUES (?, ?)",
                    (w, datetime.now().strftime("%Y-%m-%d %H:%M")))

    conn.commit()

    await message.answer(text, parse_mode="HTML")

    for w in winners:
        try:
            cur.execute("SELECT user_id FROM users WHERE username=?", (w,))
            uid = cur.fetchone()[0]
            await user_bot.send_message(uid, "🎉 Siz yutdingiz!")
        except:
            pass

@dp_admin.message(lambda m: m.text == "♻️ New Game")
@admin_only
async def new_game(message: types.Message):
    cur.execute("DELETE FROM users")
    cur.execute("DELETE FROM winners")
    conn.commit()
    await message.answer("♻️ Yangi o‘yin boshlandi")

@dp_admin.message(lambda m: m.text == "📜 History")
@admin_only
async def history(message: types.Message):
    cur.execute("SELECT username, created_at FROM winners ORDER BY id DESC LIMIT 10")
    data = cur.fetchall()

    if not data:
        await message.answer("Bo‘sh")
        return

    text = "📜 <b>History</b>\n\n"

    for w in data:
        text += f"🏅 @{w[0]} — {w[1]}\n"

    await message.answer(text, parse_mode="HTML")

# ================= MAIN =================

async def main():
    logging.basicConfig(level=logging.INFO)

    await user_bot.delete_webhook(drop_pending_updates=True)
    await admin_bot.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(
        dp_user.start_polling(user_bot),
        dp_admin.start_polling(admin_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
