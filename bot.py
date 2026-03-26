import asyncio
import logging
import random
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

# 🔐 TOKENLAR (Environment Variables orqali)
USER_BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

ADMIN_ID = 6019703915
CHANNEL = "@starflow_premium"

user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_user = Dispatcher()
dp_admin = Dispatcher()

# 🌐 Fake server (Render uchun)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        pass  # log spamni o'chirish

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 💾 DATABASE
conn = sqlite3.connect("system.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
conn.commit()

# 🔑 CONFIG FUNKSIYALAR
def set_config(key, value):
    cur.execute("INSERT OR REPLACE INTO config VALUES (?,?)", (key, value))
    conn.commit()

def get_config(key):
    cur.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else None

# Default qiymatlar
if not get_config("active"):
    set_config("active", "off")
if not get_config("code"):
    set_config("code", "1234")

def get_user_count():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

# ================= USER BOT =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        await message.answer("⛔ Giveaway hozircha faol emas.")
        return
    await message.answer("🎁 Giveawayga xush kelibsiz!\nIltimos, kodni yuboring:")

@dp_user.message()
async def join_user(message: types.Message):
    if get_config("active") != "on":
        return

    code = get_config("code")

    if message.text != code:
        await message.answer("❌ Noto'g'ri kod. Qaytadan urinib ko'ring.")
        return

    user_id = message.from_user.id
    username = message.from_user.username

    if not username:
        await message.answer("⚠️ Iltimos, Telegram username'ingizni qo'ying va qaytadan yuboring.")
        return

    cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cur.fetchone():
        await message.answer("ℹ️ Siz allaqachon ro'yxatdasiz!")
        return

    cur.execute("INSERT INTO users VALUES (?,?)", (user_id, username))
    conn.commit()

    await message.answer("✅ Muvaffaqiyatli qo'shildingiz! Omad tilaymiz 🍀")

    await admin_bot.send_message(
        ADMIN_ID,
        f"➕ Yangi ishtirokchi: @{username}\n👥 Jami: {get_user_count()} ta"
    )

# ================= ADMIN BOT =================

@dp_admin.message(Command("start"))
async def admin_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "👑 Admin panel\n\n"
        "/on — botni yoqish\n"
        "/off — botni o'chirish\n"
        "/stat — statistika\n"
        "/users — ishtirokchilar ro'yxati\n"
        "/setcode [kod] — yangi kod qo'yish\n"
        "/clear — ro'yxatni tozalash\n"
        "/winner — g'oliblarni aniqlash"
    )

@dp_admin.message(Command("on"))
async def on_bot(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    set_config("active", "on")
    await message.answer("✅ Giveaway yoqildi!")

@dp_admin.message(Command("off"))
async def off_bot(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    set_config("active", "off")
    await message.answer("⛔ Giveaway o'chirildi.")

@dp_admin.message(Command("stat"))
async def stat(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"👥 Jami ishtirokchilar: {get_user_count()} ta")

@dp_admin.message(Command("users"))
async def users_list(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    cur.execute("SELECT username FROM users")
    data = cur.fetchall()
    if not data:
        await message.answer("📭 Hali ishtirokchi yo'q.")
        return
    text = "👥 Ishtirokchilar:\n\n"
    text += "\n".join([f"{i+1}. @{u[0]}" for i, u in enumerate(data[:50])])
    await message.answer(text)

@dp_admin.message(Command("setcode"))
async def setcode(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.answer("❗ Ishlatish: /setcode [yangi_kod]")
        return
    code = parts[1].strip()
    set_config("code", code)
    await message.answer(f"🔑 Yangi kod: {code}")

@dp_admin.message(Command("clear"))
async def clear(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    cur.execute("DELETE FROM users")
    conn.commit()
    await message.answer("🗑 Ro'yxat tozalandi.")

@dp_admin.message(Command("winner"))
async def winner(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    cur.execute("SELECT username FROM users")
    all_users = [u[0] for u in cur.fetchall()]

    if len(all_users) < 3:
        await message.answer(f"⚠️ Kamida 3 ishtirokchi kerak. Hozir: {len(all_users)} ta")
        return

    winners = random.sample(all_users, 3)
    text = "🏆 G'oliblar:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, w in enumerate(winners):
        text += f"{medals[i]} @{w}\n"

    await message.answer(text)

# ================= MAIN =================

async def main():
    logging.basicConfig(level=logging.INFO)

    # ✅ Conflict oldini olish
    await user_bot.delete_webhook(drop_pending_updates=True)
    await admin_bot.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(
        dp_user.start_polling(user_bot),
        dp_admin.start_polling(admin_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
