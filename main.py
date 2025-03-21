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
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен бота зберігається у змінній середовища
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ID адміністратора
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID каналу для публікацій
COMMENTS_GROUP_ID = -1002180841211  # ID прив'язаної групи для обговорень

if not BOT_TOKEN or not ADMIN_ID or not CHANNEL_ID or not COMMENTS_GROUP_ID:
    raise ValueError("Необхідні змінні середовища не задані!")

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Словник для новин, що очікують модерації
pending_messages = {}

# Інструкція
INSTRUCTION_TEXT = (
    "👋 Вітаємо в боті ChatGPT Ukraine!"
    "📋 *Як працює бот ChatGPT Ukraine:*\n\n"
    "🔹 Надішліть текст, фото, відео або документ із вашою новиною.\n"
    "🔹 Якщо новина містить посилання, надішліть їх окремо, щоб зберегти правильне форматування.\n"
    "🔹 Адміністратор перегляне вашу новину.\n"
    "🔹 Після затвердження ваша новина буде опублікована в каналі [ChatGPT Ukraine](https://t.me/ChatGPT_in_Ukraine).\n\n"
    "🛠 *Доступні команди:*\n"
    "/start - Почати роботу з ботом\n"
    "/help - Як працює бот"
)

# Кнопки для адміністратора
def generate_approve_keyboard(message_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Затвердити", callback_data=f"approve:{message_id}")],
            [InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject:{message_id}")],
            [InlineKeyboardButton(text="✏️ Змінити", callback_data=f"edit:{message_id}")]
        ]
    )

# Привітання при команді /start
@dp.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer(
        "👋 Вітаємо в боті *ChatGPT Ukraine*! Ознайомтеся з інструкцією нижче та надсилайте свої новини:\n\n"
        + INSTRUCTION_TEXT,
        parse_mode="Markdown"
    )

# Обробка новин від користувачів
@dp.message(lambda message: message.content_type in {ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT})
async def handle_news(message: Message):
    pending_messages[message.message_id] = {
        "media_type": message.content_type,
        "file_id": (
            message.photo[-1].file_id if message.photo else
            message.video.file_id if message.video else
            message.document.file_id if message.document else None
        ),
        "caption": message.text or message.caption or "📩 Повідомлення без тексту"
    }

    await message.answer("✅ Твоя новина надіслана на модерацію.")

    try:
        admin_message = f"📝 Новина від @{message.from_user.username or 'аноніма'}:\n\n{pending_messages[message.message_id]['caption']}"
        if message.photo:
            await bot.send_photo(
                ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        elif message.video:
            await bot.send_video(
                ADMIN_ID,
                video=message.video.file_id,
                caption=admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        elif message.document:
            await bot.send_document(
                ADMIN_ID,
                document=message.document.file_id,
                caption=admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        else:
            await bot.send_message(
                ADMIN_ID,
                admin_message,
                reply_markup=generate_approve_keyboard(message.message_id)
            )
    except Exception as e:
        logger.error(f"Помилка при відправленні новини адміністратору: {e}")

# Затвердження новини
@dp.callback_query(lambda c: c.data and c.data.startswith("approve"))
async def approve_news(callback_query: CallbackQuery):
    message_id = int(callback_query.data.split(":")[1])
    if message_id not in pending_messages:
        await callback_query.answer("❌ Новина не знайдена!")
        return

    message_data = pending_messages.pop(message_id)
    try:
        if message_data["media_type"] == ContentType.PHOTO:
            await bot.send_photo(
                CHANNEL_ID,
                photo=message_data["file_id"],
                caption=message_data["caption"]
            )
        elif message_data["media_type"] == ContentType.VIDEO:
            await bot.send_video(
                CHANNEL_ID,
                video=message_data["file_id"],
                caption=message_data["caption"]
            )
        elif message_data["media_type"] == ContentType.DOCUMENT:
            await bot.send_document(
                CHANNEL_ID,
                document=message_data["file_id"],
                caption=message_data["caption"]
            )
        else:
            await bot.send_message(
                CHANNEL_ID,
                text=message_data["caption"]
            )
        await callback_query.answer("✅ Новина опублікована!")
    except Exception as e:
        logger.error(f"Помилка при публікації новини: {e}")
        await callback_query.answer("❌ Помилка публікації.")

# Відхилення новини
@dp.callback_query(lambda c: c.data and c.data.startswith("reject"))
async def reject_news(callback_query: CallbackQuery):
    message_id = int(callback_query.data.split(":")[1])
    if pending_messages.pop(message_id, None):
        await callback_query.answer("❌ Новина відхилена.")
    else:
        await callback_query.answer("❌ Повідомлення не знайдено.")

# Головна функція
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
