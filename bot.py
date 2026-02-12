import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions
)
from aiogram.enums import ChatType

# =============================
# TOKEN
# =============================
TOKEN = "8235364340:AAGQG0mwJqaaI5sAUoRpfnP_JLZ1zLBSdZI"

# =============================
# Logging
# =============================
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =============================
# Database
# =============================
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    chat_id INTEGER,
    user_id INTEGER,
    count INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    chat_id INTEGER PRIMARY KEY,
    links INTEGER DEFAULT 0
)
""")

conn.commit()

# =============================
# Keyboard
# =============================
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔓 فتح الروابط", callback_data="enable_links"),
            InlineKeyboardButton(text="🔒 قفل الروابط", callback_data="disable_links")
        ],
        [
            InlineKeyboardButton(text="🧹 تصفير التحذيرات", callback_data="reset")
        ]
    ])

# =============================
# Admin check
# =============================
async def is_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

# =============================
# Link detection
# =============================
def has_link(text):
    if not text:
        return False
    pattern = r"(https?://|www\.|t\.me)"
    return re.search(pattern, text.lower())

# =============================
# Get warnings
# =============================
def get_warnings(chat_id, user_id):

    cursor.execute(
        "SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )

    result = cursor.fetchone()

    return result[0] if result else 0


# =============================
# Add warning
# =============================
def add_warning(chat_id, user_id):

    count = get_warnings(chat_id, user_id) + 1

    cursor.execute(
        "DELETE FROM warnings WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )

    cursor.execute(
        "INSERT INTO warnings VALUES (?, ?, ?)",
        (chat_id, user_id, count)
    )

    conn.commit()

    return count


# =============================
# Reset warnings
# =============================
def reset_warnings(chat_id):

    cursor.execute(
        "DELETE FROM warnings WHERE chat_id=?",
        (chat_id,)
    )

    conn.commit()


# =============================
# Link setting
# =============================
def links_allowed(chat_id):

    cursor.execute(
        "SELECT links FROM settings WHERE chat_id=?",
        (chat_id,)
    )

    result = cursor.fetchone()

    return result and result[0] == 1


def set_links(chat_id, value):

    cursor.execute(
        "DELETE FROM settings WHERE chat_id=?",
        (chat_id,)
    )

    cursor.execute(
        "INSERT INTO settings VALUES (?, ?)",
        (chat_id, value)
    )

    conn.commit()

# =============================
# Start
# =============================
@dp.message(Command("start"))
async def start(message: types.Message):

    if message.chat.type == ChatType.PRIVATE:

        await message.answer(
            "🤖 بوت Eduaisa الاحترافي\n\n"
            "أضفني للقروب وارفعني مشرف للحماية."
        )

    else:

        await message.reply(
            "✅ تم تفعيل الحماية بنجاح",
            reply_markup=admin_keyboard()
        )

# =============================
# Welcome
# =============================
@dp.message(F.new_chat_members)
async def welcome(message: types.Message):

    for user in message.new_chat_members:

        await message.reply(
            f"👋 مرحباً {user.first_name}\n"
            f"📚 مرحباً بك في القروب"
        )

# =============================
# Block links
# =============================
@dp.message(F.text)
async def security(message: types.Message):

    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if await is_admin(chat_id, user_id):
        return

    if links_allowed(chat_id):
        return

    if has_link(message.text):

        await message.delete()

        count = add_warning(chat_id, user_id)

        if count == 1:

            await message.answer(
                f"⚠️ تحذير 1/3"
            )

        elif count == 2:

            await message.answer(
                f"⚠️ تحذير 2/3\n"
                f"سيتم كتمك عند المخالفة القادمة"
            )

        elif count >= 3:

            until = datetime.now() + timedelta(minutes=10)

            await bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=until
            )

            await message.answer(
                f"🔇 تم كتم العضو 10 دقائق"
            )

# =============================
# Callbacks
# =============================
@dp.callback_query()
async def callbacks(call: types.CallbackQuery):

    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if not await is_admin(chat_id, user_id):

        await call.answer("❌ للمشرفين فقط", show_alert=True)
        return

    if call.data == "enable_links":

        set_links(chat_id, 1)

        await call.message.answer("✅ تم فتح الروابط")

    elif call.data == "disable_links":

        set_links(chat_id, 0)

        await call.message.answer("🔒 تم قفل الروابط")

    elif call.data == "reset":

        reset_warnings(chat_id)

        await call.message.answer("🧹 تم تصفير التحذيرات")

# =============================
# Kick command
# =============================
@dp.message(Command("طرد"))
async def kick(message: types.Message):

    if not await is_admin(message.chat.id, message.from_user.id):
        return

    if message.reply_to_message:

        user_id = message.reply_to_message.from_user.id

        await bot.ban_chat_member(
            message.chat.id,
            user_id
        )

        await message.reply("🚫 تم الطرد")

# =============================
# Run
# =============================
async def main():

    print("🔥 Professional Bot Running")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
