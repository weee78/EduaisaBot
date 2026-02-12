import asyncio
import re
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

warnings = {}

@dp.message()
async def welcome_handler(message: types.Message):
    if message.new_chat_members:
        for member in message.new_chat_members:
            await message.reply(
                f"👋 مرحباً {member.full_name}\n"
                "أهلاً بك في القروب التعليمي 📚\n"
                "يرجى الالتزام بالقوانين."
            )

@dp.message()
async def anti_link_handler(message: types.Message):
    if message.text:
        url_pattern = r"(https?://|www\.)"
        if re.search(url_pattern, message.text):
            user_id = message.from_user.id
            chat_id = message.chat.id

            await message.delete()

            warnings[user_id] = warnings.get(user_id, 0) + 1

            if warnings[user_id] >= 3:
                await bot.ban_chat_member(chat_id, user_id)
                await bot.send_message(chat_id, f"🚫 تم حظر {message.from_user.full_name} بسبب نشر الروابط.")
            else:
                await bot.send_message(
                    chat_id,
                    f"⚠️ تحذير {message.from_user.full_name}\n"
                    f"عدد التحذيرات: {warnings[user_id]}/3"
                )

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.reply("🤖 البوت يعمل بنجاح!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
