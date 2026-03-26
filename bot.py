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
ADMIN_BOT_TOKEN = "8701209897:AAGTD5uZ5CanLbAq1uVD_qlsKYK6W_okxCQ"

ADMIN_ID = 6019703915
CHANNEL = "@starflow_premium"

user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_user = Dispatcher()
dp_admin = Dispatcher()

# 🌐 SERVER (Render uchun)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

threading.Thread(target=run_server).start()

# 💾 DATABASE
conn = sqlite3.connect("system.db")
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

conn.commit()

# 🔧 CONFIG
def set_config(key, value):
    cur.execute("REPLACE INTO config VALUES (?, ?)", (key, value))
    conn.commit()

def get_config(key, default=None):
    cur.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else default

# default values
if not get_config("active"):
    set_config("active", "off")

if not get_config("code"):
    set_config("code", "1234")

if not get_config("winner_count"):
    set_config("winner_count", "3")

# ================= USER BOT =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        return

    text = (
        "🎁 <b>Giveaway boshlandi!</b>\n\n"
        "🔑 Kodni yuboring va qatnashing\n"
        "📢 Kanalga obuna bo‘lishni unutmang"
    )

    await message.answer(text, parse_mode="HTML")

@dp_user.message()
async def join_user(message: types.Message):
    if get_config("active") != "on":
        return

    code = get_config("code")

    if message.text != code:
        await message.answer("❌ Noto‘g‘ri kod")
        return

    user = message.from_user

    if not user.username:
        await message.answer("❌ Username qo‘ying (@username)")
        return

    if user.is_bot:
        return

    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
        (user.id, user.username, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()

    await message.answer("✅ Siz muvaffaqiyatli qatnashdingiz!")

    # 🔔 ADMINGA SIGNAL
    await admin_bot.send_message(
        ADMIN_ID,
        f"➕ <b>Yangi user</b>\n"
        f"👤 @{user.username}\n"
        f"📊 Jami: {get_user_count()}",
        parse_mode="HTML"
    )

def get_user_count():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

# ================= ADMIN BOT =================

@dp_admin.message(Command("start"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = (
        "👑 <b>ADMIN PANEL</b>\n\n"
        "🟢 /on - botni yoqish\n"
        "🔴 /off - botni o‘chirish\n"
        "📊 /stat - statistika\n"
        "👥 /users - user list\n"
        "🔑 /setcode 1234 - kod\n"
        "🏆 /setwinner 3 - winner soni\n"
        "🎯 /winner - g‘olib\n"
        "🧹 /clear - tozalash\n"
    )

    await message.answer(text, parse_mode="HTML")

# 🔓 ON
@dp_admin.message(Command("on"))
async def on_bot(message: types.Message):
    set_config("active", "on")
    await message.answer("🟢 Bot yoqildi")

# 🔒 OFF
@dp_admin.message(Command("off"))
async def off_bot(message: types.Message):
    set_config("active", "off")
    await message.answer("🔴 Bot o‘chirildi")

# 📊 STAT
@dp_admin.message(Command("stat"))
async def stat(message: types.Message):
    await message.answer(f"👥 Jami: {get_user_count()}")

# 👥 USERS
@dp_admin.message(Command("users"))
async def users(message: types.Message):
    cur.execute("SELECT username, joined_at FROM users ORDER BY joined_at DESC")
    data = cur.fetchall()

    if not data:
        await message.answer("❌ Bo‘sh")
        return

    text = "👥 <b>Userlar:</b>\n\n"
    for u in data[:30]:
        text += f"@{u[0]} ({u[1]})\n"

    await message.answer(text, parse_mode="HTML")

# 🔑 SET CODE
@dp_admin.message(Command("setcode"))
async def setcode(message: types.Message):
    try:
        code = message.text.split()[1]
        set_config("code", code)
        await message.answer(f"🔑 Kod: {code}")
    except:
        await message.answer("❌ /setcode 1234")

# 🏆 SET WINNER COUNT
@dp_admin.message(Command("setwinner"))
async def setwinner(message: types.Message):
    try:
        count = int(message.text.split()[1])
        set_config("winner_count", str(count))
        await message.answer(f"🏆 Winner: {count}")
    except:
        await message.answer("❌ /setwinner 3")

# 🎯 WINNER
@dp_admin.message(Command("winner"))
async def winner(message: types.Message):
    cur.execute("SELECT username FROM users")
    users = [u[0] for u in cur.fetchall()]

    count = int(get_config("winner_count"))

    if len(users) < count:
        await message.answer("❌ User yetarli emas")
        return

    winners = random.sample(users, count)

    text = "🏆 <b>G‘oliblar:</b>\n\n"
    for i, w in enumerate(winners, 1):
        text += f"{i}. @{w}\n"

    await message.answer(text, parse_mode="HTML")

# 🧹 CLEAR
@dp_admin.message(Command("clear"))
async def clear(message: types.Message):
    cur.execute("DELETE FROM users")
    conn.commit()
    await message.answer("🧹 Tozalandi")

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
