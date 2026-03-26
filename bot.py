import asyncio
import logging
import random
import os
import sqlite3
import time
from datetime import datetime
from functools import wraps

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# 🔐 TOKENLAR
USER_BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

ADMIN_ID = 6019703915

BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-bot-6nns.onrender.com")

USER_WEBHOOK_PATH = "/webhook/user"
ADMIN_WEBHOOK_PATH = "/webhook/admin"

user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_user = Dispatcher()
dp_admin = Dispatcher()

# 💾 DATABASE
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

# 🔧 CONFIG
def set_config(k, v):
    cur.execute("REPLACE INTO config VALUES (?, ?)", (k, v))
    conn.commit()

def get_config(k, d=None):
    cur.execute("SELECT value FROM config WHERE key=?", (k,))
    r = cur.fetchone()
    return r[0] if r else d

if not get_config("active"):       set_config("active", "off")
if not get_config("code"):         set_config("code", "1234")
if not get_config("winner_count"): set_config("winner_count", "3")

# ✅ Admin decorator
def admin_only(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id != ADMIN_ID:
            await message.answer("🚫 Ruxsat yo'q!")
            return
        await func(message, *args, **kwargs)
    return wrapper

# ================= USER BOT =================

@dp_user.message(Command("start"))
async def start_user(message: types.Message):
    if get_config("active") != "on":
        await message.answer("⛔ Giveaway hozircha faol emas.")
        return
    await message.answer(
        "🎁 <b>Giveawayga xush kelibsiz!</b>\n\n"
        "🔑 Kodni yuboring va g'oliblar qatoriga qo'shiling!",
        parse_mode="HTML"
    )

@dp_user.message()
async def join(message: types.Message):
    if get_config("active") != "on":
        return
    if not message.text:
        return
    if message.text != get_config("code"):
        await message.answer("❌ Noto'g'ri kod!")
        return

    user = message.from_user
    game_id = get_config("current_game")

    if not user.username:
        await message.answer("⚠️ Telegram username qo'ying va qaytadan yuboring.")
        return

    cur.execute("SELECT * FROM users WHERE user_id=? AND game_id=?", (user.id, game_id))
    if cur.fetchone():
        await message.answer("ℹ️ Siz allaqachon qatnashyapsiz!")
        return

    cur.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                (user.id, user.username, game_id,
                 datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

    await message.answer("✅ Muvaffaqiyatli qo'shildingiz! Omad tilaymiz 🍀")

    cur.execute("SELECT COUNT(*) FROM users WHERE game_id=?", (game_id,))
    count = cur.fetchone()[0]

    try:
        await admin_bot.send_message(
            ADMIN_ID,
            f"➕ <b>Yangi ishtirokchi:</b> @{user.username}\n📊 Jami: {count} ta",
            parse_mode="HTML"
        )
    except:
        pass

# ================= ADMIN BOT =================

@dp_admin.message(Command("start"))
@admin_only
async def admin_panel(message: types.Message):
    status = "🟢 Faol" if get_config("active") == "on" else "🔴 To'xtagan"
    await message.answer(
        f"👑 <b>ADMIN PANEL</b>\n\n"
        f"📌 Holat: {status}\n"
        f"🔑 Kod: <code>{get_config('code')}</code>\n"
        f"🏆 G'oliblar soni: {get_config('winner_count')}\n\n"
        f"🟢 /on — yangi o'yin boshlash\n"
        f"🔴 /off — o'yinni to'xtatish\n"
        f"📊 /stat — statistika\n"
        f"👥 /users — ishtirokchilar\n"
        f"🔑 /setcode 1234 — kod\n"
        f"🏆 /setwinner 3 — g'oliblar soni\n"
        f"🎯 /winner — g'oliblarni aniqlash\n"
        f"🧹 /clear — ro'yxatni tozalash",
        parse_mode="HTML"
    )

@dp_admin.message(Command("on"))
@admin_only
async def on_game(message: types.Message):
    game_id = str(int(time.time()))
    set_config("current_game", game_id)
    set_config("active", "on")
    await message.answer(
        f"🟢 <b>Yangi Giveaway boshlandi!</b>\n"
        f"🎮 Game ID: <code>{game_id}</code>\n"
        f"🔑 Kod: <code>{get_config('code')}</code>",
        parse_mode="HTML"
    )

@dp_admin.message(Command("off"))
@admin_only
async def off_game(message: types.Message):
    set_config("active", "off")
    game_id = get_config("current_game")
    cur.execute("SELECT COUNT(*) FROM users WHERE game_id=?", (game_id,))
    count = cur.fetchone()[0]
    await message.answer(
        f"🔴 <b>Giveaway to'xtatildi!</b>\n"
        f"📊 Jami ishtirokchilar: {count} ta",
        parse_mode="HTML"
    )

@dp_admin.message(Command("stat"))
@admin_only
async def stat(message: types.Message):
    game_id = get_config("current_game")
    cur.execute("SELECT COUNT(*) FROM users WHERE game_id=?", (game_id,))
    count = cur.fetchone()[0]
    status = "🟢 Faol" if get_config("active") == "on" else "🔴 To'xtagan"
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"📌 Holat: {status}\n"
        f"👥 Ishtirokchilar: {count} ta\n"
        f"🔑 Kod: <code>{get_config('code')}</code>\n"
        f"🏆 G'oliblar soni: {get_config('winner_count')}",
        parse_mode="HTML"
    )

@dp_admin.message(Command("users"))
@admin_only
async def users_list(message: types.Message):
    game_id = get_config("current_game")
    cur.execute(
        "SELECT username, joined_at FROM users WHERE game_id=? ORDER BY joined_at",
        (game_id,)
    )
    data = cur.fetchall()
    if not data:
        await message.answer("📭 Hali ishtirokchi yo'q.")
        return
    text = f"👥 <b>Ishtirokchilar ({len(data)} ta):</b>\n\n"
    for i, (uname, jtime) in enumerate(data[:50], 1):
        text += f"{i}. @{uname} — {jtime}\n"
    if len(data) > 50:
        text += f"\n... va yana {len(data) - 50} ta"
    await message.answer(text, parse_mode="HTML")

@dp_admin.message(Command("setcode"))
@admin_only
async def setcode(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❗ /setcode 1234")
        return
    set_config("code", parts[1])
    await message.answer(f"🔑 Yangi kod: <code>{parts[1]}</code>", parse_mode="HTML")

@dp_admin.message(Command("setwinner"))
@admin_only
async def setwinner(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❗ /setwinner 3")
        return
    try:
        count = int(parts[1])
        if count < 1:
            raise ValueError
        set_config("winner_count", str(count))
        await message.answer(f"🏆 G'oliblar soni: {count} ta")
    except:
        await message.answer("❗ To'g'ri son kiriting!")

@dp_admin.message(Command("winner"))
@admin_only
async def winner(message: types.Message):
    game_id = get_config("current_game")
    cur.execute("SELECT user_id, username FROM users WHERE game_id=?", (game_id,))
    all_users = cur.fetchall()
    count = int(get_config("winner_count", "3"))

    if len(all_users) < count:
        await message.answer(
            f"⚠️ Kamida {count} ta ishtirokchi kerak.\nHozir: {len(all_users)} ta"
        )
        return

    winners = random.sample(all_users, count)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 20

    text = "🏆 <b>G'oliblar:</b>\n\n"
    for i, (uid, uname) in enumerate(winners):
        text += f"{medals[i]} @{uname}\n"
    await message.answer(text, parse_mode="HTML")

    for uid, uname in winners:
        try:
            await user_bot.send_message(
                uid,
                "🎉 <b>Tabriklaymiz!</b>\n\n"
                "🏆 Siz Giveawayda <b>G'OLIB</b> bo'ldingiz!\n\n"
                "📩 Tez orada admin siz bilan bog'lanadi.\n"
                "💫 Omadingiz doim kulib tursin!",
                parse_mode="HTML"
            )
        except:
            await message.answer(f"⚠️ @{uname} ga xabar yuborilmadi")

@dp_admin.message(Command("clear"))
@admin_only
async def clear(message: types.Message):
    game_id = get_config("current_game")
    cur.execute("DELETE FROM users WHERE game_id=?", (game_id,))
    conn.commit()
    await message.answer("🧹 Ro'yxat tozalandi.")

# ================= MAIN (WEBHOOK) =================

async def on_startup(app):
    await user_bot.set_webhook(f"{BASE_URL}{USER_WEBHOOK_PATH}")
    await admin_bot.set_webhook(f"{BASE_URL}{ADMIN_WEBHOOK_PATH}")
    logging.info("Webhooks o'rnatildi!")

async def on_shutdown(app):
    await user_bot.delete_webhook()
    await admin_bot.delete_webhook()

def main():
    logging.basicConfig(level=logging.INFO)

    app = web.Application()

    SimpleRequestHandler(dispatcher=dp_user, bot=user_bot).register(app, path=USER_WEBHOOK_PATH)
    SimpleRequestHandler(dispatcher=dp_admin, bot=admin_bot).register(app, path=ADMIN_WEBHOOK_PATH)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    setup_application(app, dp_user, bot=user_bot)

    PORT = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
