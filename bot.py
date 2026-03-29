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

# 🔐 TOKENLAR
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
def set_config(key, value):
    cur.execute("REPLACE INTO config VALUES (?, ?)", (key, value))
    conn.commit()

def get_config(key, default=None):
    cur.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else default

def get_user_count():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

# default values
if not get_config("active"): set_config("active", "off")
if not get_config("code"): set_config("code", "1234")
if not get_config("winner_count"): set_config("winner_count", "3")

# ================= USER BOT =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        await message.answer("⛔ Giveaway hozir faol emas.")
        return
    await message.answer("🎁 Giveaway boshlandi!\n\n🔑 Kodni yuboring.")

@dp_user.message()
async def join_user(message: types.Message):
    if get_config("active") != "on":
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
        await message.answer("ℹ️ Siz allaqachon qatnashgansiz")
        return

    cur.execute("INSERT INTO users VALUES (?, ?, ?)",
        (user.id, user.username, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

    await message.answer("✅ Qatnashdingiz!")

    await admin_bot.send_message(
        ADMIN_ID,
        f"➕ @{user.username} qo‘shildi\n📊 Jami: {get_user_count()}"
    )

# ================= ADMIN BOT =================

def admin_only(func):
    async def wrapper(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        await func(message)
    return wrapper

@dp_admin.message(Command("start"))
@admin_only
async def admin_panel(message: types.Message):
    await message.answer(
        "👑 ADMIN PANEL\n\n"
        "/on - yoqish\n"
        "/off - o‘chirish\n"
        "/stat - statistika\n"
        "/setcode 1234\n"
        "/setwinner 3\n"
        "/winner - tanlash\n"
        "/newgame - yangi o‘yin\n"
        "/history - history"
    )

@dp_admin.message(Command("on"))
@admin_only
async def on_bot(message: types.Message):
    set_config("active", "on")
    await message.answer("🟢 Bot yoqildi")

@dp_admin.message(Command("off"))
@admin_only
async def off_bot(message: types.Message):
    set_config("active", "off")
    await message.answer("🔴 Bot o‘chdi")

@dp_admin.message(Command("stat"))
@admin_only
async def stat(message: types.Message):
    await message.answer(f"👥 {get_user_count()} ta user")

@dp_admin.message(Command("setcode"))
@admin_only
async def setcode(message: types.Message):
    code = message.text.split()[1]
    set_config("code", code)
    await message.answer(f"🔑 Kod: {code}")

@dp_admin.message(Command("setwinner"))
@admin_only
async def setwinner(message: types.Message):
    count = message.text.split()[1]
    set_config("winner_count", count)
    await message.answer(f"🏆 Winner: {count}")

# 🔥 WINNER FIXED
@dp_admin.message(Command("winner"))
@admin_only
async def winner(message: types.Message):

    # old winners check
    cur.execute("SELECT username FROM winners")
    old = [x[0] for x in cur.fetchall()]

    cur.execute("SELECT username FROM users")
    users = [x[0] for x in cur.fetchall()]

    available = [u for u in users if u not in old]

    count = int(get_config("winner_count", "3"))

    if len(available) < count:
        await message.answer("❌ Yetarli user yo‘q")
        return

    winners = random.sample(available, count)

    for w in winners:
        cur.execute("INSERT INTO winners(username, created_at) VALUES (?, ?)",
                    (w, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

    text = "🏆 G'oliblar:\n\n"
    for i, w in enumerate(winners, 1):
        text += f"{i}. @{w}\n"

    await message.answer(text)

    # 🔥 congrat message
    for w in winners:
        try:
            cur.execute("SELECT user_id FROM users WHERE username=?", (w,))
            uid = cur.fetchone()[0]
            await user_bot.send_message(uid, "🎉 Tabriklaymiz! Siz yutdingiz!")
        except:
            pass

# 🔄 NEW GAME
@dp_admin.message(Command("newgame"))
@admin_only
async def newgame(message: types.Message):
    cur.execute("DELETE FROM users")
    cur.execute("DELETE FROM winners")
    conn.commit()
    await message.answer("♻️ Yangi o‘yin boshlandi")

# 📜 HISTORY
@dp_admin.message(Command("history"))
@admin_only
async def history(message: types.Message):
    cur.execute("SELECT username, created_at FROM winners ORDER BY id DESC LIMIT 10")
    data = cur.fetchall()

    if not data:
        await message.answer("Bo‘sh")
        return

    text = "📜 Oxirgi winnerlar:\n\n"
    for w in data:
        text += f"@{w[0]} - {w[1]}\n"

    await message.answer(text)

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
