import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ContentType
import logging

# Логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфігурація
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен вашого бота
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ID адміністратора
HIDDEN_CHANNEL_ID = -1002570163026  # ID каналу для публікацій

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Новини на модерацію
pending_messages = {}

# Генерація кнопок
def generate_keyboard(msg_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("✅ Затвердити", callback_data=f"approve:{msg_id}")],
            [InlineKeyboardButton("❌ Відхилити", callback_data=f"reject:{msg_id}")]
        ]
    )

# Привітання
@dp.message(commands=["start"])
async def send_welcome(message: Message):
    await message.answer("👋 Вітаємо! Надсилайте текст, фото, відео чи документи для модерації.")

# Обробка новин
@dp.message(lambda msg: msg.content_type in {ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT})
async def handle_news(message: Message):
    pending_messages[message.message_id] = {
        "type": message.content_type,
        "file_id": (
            message.photo[-1].file_id if message.photo else
            message.video.file_id if message.video else
            message.document.file_id if message.document else None
        ),
        "caption": message.caption or message.text or "📩 Немає тексту"
    }
    admin_message = f"📝 Новина від @{message.from_user.username or 'анонім'}:\n\n{pending_messages[message.message_id]['caption']}"
    await message.answer("✅ Новина надіслана на модерацію!")
    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_message, reply_markup=generate_keyboard(message.message_id))
    elif message.video:
        await bot.send_video(ADMIN_ID, message.video.file_id, caption=admin_message, reply_markup=generate_keyboard(message.message_id))
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=admin_message, reply_markup=generate_keyboard(message.message_id))
    else:
        await bot.send_message(ADMIN_ID, admin_message, reply_markup=generate_keyboard(message.message_id))

# Затвердження новини
@dp.callback_query(lambda c: c.data.startswith("approve"))
async def approve_news(callback_query: CallbackQuery):
    message_id = int(callback_query.data.split(":")[1])
    if message_id not in pending_messages:
        await callback_query.answer("❌ Новина не знайдена!")
        return
    news = pending_messages.pop(message_id)
    try:
        if news["type"] == ContentType.PHOTO:
            await bot.send_photo(HIDDEN_CHANNEL_ID, news["file_id"], news["caption"])
        elif news["type"] == ContentType.VIDEO:
            await bot.send_video(HIDDEN_CHANNEL_ID, news["file_id"], news["caption"])
        elif news["type"] == ContentType.DOCUMENT:
            await bot.send_document(HIDDEN_CHANNEL_ID, news["file_id"], news["caption"])
        else:
            await bot.send_message(HIDDEN_CHANNEL_ID, news["caption"])
        await callback_query.answer("✅ Новина затверджена!")
    except Exception as e:
        logger.error(f"Помилка при публікації: {e}")
        await callback_query.answer("❌ Помилка при публікації!")

# Відхилення новини
@dp.callback_query(lambda c: c.data.startswith("reject"))
async def reject_news(callback_query: CallbackQuery):
    message_id = int(callback_query.data.split(":")[1])
    if message_id in pending_messages:
        pending_messages.pop(message_id)
        await callback_query.answer("❌ Новина відхилена.")
    else:
        await callback_query.answer("❌ Новина не знайдена!")

# Головна функція
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
