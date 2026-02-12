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
# Keyboard لوحة تحكم المشرف
# =============================
def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔓 فتح الروابط", callback_data="enable_links"),
                InlineKeyboardButton(text="🔒 قفل الروابط", callback_data="disable_links")
            ],
            [
                InlineKeyboardButton(text="🧹 تصفير التحذيرات", callback_data="reset")
            ],
            # صف خاص بقفل/فتح المجموعة يدوياً
            [
                InlineKeyboardButton(text="🔒 قفل المجموعة", callback_data="close_group"),
                InlineKeyboardButton(text="🔓 تشغيل المجموعة", callback_data="open_group")
            ]
        ]
    )

# =============================
# Admin check
# =============================
async def is_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

# =============================
# Time check (للمجدول)
# =============================
def is_closed_time():
    now = datetime.now(MECCA)
    return now.hour >= 23 or now.hour < 7

# =============================
# قفل المجموعة (للإستخدام التلقائي مع رسالة الوقت)
# =============================
async def auto_close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(
        chat_id,
        "🔴 القروب مغلق الآن\n⏰ من الساعة 11 مساءً إلى 7 صباحاً\nبتوقيت مكة المكرمة"
    )

# =============================
# فتح المجموعة (للإستخدام التلقائي مع رسالة الوقت)
# =============================
async def auto_open_group(chat_id):
    await bot.set_chat_permissions(chat_id,
        ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
    )
    await bot.send_message(chat_id, "🟢 تم فتح القروب\nمرحباً بكم 🌿")

# =============================
# قفل المجموعة (يدوي - بدون رسالة الوقت)
# =============================
async def manual_close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(chat_id, "✅ تم قفل المجموعة بنجاح")

# =============================
# فتح المجموعة (يدوي - بدون رسالة الوقت)
# =============================
async def manual_open_group(chat_id):
    await bot.set_chat_permissions(chat_id,
        ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
    )
    await bot.send_message(chat_id, "✅ تم فتح المجموعة بنجاح")

# =============================
# Scheduler (يستخدم التواقيت التلقائية)
# =============================
async def scheduler():
    while True:
        cursor.execute("SELECT chat_id, closed FROM settings")
        rows = cursor.fetchall()
        for chat_id, closed in rows:
            if is_closed_time() and closed == 0:
                await auto_close_group(chat_id)
                cursor.execute("UPDATE settings SET closed=1 WHERE chat_id=?", (chat_id,))
                conn.commit()
            elif not is_closed_time() and closed == 1:
                await auto_open_group(chat_id)
                cursor.execute("UPDATE settings SET closed=0 WHERE chat_id=?", (chat_id,))
                conn.commit()
        await asyncio.sleep(60)

# =============================
# Link detect
# =============================
def has_link(text):
    if not text:
        return False
    return bool(re.search(r"(https?://|www\.|t\.me)", text.lower()))

# =============================
# Warnings
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
# Tabuk (بديل Start)
# =============================
@dp.message(Command("start"))
async def tabuk(message: types.Message):
    text = (
        "🤖 بوت Eduai-sa نماذج Ai التعليمية\n\n"
        "الموقع الالكتروني\nhttps://eduai-sa.com\n\n"
        "قناة نماذج Ai التعليمية\nhttps://t.me/eduai_ksa\n\n"
        "قروب ( نماذج Ai التعليمية ) 💬\nhttps://t.me/eduai_ksa1\n\n"
        "/n/nأضفني للقروب وارفعني مشرف للحماية./n/n"
        "برمجة الاستاذ عبدالله البلوي"
    )
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(text)
    else:
        await message.reply(
            "✅ تم تفعيل الحماية",
            reply_markup=admin_keyboard()
        )
        cursor.execute(
            "INSERT OR IGNORE INTO settings(chat_id, links, closed) VALUES (?,0,0)",
            (message.chat.id,)
        )
        conn.commit()

