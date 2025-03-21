import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# Конфігурація
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_USERNAME = "Office_GPTUA_bot"  # Вкажіть тут ім'я вашого бота

if not BOT_TOKEN or not ADMIN_ID or not CHANNEL_ID:
    raise ValueError("Токен бота, ID адміністратора або ID каналу не встановлено у змінних середовища!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Генерація кнопки для посту
def generate_post_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💌 Написати автору", url=f"https://t.me/{BOT_USERNAME}?start=contact_author")]
    ])

# Прийом повідомлень і автоматичне додавання кнопки
@dp.message(F.content_type.in_({ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT}))
async def handle_news(message: Message):
    if message.content_type == ContentType.PHOTO:
        await bot.send_photo(
            CHANNEL_ID,
            photo=message.photo[-1].file_id,
            caption=message.caption or "Новина без тексту",
            reply_markup=generate_post_keyboard()
        )
    elif message.content_type == ContentType.VIDEO:
        await bot.send_video(
            CHANNEL_ID,
            video=message.video.file_id,
            caption=message.caption or "Новина без тексту",
            reply_markup=generate_post_keyboard()
        )
    elif message.content_type == ContentType.DOCUMENT:
        await bot.send_document(
            CHANNEL_ID,
            document=message.document.file_id,
            caption=message.caption or "Новина без тексту",
            reply_markup=generate_post_keyboard()
        )
    else:
        await bot.send_message(
            CHANNEL_ID,
            text=message.text or "Новина без тексту",
            reply_markup=generate_post_keyboard()
        )

    await message.answer("✅ Ваше повідомлення опубліковано з кнопкою!")

# Головна функція
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Flask сервер для підтримки активності
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    asyncio.run(main())
