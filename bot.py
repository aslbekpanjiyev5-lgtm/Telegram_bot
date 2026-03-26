import asyncio
import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

participants = set()

CHANNEL = "@starflow_premium"

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

# MENU
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎁 Tanlovga qo‘shilish")],
        [KeyboardButton(text="🏆 G‘olibni aniqlash")]
    ],
    resize_keyboard=True
)

# START
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "⭐ StarFlow Giveaway botga xush kelibsiz!",
        reply_markup=menu
    )

# JOIN
@dp.message(lambda message: message.text == "🎁 Tanlovga qo‘shilish")
async def join(message: types.Message):
    user_id = message.from_user.id

    if not await check_sub(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Obuna bo‘lish", url="https://t.me/starflow_premium")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        ])
        await message.answer("❌ Avval kanalga obuna bo‘ling:", reply_markup=kb)
        return

    if user_id not in participants:
        participants.add(user_id)
        await message.answer("Siz tanlovga qo‘shildingiz ✅")
    else:
        await message.answer("Siz allaqachon qo‘shilgansiz 😄")

# WINNER
@dp.message(lambda message: message.text == "🏆 G‘olibni aniqlash")
async def winner(message: types.Message):
    if participants:
        win = random.choice(list(participants))
        await message.answer(f"🏆 G‘olib ID: {win}")
    else:
        await message.answer("Ishtirokchilar yo‘q ❌")

# CHECK BUTTON
@dp.callback_query(lambda c: c.data == "check_sub")
async def check_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await check_sub(user_id):
        if user_id not in participants:
            participants.add(user_id)
        await callback.message.answer("Siz tanlovga qo‘shildingiz ✅")
    else:
        await callback.message.answer("❌ Hali obuna bo‘lmadingiz!")

# MAIN
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())