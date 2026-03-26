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

# 🌐 SERVER
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")
    def log_message(self, format, *args):
        pass

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 💾 DATABASE
conn = sqlite3.connect("system.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined_at TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
)""")
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

if not get_config("active"): set_config("active", "off")
if not get_config("code"): set_config("code", "1234")
if not get_config("winner_count"): set_config("winner_count", "3")

# ================= USER BOT =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        await message.answer("⛔ Giveaway hozircha faol emas.")
        return
    await message.answer(
        "🎁 <b>Giveaway boshlandi!</b>\n\n"
        "🔑 Kodni yuboring va qatnashing!",
        parse_mode="HTML"
    )

@dp_user.message()
async def join_user(message: types.Message):
    if get_config("active") != "on":
        return

    if message.text != get_config("code"):
        await message.answer("❌ Noto'g'ri kod")
        return

    user = message.from_user
    if not user.username:
        await message.answer("❌ Telegram username qo'ying")
        return

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if cur.fetchone():
        await message.answer("ℹ️ Siz allaqachon qatnashyapsiz!")
        return

    cur.execute("INSERT INTO users VALUES (?, ?, ?)",
        (user.id, user.username, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

    await message.answer("✅ Muvaffaqiyatli qatnashdingiz! Omad! 🍀")
    await admin_bot.send_message(
        ADMIN_ID,
        f"➕ <b>Yangi user:</b> @{user.username}\n📊 Jami: {get_user_count()}",
        parse_mode="HTML"
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
        "👑 <b>ADMIN PANEL</b>\n\n"
        "🟢 /on — botni yoqish\n"
        "🔴 /off — botni o'chirish\n"
        "📊 /stat — statistika\n"
        "👥 /users — userlar ro'yxati\n"
        "🔑 /setcode 1234 — kod o'zgartirish\n"
        "🏆 /setwinner 3 — g'oliblar soni\n"
        "🎯 /winner — g'oliblarni aniqlash\n"
        "🧹 /clear — ro'yxatni tozalash",
        parse_mode="HTML"
    )

@dp_admin.message(Command("on"))
@admin_only
async def on_bot(message: types.Message):
    set_config("active", "on")
    await message.answer("🟢 Giveaway yoqildi!")

@dp_admin.message(Command("off"))
@admin_only
async def off_bot(message: types.Message):
    set_config("active", "off")
    await message.answer("🔴 Giveaway o'chirildi.")

@dp_admin.message(Command("stat"))
@admin_only
async def stat(message: types.Message):
    await message.answer(f"👥 Jami ishtirokchilar: {get_user_count()} ta")

@dp_admin.message(Command("users"))
@admin_only
async def users_list(message: types.Message):
    cur.execute("SELECT username, joined_at FROM users ORDER BY joined_at DESC")
    data = cur.fetchall()
    if not data:
        await message.answer("📭 Hali ishtirokchi yo'q.")
        return
    text = "👥 <b>Ishtirokchilar:</b>\n\n"
    for u in data[:30]:
        text += f"@{u[0]} — {u[1]}\n"
    await message.answer(text, parse_mode="HTML")

@dp_admin.message(Command("setcode"))
@admin_only
async def setcode(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❗ /setcode 1234")
        return
    set_config("code", parts[1])
    await message.answer(f"🔑 Yangi kod: {parts[1]}")

@dp_admin.message(Command("setwinner"))
@admin_only
async def setwinner(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❗ /setwinner 3")
        return
    set_config("winner_count", parts[1])
    await message.answer(f"🏆 G'oliblar soni: {parts[1]}")

@dp_admin.message(Command("winner"))
@admin_only
async def winner(message: types.Message):
    cur.execute("SELECT username FROM users")
    all_users = [u[0] for u in cur.fetchall()]
    count = int(get_config("winner_count", "3"))
    if len(all_users) < count:
        await message.answer(f"⚠️ Kamida {count} ta ishtirokchi kerak. Hozir: {len(all_users)}")
        return
    winners = random.sample(all_users, count)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 10
    text = "🏆 <b>G'oliblar:</b>\n\n"
    for i, w in enumerate(winners):
        text += f"{medals[i]} @{w}\n"
    await message.answer(text, parse_mode="HTML")

@dp_admin.message(Command("clear"))
@admin_only
async def clear(message: types.Message):
    cur.execute("DELETE FROM users")
    conn.commit()
    await message.answer("🧹 Ro'yxat tozalandi.")

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
