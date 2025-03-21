import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import logging

# Логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфігурація
BOT_TOKEN = "7757705270:AAFy_wrryE6_ERVtAt_iBk01IZ_hfvGSzQI"
ADMIN_ID = 403857343  # Ваш ID
CHANNEL_ID = "@ChatGPT_in_Ukraine"

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список для зберігання новин, які очікують модерації
pending_messages = {}

# Інструкція
INSTRUCTION_TEXT = (
    "📋 *Інструкція з використання бота:*\n\n"
    "1️⃣ Надішліть текст, фото, відео або документ.\n"
    "2️⃣ Адміністратор розгляне вашу новину.\n"
    "3️⃣ Після затвердження ваша новина буде опублікована в каналі.\n\n"
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

# Кнопка для каналу
def generate_publish_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Надіслати Новину", url="https://t.me/Office_GPTUA_bot")]  # Посилання на бота
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
    # Зберігаємо повідомлення для модерації
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

    await message.answer("✅ Твоя новина надіслана на модерацію.")

    try:
        if message.text:
            admin_message = f"📝 Новина від @{message.from_user.username or 'аноніма'}:\n{message.text}"
            await bot.send_message(ADMIN_ID, admin_message, reply_markup=generate_approve_keyboard(message.message_id))
        elif message.photo:
            await bot.send_photo(
                ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=pending_messages[message.message_id]['caption'],
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        elif message.video:
            await bot.send_video(
                ADMIN_ID,
                video=message.video.file_id,
                caption=pending_messages[message.message_id]['caption'],
                reply_markup=generate_approve_keyboard(message.message_id)
            )
        elif message.document:
            await bot.send_document(
                ADMIN_ID,
                document=message.document.file_id,
                caption=pending_messages[message.message_id]['caption'],
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
                    CHANNEL_ID,
                    photo=message_data["file_id"],
                    caption=message_data["caption"],
                    reply_markup=generate_publish_keyboard()
                )
            elif message_data["media_type"] == ContentType.VIDEO:
                await bot.send_video(
                    CHANNEL_ID,
                    video=message_data["file_id"],
                    caption=message_data["caption"],
                    reply_markup=generate_publish_keyboard()
                )
            elif message_data["media_type"] == ContentType.DOCUMENT:
                await bot.send_document(
                    CHANNEL_ID,
                    document=message_data["file_id"],
                    caption=message_data["caption"],
                    reply_markup=generate_publish_keyboard()
                )
            else:
                await bot.send_message(
                    CHANNEL_ID,
                    text=message_data["caption"],
                    reply_markup=generate_publish_keyboard()
                )
            await callback.answer("✅ Новину опубліковано!")
        except Exception as e:
            logger.error(f"Помилка публікації новини: {e}")
            await callback.answer(f"❌ Помилка публікації: {e}")
    else:
        await callback.answer("❌ Повідомлення не знайдено або вже оброблено.")

# Редагування новини
@dp.callback_query(F.data.startswith("edit"))
async def edit_news(callback: CallbackQuery):
    global pending_messages
    _, message_id = callback.data.split(":")
    message_data = pending_messages.get(int(message_id))

    if message_data:
        await callback.message.answer("✏️ Введіть новий текст для новини. Якщо хочете залишити зображення, просто змініть текст.")

        @dp.message(F.text)
        async def process_edit_response(new_message: Message):
            updated_text = new_message.text  # Оновлюємо текст
            message_data["caption"] = updated_text

            try:
                if message_data["media_type"] == ContentType.PHOTO:
                    await bot.send_photo(
                        ADMIN_ID,
                        photo=message_data["file_id"],
                        caption=updated_text,
                        reply_markup=generate_approve_keyboard(int(message_id))
                    )
                elif message_data["media_type"] == ContentType.VIDEO:
                    await bot.send_video(
                        ADMIN_ID,
                        video=message_data["file_id"],
                        caption=updated_text,
                        reply_markup=generate_approve_keyboard(int(message_id))
                    )
                elif message_data["media_type"] == ContentType.DOCUMENT:
                    await bot.send_document(
                        ADMIN_ID,
                        document=message_data["file_id"],
                        caption=updated_text,
                        reply_markup=generate_approve_keyboard(int(message_id))
                    )
                else:
                    await bot.send_message(
                        ADMIN_ID,
                        text=updated_text,
                        reply_markup=generate_approve_keyboard(int(message_id))
                    )
                await new_message.answer("✅ Текст успішно оновлено.")
            except Exception as e:
                logger.error(f"Помилка при редагуванні новини: {e}")
                await new_message.answer("❌ Сталася помилка при оновленні тексту.")
    else:
        await callback.answer("❌ Повідомлення не знайдено для редагування.")

# Відхилення новини
@dp.callback_query(F.data.startswith("reject"))
async def reject_news(callback: CallbackQuery):
    global pending_messages
    _, message_id = callback.data.split(":")
    if pending_messages.pop(int(message_id), None):
        await callback.answer("❌ Новина відхилена.")
    else:
        await callback.answer("❌ Повідомлення не знайдено або вже оброблено.")

# Головна функція
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
