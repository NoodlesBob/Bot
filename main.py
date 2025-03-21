import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties
import os

# Логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфігурація
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен вашого бота
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ID адміністратора
HIDDEN_CHANNEL_ID = int(os.getenv("HIDDEN_CHANNEL_ID"))  # ID прихованого каналу

if not BOT_TOKEN or not ADMIN_ID or not HIDDEN_CHANNEL_ID:
    raise ValueError("BOT_TOKEN, ADMIN_ID або HIDDEN_CHANNEL_ID не встановлено у змінних середовища!")

# Ініціалізація бота
bot = Bot(
    token=BOT_TOKEN,
    session=AiohttpSession(),
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# Список для зберігання новин, які очікують модерації
pending_messages = {}

# Інструкція
INSTRUCTION_TEXT = (
    "📋 *Інструкція з використання бота:*\n\n"
    "1️⃣ Надішліть текст, фото, відео або документ.\n"
    "2️⃣ Адміністратор розгляне вашу новину.\n"
    "3️⃣ Після затвердження ваша новина буде опублікована у прихованому каналі.\n\n"
    "🔒 *Анонімність:*\n"
    "Повідомлення є анонімними. Якщо ви хочете бути публічно згаданими, вкажіть це у тексті повідомлення.\n\n"
    "🛠 *Основні команди:*\n"
    "/start - Перезапустити бота\n"
    "/help - Опис функцій бота\n"
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
        "👋 Вітаємо в боті! Ознайомтеся з інструкцією нижче та надішліть свою новину.\n\n"
        + INSTRUCTION_TEXT,
        parse_mode="Markdown"
    )

# Обробка новин від користувачів
@dp.message(F.content_type.in_({ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT}))
async def handle_news(message: Message):
    global pending_messages
    pending_messages[message.message_id] = {
        "message": message,
        "media_type": message.content_type,
        "file_id": (
            message.photo[-1].file_id if message.photo else
            message.video.file_id if message.video else
            message.document.file_id if message.document else None
        ),
        "caption": message.text or message.caption or "📩 Повідомлення без тексту"
    }
    await message.answer("✅ Твоя новина надіслана на модерацію!")

    try:
        admin_message = f"📝 Новина від @{message.from_user.username or 'аноніма'}:\n{pending_messages[message.message_id]['caption']}"
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
        logger.error(f"Помилка при відправці новини адміністратору: {e}")

# Затвердження новини
@dp.callback_query(F.data.startswith("approve"))
async def approve_news(callback: CallbackQuery):
    global pending_messages
    _, message_id = callback.data.split(":")
    message_data = pending_messages.pop(int(message_id), None)

    if message_data:
        try:
            if message_data["media_type"] == ContentType.PHOTO:
                await bot.send_photo(
                    HIDDEN_CHANNEL_ID,
                    photo=message_data["file_id"],
                    caption=message_data["caption"]
                )
            elif message_data["media_type"] == ContentType.VIDEO:
                await bot.send_video(
                    HIDDEN_CHANNEL_ID,
                    video=message_data["file_id"],
                    caption=message_data["caption"]
                )
            elif message_data["media_type"] == ContentType.DOCUMENT:
                await bot.send_document(
                    HIDDEN_CHANNEL_ID,
                    document=message_data["file_id"],
                    caption=message_data["caption"]
                )
            else:
                await bot.send_message(
                    HIDDEN_CHANNEL_ID,
                    text=message_data["caption"]
                )
            await callback.answer("✅ Новину опубліковано!")
        except Exception as e:
            logger.error(f"Помилка публікації новини: {e}")
            await callback.answer(f"❌ Помилка публікації: {e}")
    else:
        await callback.answer("❌ Новина не знайдена або вже оброблена!")

# Відхилення новини
@dp.callback_query(F.data.startswith("reject"))
async def reject_news(callback: CallbackQuery):
    global pending_messages
    _, message_id = callback.data.split(":")
    if pending_messages.pop(int(message_id), None):
        await callback.answer("❌ Новина відхилена.")
        await callback.message.edit_text("❌ Ця новина була відхилена.")
    else:
        await callback.answer("❌ Новина не знайдена або вже оброблена!")

# Головна функція
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
