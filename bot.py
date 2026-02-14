import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from aiogram.enums import ChatType

# =============================
# TOKEN
# =============================
TOKEN = "8235364340:AAGQG0mwJqaaI5sAUoRpfnP_JLZ1zLBSdZI"

# =============================
# TIMEZONE FUNCTIONS
# =============================
def mecca_now():
    """ترجع الوقت الحالي بتوقيت مكة المكرمة (UTC+3) للمقارنة فقط"""
    return datetime.utcnow() + timedelta(hours=3)

def utc_now():
    """ترجع الوقت الحالي بتوقيت UTC لاستخدامه مع until_date"""
    return datetime.utcnow()

# =============================
# قائمة الكلمات الممنوعة (موسعة)
# =============================
BANNED_WORDS = [
    # كلمات خارجة / نابية
    "كس", "زب", "طيز", "شرج", "بظر", "فرج",
    "نيك", "ينيك", "انيك", "نيكني", "ينيكك",
    "متناك", "منيوك", "منيوكة", "منيوكين",
    "شرموطة", "شرموط", "شرمطة",
    "قحبة", "قحب", "قحبات",
    "عاهرة", "عاهرات", "عاهره",
    "خول", "خولات", "خولين",
    "لوطي", "لواط", "لوطية",
    "سحاق", "سحاقيات", "سحاقية",
    "سكس", "سكسي", "جنس", "جنسي",
    "سالب", "موجب", "مبادل",
    "محارم", "سفاح", "سفاحين",
    "اغتصاب", "مغتصب", "مغتصبة",
    # سب وقذف
    "لعن", "اللعنة", "ملعون",
    "كلب", "كلبة", "كلاب",
    "خنزير", "خنزيرة",
    "حمار", "حمارة", "حمير",
    "بهيمة", "بهيم",
    "ثور", "ثيران",
    "غبي", "غبية", "أغبياء",
    "أحمق", "حمقاء", "حمقى",
    "مجنون", "مجنونة",
    "معتوه", "معتوهة",
    "متخلف", "متخلفة",
    "وسخ", "وسخة",
    "قذر", "قذرة",
    "منحط", "منحطة",
    "حقير", "حقيرة",
    "خبيث", "خبيثة",
    "نذل", "نذلة",
    "وغد", "وغدة",
    # عيب وشتم
    "عيب", "حرام",
    "فاسق", "فاسقة",
    "فاجر", "فاجرة",
    "زاني", "زانية",
    "سارق", "سارقة",
    "كذاب", "كذابة",
    "منافق", "منافقة",
    "مرتزق", "مرتزقة",
    "عميل", "عملاء",
    # ألفاظ جنسية صريحة
    "سكس", "سكسي", "بورن", "إباحي", "إباحية",
    "سكربت", "سكربتات",
    "عري", "عرايا",
    "بزاز", "بز", "نهد", "نهدين", "صدر", "صدور",
    "مؤخرة", "عجيزة",
    "مقبلات", "مداعبات",
    "رومانسية", "رومانسي",
    "ليالي حب", "ليالي الدخلة",
    # كلمات طبية غير مرغوب فيها
    "اجازة مرضية", "سكليف", "تقرير طبي",
    "شهادة مرضية", "عذر طبي",
    "مرض", "مرضى", "مريض",
    "مستشفى", "عيادة",
    "دواء", "أدوية",
    "علاج", "معالجة",
    "وصفة طبية", "روشتة","وصفة طبية", "روشتة","خرى","خرا", "زق",
]

# نمط أرقام الجوال السعودي (05xxxxxxxx أو 9665xxxxxxxx)
SAUDI_PHONE_PATTERN = re.compile(r'(05\d{8}|9665\d{8})')

def contains_banned_content(text: str) -> bool:
    """التحقق مما إذا كان النص يحتوي على كلمة ممنوعة أو رقم جوال سعودي"""
    if not text:
        return False
    lower_text = text.lower()
    for word in BANNED_WORDS:
        if word in lower_text:
            return True
    if SAUDI_PHONE_PATTERN.search(text):
        return True
    return False

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
    closed INTEGER DEFAULT 0,
    manually_closed INTEGER DEFAULT 0,
    manually_opened INTEGER DEFAULT 0
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
    now = mecca_now()
    return now.hour >= 23 or now.hour < 7

# =============================
# الإغلاق والفتح التلقائي (مع رسالة الوقت)
# =============================
async def auto_close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(
        chat_id,
        "🔴 القروب مغلق الآن\n⏰ من الساعة 11 مساءً إلى 7 صباحاً\nبتوقيت مكة المكرمة"
    )
    cursor.execute(
        "UPDATE settings SET closed=1, manually_closed=0, manually_opened=0 WHERE chat_id=?",
        (chat_id,)
    )
    conn.commit()

