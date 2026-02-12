import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timedelta
import pytz

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from aiogram.enums import ChatType

# =========================
# TOKEN
# =========================
TOKEN = "8235364340:AAGQG0mwJqaaI5sAUoRpfnP_JLZ1zLBSdZI"

# =========================
# TIMEZONE (مكة)
# =========================
MECCA = pytz.timezone("Asia/Riyadh")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================
# DATABASE
# =========================
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
links INTEGER DEFAULT 0,
closed INTEGER DEFAULT 0
)
""")

conn.commit()

# =========================
# لوحة تحكم المشرف
# =========================
def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔓 فتح الروابط", callback_data="enable_links"),
                InlineKeyboardButton(text="🔒 قفل الروابط", callback_data="disable_links")
            ],
            [
                InlineKeyboardButton(text="🧹 تصفير التحذيرات", callback_data="reset")
            ]
        ]
    )

# =========================
# تحقق مشرف
# =========================
async def is_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

# =========================
# تحقق وقت الإغلاق
# =========================
def is_closed_time():
    now = datetime.now(MECCA)
    hour = now.hour
    return hour >= 23 or hour < 7

# =========================
# إغلاق القروب
# =========================
async def close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(chat_id,
        "🔴 القروب مغلق الآن\n⏰ من 11 مساءً إلى 7 صباحاً\nبتوقيت مكة المكرمة"
    )

# =========================
# فتح القروب
# =========================
async def open_group(chat_id):
    await bot.set_chat_permissions(chat_id,
        ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
    )
    await bot.send_message(chat_id, "🟢 تم فتح القروب\nمرحباً بكم 🌿")

# =========================
# Scheduler لإغلاق وفتح القروب تلقائياً
# =========================
async def scheduler():
    while True:
        cursor.execute("SELECT chat_id, closed FROM settings")
        rows = cursor.fetchall()
        for chat_id, closed in rows:
            if is_closed_time() and closed == 0:
                await close_group(chat_id)
                cursor.execute("UPDATE settings SET closed=1 WHERE chat_id=?", (chat_id,))
                conn.commit()
            elif not is_closed_time() and closed == 1:
                await open_group(chat_id)
                cursor.execute("UPDATE settings SET closed=0 WHERE chat_id=?", (chat_id,))
                conn.commit()
        await asyncio.sleep(60)

# =========================
# اكتشاف الروابط
# =========================
def has_link(text):
    if not text:
        return False
    pattern = r"(https?://|www\.|t\.me)"
    return re.search(pattern, text.lower())

# =========================
# التحذيرات
# =========================
def get_warnings(chat_id, user_id):
    cursor.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    result = cursor.fetchone()
    return result[0] if result else 0

def add_warning(chat_id, user_id):
    count = get_warnings(chat_id, user_id) + 1
    cursor.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    cursor.execute("INSERT INTO warnings VALUES (?, ?, ?)", (chat_id, user_id, count))
    conn.commit()
    return count

# =========================
# START (خاص فقط)
# =========================
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.chat.type == ChatType.PRIVATE:
        text = (
            "🤖 بوت Eduai-sa نماذج Ai التعليمية\n\n"
            "الموقع الالكتروني\nhttps://eduai-sa.com\n\n"
            "قناة نماذج Ai التعليمية\nhttps://t.me/eduai_ksa\n\n"
            "قروب ( نماذج Ai التعليمية ) 💬\nhttps://t.me/eduai_ksa1\n\n"
            "برمجة الاستاذ عبدالله البلوي"
        )
        await message.answer(text)

# =========================
# PANEL (للمشرف والمالك فقط)
# =========================
@dp.message(Command("panel"))
async def panel(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    cursor.execute("INSERT OR IGNORE INTO settings(chat_id, links, closed) VALUES (?,0,0)", (chat_id,))
    conn.commit()

    if await is_admin(chat_id, user_id):
        await message.reply("🔧 لوحة تحكم المشرف:", reply_markup=admin_keyboard())
    # العضو العادي لا يحصل على شيء إطلاقاً

# =========================
# ترحيب
# =========================
@dp.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        await message.reply(f"👋 مرحباً {user.first_name}")

# =========================
# الحماية
# =========================
@dp.message(F.text)
async def security(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if await is_admin(chat_id, user_id):
        return

    # وقت الإغلاق
    if is_closed_time():
        await message.delete()
        return

    # منع الروابط
    if has_link(message.text):
        await message.delete()
        count = add_warning(chat_id, user_id)
        if count >= 3:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=datetime.now(MECCA) + timedelta(minutes=10)
            )
            await message.answer("🔇 تم كتم العضو 10 دقائق")
        else:
            await message.answer(f"⚠️ تحذير {count}/3")

# =========================
# Callbacks لوحة التحكم
# =========================
@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if not await is_admin(chat_id, user_id):
        await call.answer("❌ للمشرفين فقط", show_alert=True)
        return

    if call.data == "enable_links":
        cursor.execute("UPDATE settings SET links=1 WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.message.answer("✅ تم فتح الروابط")
    elif call.data == "disable_links":
        cursor.execute("UPDATE settings SET links=0 WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.message.answer("🔒 تم قفل الروابط")
    elif call.data == "reset":
        cursor.execute("DELETE FROM warnings WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.message.answer("🧹 تم تصفير التحذيرات")

# =========================
# MAIN
# =========================
async def main():
    print("🔥 Eduai-sa Institutional Bot Running")
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