# =============================
# Welcome
# =============================
@dp.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        await message.reply(f"👋 مرحباً {user.first_name}")

# =============================
# Security
# =============================
@dp.message(F.text)
async def security(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if await is_admin(chat_id, user_id):
        return

    if is_closed_time():
        await message.delete()
        return

    if has_link(message.text):
        await message.delete()
        count = add_warning(chat_id, user_id)
        if count >= 3:
            # تعديل المدة إلى ساعة واحدة
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=datetime.now(MECCA) + timedelta(hours=1)
            )
            await message.answer("🔇 تم كتم العضو ساعة واحدة")
        else:
            await message.answer(f"⚠️ تحذير {count}/3")

# =============================
# الأمر /mute لكتم أي عضو مع اختيار المدة
# =============================
@dp.message(Command("mute"))
async def mute_command(message: types.Message):
    """كتم عضو معين مع مدة محددة.
    الاستخدام:
        /mute 1h      (بالرد على رسالة العضو)
        /mute 30m @username
        /mute 2d      (بالرد أو بذكر العضو)
    """
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(chat_id, user_id):
        await message.reply("❌ هذا الأمر للمشرفين فقط.")
        return

    # استخراج المدة من الرسالة
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("⚠️ يرجى تحديد المدة، مثال:\n`/mute 1h` (بالرد على رسالة العضو)\n`/mute 30m @username`")
        return

    duration_str = parts[1].lower()
    # تحويل المدة إلى timedelta
    delta = None
    match = re.match(r"^(\d+)([smhd])$", duration_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit == 's':
            delta = timedelta(seconds=value)
        elif unit == 'm':
            delta = timedelta(minutes=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'd':
            delta = timedelta(days=value)
    if not delta:
        await message.reply("❌ صيغة المدة غير صحيحة.\nاستخدم `30m`, `1h`, `2d`, `10s` ...")
        return

    # تحديد العضو المراد كتمه
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        # محاولة استخراج @username من النص
        if len(parts) >= 3:
            username = parts[2].lstrip('@')
            try:
                # الحصول على معلومات العضو عبر اسم المستخدم
                chat = await bot.get_chat(chat_id)
                async for member in bot.get_chat_members(chat_id):
                    if member.user.username and member.user.username.lower() == username.lower():
                        target_user = member.user
                        break
            except:
                pass
        if not target_user:
            await message.reply("❌ لم يتم العثور على العضو. تأكد من الرد على رسالته أو ذكر معرفه بشكل صحيح.")
            return

    # لا يمكن كتم المشرفين
    if await is_admin(chat_id, target_user.id):
        await message.reply("❌ لا يمكن كتم مشرف.")
        return

    try:
        await bot.restrict_chat_member(
            chat_id,
            target_user.id,
            ChatPermissions(can_send_messages=False),
            until_date=datetime.now(MECCA) + delta
        )
        await message.reply(f"🔇 تم كتم {target_user.first_name} لمدة {duration_str}.")
    except Exception as e:
        await message.reply(f"❌ فشل الكتم: {e}")

# =============================
# Callbacks لوحة التحكم
# =============================
@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if not await is_admin(chat_id, user_id):
        await call.answer("❌ للأعضاء المسموح لهم فقط", show_alert=True)
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

    # 🆕 أزرار قفل/فتح المجموعة - يدوي (رسالة مبسطة)
    elif call.data == "close_group":
        await manual_close_group(chat_id)
        cursor.execute("UPDATE settings SET closed=1 WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.answer("🔒 تم قفل المجموعة")
    elif call.data == "open_group":
        await manual_open_group(chat_id)
        cursor.execute("UPDATE settings SET closed=0 WHERE chat_id=?", (chat_id,))
        conn.commit()
        await call.answer("🔓 تم فتح المجموعة")

# =============================
# Main
# =============================
async def main():
    print("🔥 Bot Running")
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
