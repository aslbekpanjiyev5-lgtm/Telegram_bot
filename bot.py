import asyncio
import logging
import random
import os
import sqlite3
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

# 🔐 TOKEN
USER_BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

ADMIN_ID = 6019703915

user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_user = Dispatcher()
dp_admin = Dispatcher()

# 🌐 SERVER
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot alive")

    def log_message(self, format, *args):
        pass

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 💾 DB
conn = sqlite3.connect("system.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    username TEXT,
    game_id TEXT,
    joined_at TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
)""")

conn.commit()

# CONFIG
def set_config(k, v):
    cur.execute("REPLACE INTO config VALUES (?, ?)", (k, v))
    conn.commit()

def get_config(k, d=None):
    cur.execute("SELECT value FROM config WHERE key=?", (k,))
    r = cur.fetchone()
    return r[0] if r else d

if not get_config("active"): set_config("active", "off")
if not get_config("code"): set_config("code", "1234")
if not get_config("winner_count"): set_config("winner_count", "3")

# ================= USER =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        await message.answer("⛔ Giveaway faol emas")
        return

    await message.answer("🎁 Kodni yuboring!")

@dp_user.message()
async def join(message: types.Message):
    if get_config("active") != "on":
        return

    if message.text != get_config("code"):
        await message.answer("❌ Noto‘g‘ri kod")
        return

    game_id = get_config("current_game")

    user = message.from_user

    if not user.username:
        await message.answer("❌ Username qo‘ying")
        return

    cur.execute("SELECT * FROM users WHERE user_id=? AND game_id=?",
                (user.id, game_id))

    if cur.fetchone():
        await message.answer("ℹ️ Siz qatnashgansiz")
        return

    cur.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                (user.id, user.username, game_id,
                 datetime.now().strftime("%H:%M")))
    conn.commit()

    await message.answer("✅ Qo‘shildingiz!")

# ================= ADMIN =================

def admin_only(func):
    async def wrap(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        await func(message)
    return wrap

@dp_admin.message(Command("start"))
@admin_only
async def admin(message: types.Message):
    await message.answer(
        "👑 ADMIN PANEL\n\n"
        "/on - start game\n"
        "/off - stop\n"
        "/stat\n"
        "/setcode 1234\n"
        "/setwinner 3\n"
        "/winner"
    )

# 🟢 YANGI O‘YIN
@dp_admin.message(Command("on"))
@admin_only
async def on(message: types.Message):
    game_id = str(int(time.time()))
    set_config("current_game", game_id)
    set_config("active", "on")

    await message.answer(f"🟢 Yangi o‘yin boshlandi\nID: {game_id}")

# 🔴 STOP
@dp_admin.message(Command("off"))
@admin_only
async def off(message: types.Message):
    set_config("active", "off")
    await message.answer("🔴 O‘yin to‘xtadi")

# 📊 STAT
@dp_admin.message(Command("stat"))
@admin_only
async def stat(message: types.Message):
    game_id = get_config("current_game")
    cur.execute("SELECT COUNT(*) FROM users WHERE game_id=?", (game_id,))
    c = cur.fetchone()[0]

    await message.answer(f"👥 {c} ta user")

# 🔑 CODE
@dp_admin.message(Command("setcode"))
@admin_only
async def code(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        return
    set_config("code", parts[1])
    await message.answer("✅ Kod o‘zgardi")

# 🏆 WINNER
@dp_admin.message(Command("winner"))
@admin_only
async def winner(message: types.Message):
    game_id = get_config("current_game")

    cur.execute("SELECT user_id, username FROM users WHERE game_id=?", (game_id,))
    users = cur.fetchall()

    count = int(get_config("winner_count"))

    if len(users) < count:
        await message.answer("❌ User yetarli emas")
        return

    winners = random.sample(users, count)

    text = "🏆 G‘oliblar:\n\n"

    for i, (uid, uname) in enumerate(winners, 1):
        text += f"{i}) @{uname}\n"

        try:
            await user_bot.send_message(uid, "🎉 Siz yutdingiz!")
        except:
            pass

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
