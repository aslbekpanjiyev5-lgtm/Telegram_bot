import asyncio
import logging
import random
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

# 🔐 TOKENLAR
USER_BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = "8701209897:AAH0FxJhnqOqtydS5eNmBsrcNmtboWLirX0"

ADMIN_ID = 6019703915
CHANNEL = "@starflow_premium"

user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_user = Dispatcher()
dp_admin = Dispatcher()

# 🌐 Fake server
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

threading.Thread(target=run_server).start()

# 💾 DATABASE
conn = sqlite3.connect("system.db")
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT, value TEXT)")
conn.commit()

# 🔑 DEFAULT CONFIG
def set_config(key, value):
    cur.execute("DELETE FROM config WHERE key=?", (key,))
    cur.execute("INSERT INTO config VALUES (?,?)", (key, value))
    conn.commit()

def get_config(key):
    cur.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else None

# default values
if not get_config("active"):
    set_config("active", "off")
if not get_config("code"):
    set_config("code", "1234")

# ================= USER BOT =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        return

    await message.answer("🎁 Giveawayga xush kelibsiz\nKod yuboring:")

@dp_user.message()
async def join_user(message: types.Message):
    if get_config("active") != "on":
        return

    code = get_config("code")

    if message.text != code:
        await message.answer("❌ Noto‘g‘ri kod")
        return

    user_id = message.from_user.id
    username = message.from_user.username

    if not username:
        await message.answer("Username qo‘ying")
        return

    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (user_id, username))
    conn.commit()

    await message.answer("✅ Qo‘shildingiz")

    # 🔔 ADMIN NOTIFY
    await admin_bot.send_message(
        ADMIN_ID,
        f"➕ Yangi user: @{username}\nJami: {get_user_count()}"
    )

def get_user_count():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

# ================= ADMIN BOT =================

@dp_admin.message(Command("start"))
async def admin_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "👑 Admin panel\n\n"
        "/on - botni yoqish\n"
        "/off - botni o‘chirish\n"
        "/stat - statistika\n"
        "/users - userlar\n"
        "/setcode 1234 - kod qo‘yish\n"
        "/clear - tozalash\n"
        "/winner - g‘olib"
    )

@dp_admin.message(Command("on"))
async def on_bot(message: types.Message):
    set_config("active", "on")
    await message.answer("✅ Bot yoqildi")

@dp_admin.message(Command("off"))
async def off_bot(message: types.Message):
    set_config("active", "off")
    await message.answer("⛔ Bot o‘chirildi")

@dp_admin.message(Command("stat"))
async def stat(message: types.Message):
    await message.answer(f"👥 Jami: {get_user_count()}")

@dp_admin.message(Command("users"))
async def users(message: types.Message):
    cur.execute("SELECT username FROM users")
    data = cur.fetchall()

    text = "\n".join([f"@{u[0]}" for u in data[:50]])
    await message.answer(text or "Bo‘sh")

@dp_admin.message(Command("setcode"))
async def setcode(message: types.Message):
    code = message.text.split(" ")[1]
    set_config("code", code)
    await message.answer(f"🔑 Kod: {code}")

@dp_admin.message(Command("clear"))
async def clear(message: types.Message):
    cur.execute("DELETE FROM users")
    conn.commit()
    await message.answer("🗑 Tozalandi")

@dp_admin.message(Command("winner"))
async def winner(message: types.Message):
    cur.execute("SELECT username FROM users")
    users = [u[0] for u in cur.fetchall()]

    if len(users) < 3:
        await message.answer("Kam user")
        return

    winners = random.sample(users, 3)

    text = "🏆 G‘oliblar:\n\n"
    for i, w in enumerate(winners, 1):
        text += f"{i}. @{w}\n"

    await message.answer(text)

# ================= MAIN =================

async def main():
    logging.basicConfig(level=logging.INFO)

    await asyncio.gather(
        dp_user.start_polling(user_bot),
        dp_admin.start_polling(admin_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
