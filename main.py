import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from flask import Flask
from threading import Thread

# Конфігурація
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
COMMENTS_GROUP_ID = os.getenv("1002180841211")  # ID групи, прив'язаної до каналу
BOT_USERNAME = "Office_GPTUA_bot"

if not BOT_TOKEN or not ADMIN_ID or not CHANNEL_ID or not COMMENTS_GROUP_ID:
    raise ValueError("Токен бота, ID адміністратора, ID каналу або ID групи не встановлено!")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")  # HTML-форматування
dp = Dispatcher()

pending_messages = {}

def generate_approve_keyboard(message_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Затвердити", callback_data=f"approve:{message_id}")],
        [InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject:{message_id}")],
        [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit:{message_id}")]
    ])

@dp.message(F.content_type.in_({ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT}))
async def handle_news(message: Message):
    pending_messages[message.message_id] = {
        "content_type": message.content_type,
        "file_id": (
            message.photo[-1].file_id if message.photo else
            message.video.file_id if message.video else
            message.document.file_id if message.document else None
        ),
        "caption": message.html_text or message.caption or "Новина без тексту"
    }
    await message.answer("✅ Ваше повідомлення надіслано на модерацію!")
    admin_text = f"📝 <b>Новина від @{message.from_user.username or 'аноніма'}:</b>\n{pending_messages[message.message_id]['caption']}"

    if message.content_type == ContentType.PHOTO:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_text, reply_markup=generate_approve_keyboard(message.message_id))
    elif message.content_type == ContentType.VIDEO:
        await bot.send_video(ADMIN_ID, message.video.file_id, caption=admin_text, reply_markup=generate_approve_keyboard(message.message_id))
    elif message.content_type == ContentType.DOCUMENT:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=admin_text, reply_markup=generate_approve_keyboard(message.message_id))
    else:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=generate_approve_keyboard(message.message_id))

@dp.callback_query(F.data.startswith("approve"))
async def approve_news(callback: CallbackQuery):
    _, message_id = callback.data.split(":")
    message_data = pending_messages.pop(int(message_id), None)
    
    if not message_data:
        await callback.answer("❌ Новина не знайдена!")
        return

    sent_message = None
    if message_data["content_type"] == ContentType.PHOTO:
        sent_message = await bot.send_photo(CHANNEL_ID, photo=message_data["file_id"], caption=message_data["caption"])
    elif message_data["content_type"] == ContentType.VIDEO:
        sent_message = await bot.send_video(CHANNEL_ID, video=message_data["file_id"], caption=message_data["caption"])
    elif message_data["content_type"] == ContentType.DOCUMENT:
        sent_message = await bot.send_document(CHANNEL_ID, document=message_data["file_id"], caption=message_data["caption"])
    else:
        sent_message = await bot.send_message(CHANNEL_ID, text=message_data["caption"])

    if sent_message:
        await bot.send_message(CHANNEL_ID, "💬 Ви можете залишати коментарі до цієї новини!", message_thread_id=sent_message.message_id)
    
    await callback.answer("✅ Новина опублікована!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    asyncio.run(main())