async def auto_open_group(chat_id):
    await bot.set_chat_permissions(
        chat_id,
        ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True
        )
    )
    await bot.send_message(chat_id, "🟢 تم فتح القروب\nمرحباً بكم 🌿")
    cursor.execute(
        "UPDATE settings SET closed=0, manually_closed=0, manually_opened=0 WHERE chat_id=?",
        (chat_id,)
    )
    conn.commit()

# =============================
# الإغلاق والفتح اليدوي (بدون رسالة الوقت)
# =============================
async def manual_close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(chat_id, "✅ تم قفل المجموعة بنجاح")
    cursor.execute(
        "UPDATE settings SET closed=1, manually_closed=1, manually_opened=0 WHERE chat_id=?",
        (chat_id,)
    )
    conn.commit()

async def manual_open_group(chat_id):
    await bot.set_chat_permissions(
        chat_id,
        ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True
        )
    )
    await bot.send_message(chat_id, "✅ تم فتح المجموعة بنجاح")
    cursor.execute(
        "UPDATE settings SET closed=0, manually_closed=0, manually_opened=1 WHERE chat_id=?",
        (chat_id,)
    )
    conn.commit()

# =============================
# Scheduler
# =============================
async def scheduler():
    print("🚀 بدأ المجدول التلقائي - توقيت مكة المكرمة (UTC+3)")
    while True:
        now = mecca_now()
        print(f"🕐 توقيت مكة الآن: {now.strftime('%Y-%m-%d %H:%M:%S')} - الساعة: {now.hour}")

        cursor.execute("SELECT chat_id, closed, manually_closed, manually_opened FROM settings")
        rows = cursor.fetchall()
        print(f"📊 عدد المجموعات المسجلة: {len(rows)}")

        for chat_id, closed, manually_closed, manually_opened in rows:
            if is_closed_time():
                if closed == 0 and manually_opened == 0:
                    print(f"🔴 جاري إغلاق المجموعة {chat_id} تلقائياً")
                    await auto_close_group(chat_id)
            else:
                if closed == 1 and manually_closed == 0:
                    print(f"🟢 جاري فتح المجموعة {chat_id} تلقائياً")
                    await auto_open_group(chat_id)

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
# Start
# =============================
@dp.message(Command("start"))
async def tabuk(message: types.Message):
    text = (
        "🤖 بوت Eduai-sa نماذج Ai التعليمية\n\n"
        "الموقع الالكتروني\nhttps://eduai-sa.com\n\n"
        "قناة نماذج Ai التعليمية\nhttps://t.me/eduai_ksa\n\n"
        "قروب ( نماذج Ai التعليمية ) 💬\nhttps://t.me/eduai_ksa1\n\n"
        "\n\nأضفني للقروب وارفعني مشرف للحماية.\n\n"
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
            "INSERT OR IGNORE INTO settings(chat_id, links, closed, manually_closed, manually_opened) VALUES (?,0,0,0,0)",
            (message.chat.id,)
        )
        conn.commit()

# =============================
# Welcome
# =============================
@dp.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        if user.id == bot.id:
            continue
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

    cursor.execute("SELECT closed FROM settings WHERE chat_id=?", (chat_id,))
    row = cursor.fetchone()
    if row and row[0] == 1:
        await message.delete()
        return

    cursor.execute("SELECT links FROM settings WHERE chat_id=?", (chat_id,))
    row = cursor.fetchone()
    links_enabled = row[0] if row else 0

    violated = False
    if not links_enabled and has_link(message.text):
        violated = True
    if contains_banned_content(message.text):
        violated = True

    if violated:
        await message.delete()
        count = add_warning(chat_id, user_id)
        if count >= 3:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=utc_now() + timedelta(hours=1)
            )
            await message.answer("🔇 تم كتم العضو ساعة واحدة")
        else:
            await message.answer(f"⚠️ تحذير {count}/3")

# =============================
# الأمر /mute (يعمل فقط بالرد)
# =============================
@dp.message(Command("mute"))
async def mute_command(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(chat_id, user_id):
        await message.reply("❌ هذا الأمر للمشرفين فقط.")
        return

    if not message.reply_to_message:
        await message.reply("⚠️ يجب الرد على رسالة العضو الذي تريد كتمه.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("⚠️ يرجى تحديد المدة، مثال: `/mute 1h` عند الرد على العضو.")
        return

    duration_str = parts[1].lower()
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

    target_user = message.reply_to_message.from_user

    if await is_admin(chat_id, target_user.id):
        await message.reply("❌ لا يمكن كتم مشرف.")
        return

    try:
        await bot.restrict_chat_member(
            chat_id,
            target_user.id,
            ChatPermissions(can_send_messages=False),
            until_date=utc_now() + delta
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
    elif call.data == "close_group":
        await manual_close_group(chat_id)
        await call.answer("🔒 تم قفل المجموعة")
    elif call.data == "open_group":
        await manual_open_group(chat_id)
        await call.answer("🔓 تم فتح المجموعة")

# =============================
# Main
# =============================
async def main():
    print("🔥 بوت الحماية شغال - توقيت مكة المكرمة (UTC+3)")
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
