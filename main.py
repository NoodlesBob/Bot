import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ContentType, Message
from aiogram.filters import Command
import logging

# Логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфігурація
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
HIDDEN_CHANNEL_ID = -1002570163026  # ID прихованого каналу

if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("Необхідні змінні середовища не задані!")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Словник для новин
pending_messages = {}

# Генерація кнопок
def generate_keyboard(msg_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("✅ Затвердити", callback_data=f"approve:{msg_id}")],
            [InlineKeyboardButton("❌ Відхилити", callback_data=f"reject:{msg_id}")],
            [InlineKeyboardButton("✏️ Змінити", callback_data=f"edit:{msg_id}")]
        ]
    )

# Привітання
@dp.message(Command("start"))
async def send_welcome(message: Message):
    text = (
        "👋 Вітаємо! Надсилайте текст, фото, відео або документи для модерації.\n"
        "Після затвердження новина буде опублікована. Адміністратор може редагувати чи відхилити новини."
    )
    await message.answer(text)

# Обробка новин
@dp.message(lambda msg: msg.content_type in {ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT})
async def handle_news(message: Message):
    pending_messages[message.message_id] = {
        "type": message.content_type,
        "file_id": (message.photo[-1].file_id if message.photo else
                    message.video.file_id if message.video else
                    message.document.file_id if message.document else None),
        "caption": message.text or message.caption or "📩 Немає тексту"
    }

    await message.answer("✅ Новина надіслана на модерацію!")
    admin_text = f"📝 Новина від @{message.from_user.username or 'анонім'}:\n\n{pending_messages[message.message_id]['caption']}"

    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, pending_messages[message.message_id]['file_id'], admin_text, reply_markup=generate_keyboard(message.message_id))
        elif message.video:
            await bot.send_video(ADMIN_ID, pending_messages[message.message_id]['file_id'], admin_text, reply_markup=generate_keyboard(message.message_id))
        elif message.document:
            await bot.send_document(ADMIN_ID, pending_messages[message.message_id]['file_id'], admin_text, reply_markup=generate_keyboard(message.message_id))
        else:
            await bot.send_message(ADMIN_ID, admin_text, reply_markup=generate_keyboard(message.message_id))
    except Exception as e:
        logger.error(f"Помилка відправлення адміністратору: {e}")

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
            await bot.send_photo(HIDDEN_CHANNEL_ID, news["file_id"], news["caption"], disable_notification=True)
        elif news["type"] == ContentType.VIDEO:
            await bot.send_video(HIDDEN_CHANNEL_ID, news["file_id"], news["caption"], disable_notification=True)
        elif news["type"] == ContentType.DOCUMENT:
            await bot.send_document(HIDDEN_CHANNEL_ID, news["file_id"], news["caption"], disable_notification=True)
        else:
            await bot.send_message(HIDDEN_CHANNEL_ID, news["caption"], disable_notification=True)
        await callback_query.answer("✅ Новина затверджена!")
    except Exception as e:
        logger.error(f"Помилка публікації: {e}")
        await callback_query.answer("❌ Помилка публікації!")

# Відхилення новини
@dp.callback_query(lambda c: c.data.startswith("reject"))
async def reject_news(callback_query: CallbackQuery):
    message_id = int(callback_query.data.split(":")[1])

    if pending_messages.pop(message_id, None):
        await callback_query.answer("❌ Новина відхилена.")
    else:
        await callback_query.answer("❌ Новина не знайдена!")

# Редагування новини
@dp.callback_query(lambda c: c.data.startswith("edit"))
async def edit_news(callback_query: CallbackQuery):
    message_id = int(callback_query.data.split(":")[1])

    if message_id not in pending_messages:
        await callback_query.answer("❌ Новина не знайдена для редагування!")
        return

    await callback_query.message.answer("✏️ Введіть новий текст для цієї новини:")

    @dp.message(lambda msg: msg.text)
    async def save_edit(new_message: Message):
        pending_messages[message_id]["caption"] = new_message.text
        await new_message.answer("✅ Текст новини оновлено!")
        dp.message.middleware_stack.pop()  # Зупиняємо обробник для уникнення конфліктів

# Основна функція
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
