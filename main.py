from aiogram import Bot
import asyncio

BOT_TOKEN = "ВАШ_ТОКЕН"  # Вставте токен вашого бота
HIDDEN_CHANNEL_ID = -1002570163026  # ID каналу

bot = Bot(token=BOT_TOKEN)

async def test_send():
    try:
        await bot.send_message(chat_id=HIDDEN_CHANNEL_ID, text="Тестове повідомлення")
        print("✅ Повідомлення надіслано успішно!")
    except Exception as e:
        print(f"❌ Помилка: {e}")

asyncio.run(test_send())
