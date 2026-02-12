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

# =============================
# TOKEN
# =============================
TOKEN = "8235364340:AAGQG0mwJqaaI5sAUoRpfnP_JLZ1zLBSdZI"

# =============================
# TIMEZONE
# =============================
MECCA = pytz.timezone("Asia/Riyadh")

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
links INTEGER DEFAULT 0,
closed INTEGER DEFAULT 0
)
""")

conn.commit()

# =============================
# لوحة تحكم المشرف
# =============================
def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("🔓 فتح الرسائل للجميع", callback_data="open_messages"),
                InlineKeyboardButton("🔒 قفل الرسائل للجميع", callback_data="close_messages")
            ],
            [
                InlineKeyboardButton("🔓 فتح الروابط", callback_data="enable_links"),
                InlineKeyboardButton("🔒 قفل الروابط", callback_data="disable_links")
            ],
            [
                InlineKeyboardButton("🧹 تصفير التحذيرات", callback_data="reset")
            ],
            [
                InlineKeyboardButton("🔇 كتم عضو", callback_data="mute_user")
            ]
        ]
    )

# =============================
# التحقق من المشرف
# =============================
async def is_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

# =============================
# التوقيت المغلق للقروب
# =============================
def is_closed_time():
    now = datetime.now(MECCA)
    hour = now.hour
    return hour >= 23 or hour < 7

# =============================
# فتح / قفل القروب
# =============================
async def close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(chat_id, "🔴 القروب مغلق الآن ⏰ من 11 مساءً إلى 7 صباحاً")

async def open_group(chat_id):
    await bot.set_chat_permissions(
        chat_id,
        ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
    )
    await bot.send_message(chat_id, "🟢 تم فتح القروب، مرحباً بكم 🌿")

# =============================
# المجدول
# =============================
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

# =============================
# كشف الروابط
# =============================
def has_link(text):
    if not text: return False
    pattern = r"(https?://|www\.|t\.me)"
    return re.search(pattern, text.lower())

# =============================
# التحذيرات
# =============================
def get_warnings(chat_id, user_id):
    cursor.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    r = cursor.fetchone()
    return r[0] if r else 0

def add_warning(chat_id, user_id):
    count = get_warnings(chat_id, user_id) + 1
    cursor.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    cursor.execute("INSERT INTO warnings VALUES (?, ?, ?)", (chat_id, user_id, count))
    conn.commit()
    return count

# =============================
# أمر /start
# =============================
@dp.message(Command("start"))
async def start(message: types.Message):
    text = (
        "🤖 بوت Eduai-sa نماذج Ai التعليمية\n\n"
        "الموقع الالكتروني\nhttps://eduai-sa.com\n\n"
        "قناة نماذج Ai التعليمية\nhttps://t.me/eduai_ksa\n\n"
        "قروب (نماذج Ai التعليمية) 💬\nhttps://t.me/eduai_ksa1\n\n"
        "أضفني للقروب وارفعني مشرف للحماية\n"
        "برمجة الأستاذ عبدالله البلوي"
    )

    if message.chat.type == ChatType.PRIVATE:
        await message.answer(text)
    else:
        # تظهر لوحة التحكم للمشرف فقط
        if await is_admin(message.chat.id, message.from_user.id):
            await message.reply("✅ لوحة تحكم المشرف", reply_markup=admin_keyboard())
        else:
            await message.reply("✅ تم تفعيل الحماية")
        cursor.execute("INSERT OR IGNORE INTO settings(chat_id, links, closed) VALUES (?,0,0)", (message.chat.id,))
        conn.commit()

# =============================
# الترحيب بالمشتركين الجدد
# =============================
@dp.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        await message.reply(f"👋 مرحباً {user.first_name} في القروب 🌿")

# =============================
# حماية الرسائل والروابط
# =============================
@dp.message(F.text)
async def security(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id
    if await is_admin(chat_id, user_id):
        return
    # قفل الوقت
    if is_closed_time():
        await message.delete()
        return
    # كشف الروابط
    if has_link(message.text):
        await message.delete()
        count = add_warning(chat_id, user_id)
        if count >= 3:
            await bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False),
                                           until_date=datetime.now(MECCA) + timedelta(hours=1))
            await message.answer("🔇 تم كتم العضو لمدة ساعة")
        else:
            await message.answer(f"⚠️ تحذير {count}/3")

# =============================
# Callbacks لوحة التحكم
# =============================
@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if not await is_admin(chat_id, user_id):
        await call.answer("⚠️ فقط المشرفين يمكنهم استخدام لوحة التحكم", show_alert=True)
        return

    # فتح الرسائل
    if call.data == "open_messages":
        await bot.set_chat_permissions(chat_id, ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        await call.message.answer("🟢 تم فتح الرسائل للجميع")

    # قفل الرسائل
    elif call.data == "close_messages":
        await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
        await call.message.answer("🔴 تم قفل الرسائل للجميع")

    # فتح الروابط
    elif call.data == "enable_links":
        cursor.execute("UPDATE settings SET links=1 WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.message.answer("✅ تم فتح الروابط")

    # قفل الروابط
    elif call.data == "disable_links":
        cursor.execute("UPDATE settings SET links=0 WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.message.answer("🔒 تم قفل الروابط")

    # تصفير التحذيرات
    elif call.data == "reset":
        cursor.execute("DELETE FROM warnings WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.message.answer("🧹 تم تصفير التحذيرات")

    # كتم عضو مع اختيار المدة
    elif call.data == "mute_user":
        await call.message.answer("🔇 أرسل معرف العضو + مدة الكتم بالدقائق (مثال: 123456789 30)")

        def check(m: types.Message):
            return m.chat.id == chat_id and m.from_user.id == user_id

        try:
            msg = await dp.bot.wait_for("message", check=check, timeout=120)
            parts = msg.text.split()
            target_id = int(parts[0])
            duration = int(parts[1]) if len(parts) > 1 else 60
            await bot.restrict_chat_member(chat_id, target_id,
                                           ChatPermissions(can_send_messages=False),
                                           until_date=datetime.now(MECCA) + timedelta(minutes=duration))
            await msg.reply(f"🔇 تم كتم العضو {target_id} لمدة {duration} دقيقة")
        except Exception:
            await call.message.answer("⚠️ لم يتم كتم العضو، أو انتهت المدة")

# =============================
# Main
# =============================
async def main():
    print("🔥 Bot Running")
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
