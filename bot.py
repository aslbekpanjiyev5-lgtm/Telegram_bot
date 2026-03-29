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

# ╔══════════════════════════════════════╗
# ║         🔐 TOKEN SOZLAMA            ║
# ╚══════════════════════════════════════╝
USER_BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID        = 6019703915

user_bot  = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_user  = Dispatcher()
dp_admin = Dispatcher()

# ╔══════════════════════════════════════╗
# ║       🌐 SERVER (Render fix)        ║
# ╚══════════════════════════════════════╝
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

# ╔══════════════════════════════════════╗
# ║         💾 DATABASE                 ║
# ╚══════════════════════════════════════╝
conn = sqlite3.connect("system.db", check_same_thread=False)
cur  = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    joined_at  TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS winners (
    username TEXT PRIMARY KEY
)
""")

conn.commit()

# ╔══════════════════════════════════════╗
# ║         ⚙️ CONFIG                   ║
# ╚══════════════════════════════════════╝
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

if not get_config("active"):      set_config("active",       "off")
if not get_config("code"):        set_config("code",         "1234")
if not get_config("winner_count"):set_config("winner_count", "1")

# ╔══════════════════════════════════════╗
# ║         🎛 KLAVIATURA               ║
# ╚══════════════════════════════════════╝
user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎁 Qatnashish")],
        [KeyboardButton(text="📊 Statistika")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟢 Yoqish"),      KeyboardButton(text="🔴 O'chirish")],
        [KeyboardButton(text="🏆 Winner"),       KeyboardButton(text="📊 Stat")],
        [KeyboardButton(text="⚙️ Winner soni"),  KeyboardButton(text="♻️ New Game")]
    ],
    resize_keyboard=True
)

# ╔══════════════════════════════════════╗
# ║         👤 USER BOT                 ║
# ╚══════════════════════════════════════╝

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        await message.answer(
            "╔═══════════════════╗\n"
            "║   ⏳ KUTISH REJIMI  ║\n"
            "╚═══════════════════╝\n\n"
            "🚫 Giveaway hali boshlanmagan!\n"
            "📢 Tez kunda e'lon qilinadi...\n\n"
            "🔔 Kuzatib boring!"
        )
        return

    await message.answer(
        "╔═══════════════════════╗\n"
        "║   🎉 GIVEAWAY BOT   ║\n"
        "╚═══════════════════════╝\n\n"
        "✨ Xush kelibsiz!\n\n"
        "📌 Qanday qatnashish mumkin:\n"
        "  1️⃣  « 🎁 Qatnashish » tugmasini bosing\n"
        "  2️⃣  Maxsus kodni yuboring\n"
        "  3️⃣  G'oliblar e'lonini kuting!\n\n"
        "🍀 Omad tilaymiz!",
        reply_markup=user_menu
    )

@dp_user.message(lambda m: m.text == "🎁 Qatnashish")
async def ask_code(message: types.Message):
    if get_config("active") != "on":
        await message.answer("⏳ Giveaway hali aktiv emas!")
        return
    await message.answer(
        "🔑 *Maxsus kodni yuboring:*\n\n"
        "💡 Kodni to'g'ri kiriting va ishtirokchi bo'ling!",
        parse_mode="Markdown"
    )

@dp_user.message(lambda m: m.text == "📊 Statistika")
async def stat_user(message: types.Message):
    count = get_user_count()
    await message.answer(
        "╔══════════════════════╗\n"
        "║    📊 STATISTIKA    ║\n"
        "╚══════════════════════╝\n\n"
        f"👥 Ishtirokchilar: *{count}* ta\n\n"
        "🍀 Siz ham qatnashing!",
        parse_mode="Markdown"
    )

@dp_user.message()
async def join_user(message: types.Message):
    if get_config("active") != "on":
        return

    if message.text.startswith("/"):
        return

    if message.text != get_config("code"):
        await message.answer(
            "❌ *Noto'g'ri kod!*\n\n"
            "🔑 Kodni qayta tekshirib yuboring.",
            parse_mode="Markdown"
        )
        return

    user = message.from_user

    if not user.username:
        await message.answer(
            "⚠️ *Username topilmadi!*\n\n"
            "📝 Telegram sozlamalaridan @username o'rnating\n"
            "va qaytadan urinib ko'ring.",
            parse_mode="Markdown"
        )
        return

    cur.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    if cur.fetchone():
        await message.answer(
            "ℹ️ *Siz allaqachon ishtirokchisiz!*\n\n"
            "⏳ G'oliblar e'lonini kuting...\n"
            "🍀 Omad bo'lsin!",
            parse_mode="Markdown"
        )
        return

    cur.execute(
        "INSERT INTO users VALUES (?, ?, ?)",
        (user.id, user.username, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()

    await message.answer(
        "╔══════════════════════════╗\n"
        "║  ✅ MUVAFFAQIYATLI!    ║\n"
        "╚══════════════════════════╝\n\n"
        f"🎊 @{user.username}, siz ro'yxatdan o'tdingiz!\n\n"
        f"👥 Jami ishtirokchilar: *{get_user_count()}* ta\n\n"
        "🍀 Omad tilaymiz! G'oliblar tez kunda e'lon qilinadi!",
        parse_mode="Markdown"
    )

    await admin_bot.send_message(
        ADMIN_ID,
        f"🔔 *Yangi ishtirokchi!*\n\n"
        f"👤 @{user.username}\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}\n"
        f"📊 Jami: *{get_user_count()}* ta",
        parse_mode="Markdown"
    )

# ╔══════════════════════════════════════╗
# ║         👑 ADMIN BOT                ║
# ╚══════════════════════════════════════╝

def admin_only(func):
    async def wrapper(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("🚫 Ruxsat yo'q!")
            return
        await func(message)
    return wrapper

@dp_admin.message(Command("start"))
@admin_only
async def admin_start(message: types.Message):
    status = "🟢 Aktiv" if get_config("active") == "on" else "🔴 Nofaol"
    await message.answer(
        "╔══════════════════════════╗\n"
        "║    👑 ADMIN PANEL      ║\n"
        "╚══════════════════════════╝\n\n"
        f"📌 Holat: {status}\n"
        f"👥 Ishtirokchilar: *{get_user_count()}* ta\n"
        f"🏆 Winner soni: *{get_config('winner_count')}* ta\n\n"
        "⬇️ Kerakli bo'limni tanlang:",
        reply_markup=admin_menu,
        parse_mode="Markdown"
    )

@dp_admin.message(lambda m: m.text == "🟢 Yoqish")
@admin_only
async def on_bot(message: types.Message):
    set_config("active", "on")
    await message.answer(
        "╔══════════════════════════╗\n"
        "║    🟢 BOT YOQILDI!    ║\n"
        "╚══════════════════════════╝\n\n"
        "✅ Giveaway boshlandi!\n"
        "👥 Foydalanuvchilar qatnasha oladi."
    )

@dp_admin.message(lambda m: m.text == "🔴 O'chirish")
@admin_only
async def off_bot(message: types.Message):
    set_config("active", "off")
    await message.answer(
        "╔══════════════════════════╗\n"
        "║   🔴 BOT O'CHIRILDI!  ║\n"
        "╚══════════════════════════╝\n\n"
        "⛔ Giveaway to'xtatildi.\n"
        "📌 Qayta yoqish uchun 🟢 Yoqish tugmasini bosing."
    )

@dp_admin.message(lambda m: m.text == "📊 Stat")
@admin_only
async def stat_admin(message: types.Message):
    count  = get_user_count()
    status = "🟢 Aktiv" if get_config("active") == "on" else "🔴 Nofaol"

    cur.execute("SELECT COUNT(*) FROM winners")
    winner_count = cur.fetchone()[0]

    await message.answer(
        "╔══════════════════════════╗\n"
        "║      📊 STATISTIKA     ║\n"
        "╚══════════════════════════╝\n\n"
        f"📌 Holat:         {status}\n"
        f"👥 Ishtirokchilar: *{count}* ta\n"
        f"🏆 G'oliblar:      *{winner_count}* ta\n"
        f"🎯 Winner kvotasi: *{get_config('winner_count')}* ta\n"
        f"🕐 Vaqt: {datetime.now().strftime('%H:%M — %d.%m.%Y')}",
        parse_mode="Markdown"
    )

@dp_admin.message(lambda m: m.text == "⚙️ Winner soni")
@admin_only
async def ask_winner_count(message: types.Message):
    await message.answer(
        "⚙️ *Winner soni sozlash*\n\n"
        f"📌 Hozirgi qiymat: *{get_config('winner_count')}* ta\n\n"
        "🔢 Yangi sonni yuboring (masalan: 3):",
        parse_mode="Markdown"
    )

@dp_admin.message(lambda m: m.text.isdigit())
@admin_only
async def set_winner_count(message: types.Message):
    set_config("winner_count", message.text)
    await message.answer(
        f"✅ *Winner soni yangilandi!*\n\n"
        f"🏆 Yangi qiymat: *{message.text}* ta",
        parse_mode="Markdown"
    )

@dp_admin.message(lambda m: m.text == "🏆 Winner")
@admin_only
async def winner(message: types.Message):
    cur.execute("SELECT username FROM winners")
    old = [x[0] for x in cur.fetchall()]

    cur.execute("SELECT username FROM users")
    users = [x[0] for x in cur.fetchall()]

    available = [u for u in users if u not in old]
    count     = int(get_config("winner_count"))

    if len(available) < count:
        await message.answer(
            "╔══════════════════════════╗\n"
            "║      ⚠️ XATOLIK!       ║\n"
            "╚══════════════════════════╝\n\n"
            f"❌ Yetarli ishtirokchi yo'q!\n\n"
            f"👥 Mavjud: *{len(available)}* ta\n"
            f"🎯 Kerakli: *{count}* ta",
            parse_mode="Markdown"
        )
        return

    winners = random.sample(available, count)
    medals  = ["🥇", "🥈", "🥉", "🏅", "🎖️"]

    text = (
        "╔══════════════════════════╗\n"
        "║    🏆 G'OLIBLAR!       ║\n"
        "╚══════════════════════════╝\n\n"
    )

    for i, w in enumerate(winners):
        medal  = medals[i] if i < len(medals) else "🎖️"
        text  += f"{medal} @{w}\n"
        cur.execute("INSERT OR IGNORE INTO winners VALUES (?)", (w,))

    conn.commit()

    text += f"\n🎊 Tabriklaymiz!\n👥 Jami ishtirokchilar: *{get_user_count()}* ta"

    await message.answer(text, parse_mode="Markdown")

    for w in winners:
        try:
            cur.execute("SELECT user_id FROM users WHERE username=?", (w,))
            uid = cur.fetchone()[0]
            await user_bot.send_message(
                uid,
                "╔══════════════════════════╗\n"
                "║   🎉 TABRIKLAYMIZ!     ║\n"
                "╚══════════════════════════╝\n\n"
                f"🏆 Hurmatli @{w}!\n\n"
                "✨ Siz giveaway g'olibi sifatida\n"
                "   tanlab olindingiz!\n\n"
                "📩 Admin siz bilan tez orada\n"
                "   bog'lanadi.\n\n"
                "🌟 Omadingiz doim kulib tursin!"
            )
        except:
            pass

@dp_admin.message(lambda m: m.text == "♻️ New Game")
@admin_only
async def reset(message: types.Message):
    cur.execute("DELETE FROM users")
    cur.execute("DELETE FROM winners")
    conn.commit()
    set_config("active", "off")

    await message.answer(
        "╔══════════════════════════╗\n"
        "║    ♻️ YANGI O'YIN!     ║\n"
        "╚══════════════════════════╝\n\n"
        "✅ Barcha ma'lumotlar tozalandi!\n\n"
        "📋 Nima tozalandi:\n"
        "  🗑️ Barcha ishtirokchilar\n"
        "  🗑️ G'oliblar ro'yxati\n\n"
        "📌 Bot holati: 🔴 Nofaol\n"
        "🟢 Boshlash uchun « Yoqish » tugmasini bosing."
    )

# ╔══════════════════════════════════════╗
# ║           🚀 MAIN                   ║
# ╚══════════════════════════════════════╝
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
