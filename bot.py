import asyncio
import logging
import random
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# 🌐 Fake server (Render uchun)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()

threading.Thread(target=run_server).start()

# 🔐 TOKEN
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

CHANNEL = "@starflow_premium"
ADMIN_ID = 6019703915

# 💾 DATABASE (SQLite)
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")
conn.commit()

# 📢 OBUNA TEKSHIRISH
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

# 📋 MENU
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎁 Qo‘shilish")],
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🏆 Winner")]
    ],
    resize_keyboard=True
)

# 🚀 START
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🔥 Giveaway botga xush kelibsiz!", reply_markup=menu)

# 🎁 JOIN
@dp.message(lambda m: m.text == "🎁 Qo‘shilish")
async def join(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if not username:
        await message.answer("❌ Username qo‘ying (@username)")
        return

    if message.from_user.is_bot:
        return

    if not await check_sub(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Obuna", url="https://t.me/starflow_premium")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check")]
        ])
        await message.answer("❌ Kanalga obuna bo‘ling", reply_markup=kb)
        return

    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user_id, username))
    conn.commit()

    await message.answer("✅ Siz qo‘shildingiz")

# 📊 STAT
@dp.message(lambda m: m.text == "📊 Statistika")
async def stat(message: types.Message):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    await message.answer(f"👥 Jami: {count} ta")

# 🏆 WINNER (3 ta)
@dp.message(lambda m: m.text == "🏆 Winner")
async def winner(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Faqat admin")
        return

    cursor.execute("SELECT user_id, username FROM users")
    users = cursor.fetchall()

    if len(users) < 3:
        await message.answer("❌ Kamida 3 user kerak")
        return

    winners = random.sample(users, 3)

    text = "🏆 G‘oliblar:\n\n"
    for i, w in enumerate(winners, 1):
        text += f"{i}. @{w[1]}\n"

    await message.answer(text)

# 🔘 CHECK BUTTON
@dp.callback_query(lambda c: c.data == "check")
async def check_btn(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username

    if await check_sub(user_id):
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user_id, username))
        conn.commit()
        await callback.message.answer("✅ Qo‘shildingiz")
    else:
        await callback.message.answer("❌ Obuna yo‘q")

# 👑 ADMIN PANEL
@dp.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Bazani tozalash", callback_data="clear")]
    ])

    await message.answer("👑 Admin panel", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "clear")
async def clear(callback: types.CallbackQuery):
    cursor.execute("DELETE FROM users")
    conn.commit()
    await callback.message.answer("🗑 Baza tozalandi")

# ▶️ MAIN
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
