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
BOT_USERNAME = "Office_GPTUA_bot"  # Ім'я вашого бота

if not BOT_TOKEN or not ADMIN_ID or not CHANNEL_ID:
    raise ValueError("Токен бота, ID адміністратора або ID каналу не встановлено у змінних середовища!")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")  # Збереження HTML-форматування
dp = Dispatcher()

pending_messages = {}  # Словник для новин, що очікують модерації

# Генерація кнопок модерації
def generate_approve_keyboard(message_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Затвердити", callback_data=f"approve:{message_id}")],
        [InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject:{message_id}")],
        [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit:{message_id}")]
    ])

# Генерація кнопки для посту
def generate_post_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Надіслати Новину", url=f"https://t.me/{BOT_USERNAME}?start=contact_author")]
    ])

# Прийом новин (відправляється на модерацію адміну)
@dp.message(F.content_type.in_({ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT}))
async def handle_news(message: Message):
    pending_messages[message.message_id] = {
        "content_type": message.content_type,
        "file_id": (
            message.photo[-1].file_id if message.photo else
            message.video.file_id if message.video else
            message.document.file_id if message.document else None
        ),
        "caption": message.html_text or message.caption or "Новина без тексту"  # Повне збереження HTML-форматування
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

# Затвердження новини
@dp.callback_query(F.data.startswith("approve"))
async def approve_news(callback: CallbackQuery):
    _, message_id = callback.data.split(":")
    message_data = pending_messages.pop(int(message_id), None)
    
    if not message_data:
        await callback.answer("❌ Новина не знайдена!")
        return

    # Публікація новини у канал із збереженим форматуванням
    if message_data["content_type"] == ContentType.PHOTO:
        await bot.send_photo(
            CHANNEL_ID,
            photo=message_data["file_id"],
            caption=message_data["caption"],
            reply_markup=generate_post_keyboard()
        )
    elif message_data["content_type"] == ContentType.VIDEO:
        await bot.send_video(
            CHANNEL_ID,
            video=message_data["file_id"],
            caption=message_data["caption"],
            reply_markup=generate_post_keyboard()
        )
    elif message_data["content_type"] == ContentType.DOCUMENT:
        await bot.send_document(
            CHANNEL_ID,
            document=message_data["file_id"],
            caption=message_data["caption"],
            reply_markup=generate_post_keyboard()
        )
    else:
        await bot.send_message(
            CHANNEL_ID,
            text=message_data["caption"],
            reply_markup=generate_post_keyboard()
        )
    await bot.send_message(CHANNEL_ID, "💬 Ви можете залишати коментарі до цієї новини!")  # Активізація коментарів

    await callback.answer("✅ Новина опублікована!")

# Відхилення новини
@dp.callback_query(F.data.startswith("reject"))
async def reject_news(callback: CallbackQuery):
    _, message_id = callback.data.split(":")
    if pending_messages.pop(int(message_id), None):
        await callback.message.edit_text("❌ Новина відхилена.")
        await callback.answer("❌ Новина відхилена.")
    else:
        await callback.answer("❌ Новина не знайдена!")

# Редагування новини
@dp.callback_query(F.data.startswith("edit"))
async def edit_news(callback: CallbackQuery):
    _, message_id = callback.data.split(":")
    message_data = pending_messages.get(int(message_id))
    
    if not message_data:
        await callback.answer("❌ Новина не знайдена!")
        return

    await callback.message.answer("✏️ Введіть новий текст для новини (з форматуванням):")

    @dp.message(F.text)
    async def handle_edit_response(new_message: Message):
        message_data["caption"] = new_message.html_text  # Збереження HTML-форматування при редагуванні
        pending_messages[int(message_id)] = message_data
        await new_message.answer("✅ Текст новини оновлено!")
        await bot.send_message(
            ADMIN_ID,
            f"📝 Оновлена новина:\n{message_data['caption']}",
            reply_markup=generate_approve_keyboard(int(message_id))
        )

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
