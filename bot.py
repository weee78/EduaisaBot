import asyncio
import logging
import re
import sqlite3
import random
from datetime import datetime, timedelta, date

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from aiogram.enums import ChatType

# =============================
# TOKEN
# =============================
TOKEN = "8235364340:AAGQG0mwJqaaI5sAUoRpfnP_JLZ1zLBSdZI"

# =============================
# معرف المجموعة الخاصة (التي يسمح فيها بالأمر /ask والنصائح)
# =============================
OWNER_GROUP_ID = -1003872430815

# =============================
# إعدادات DeepSeek API
# =============================
import openai
openai.api_key = "sk-06779354cc134f26a816282d5fb19984"
openai.api_base = "https://api.deepseek.com/v1"

async def ask_deepseek(question: str) -> str:
    try:
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="deepseek-chat",
            messages=[{"role": "user", "content": question}],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ خطأ في الاتصال بـ DeepSeek: {e}"

# =============================
# TIME FUNCTIONS
# =============================
def utc_now():
    return datetime.utcnow()

def mecca_now():
    return utc_now() + timedelta(hours=3)

def today_str():
    return date.today().isoformat()

# =============================
# قائمة الكلمات الممنوعة
# =============================
BANNED_WORDS = [
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
    "عيب", "حرام",
    "فاسق", "فاسقة",
    "فاجر", "فاجرة",
    "زاني", "زانية",
    "سارق", "سارقة",
    "كذاب", "كذابة",
    "منافق", "منافقة",
    "مرتزق", "مرتزقة",
    "عميل", "عملاء",
    "سكس", "سكسي", "بورن", "إباحي", "إباحية",
    "سكربت", "سكربتات",
    "عري", "عرايا",
    "بزاز", "بز", "نهد", "نهدين", "صدر", "صدور",
    "مؤخرة", "عجيزة",
    "مقبلات", "مداعبات",
    "رومانسية", "رومانسي",
    "ليالي حب", "ليالي الدخلة",
    "اجازة مرضية", "سكليف", "تقرير طبي",
    "شهادة مرضية", "عذر طبي",
    "مرض", "مرضى", "مريض",
    "مستشفى", "عيادة",
    "دواء", "أدوية",
    "علاج", "معالجة",
    "وصفة طبية", "روشتة",
]

SAUDI_PHONE_PATTERN = re.compile(r'(05\d{8}|9665\d{8})')

def contains_banned_content(text: str) -> bool:
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
# Logging & Bot
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS ask_usage (
    chat_id INTEGER,
    user_id INTEGER,
    date TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, user_id, date)
)
""")
conn.commit()

# =============================
# قائمة النصائح التقنية
# =============================
TIPS = [
    "💡 **نصيحة تقنية**: الذكاء الاصطناعي ليس مجرد روبوتات! تعلم أساسيات تعلم الآلة يمكن أن يغير مسار حياتك المهنية.",
    "🔐 **الأمن السيبراني**: استخدم كلمات مرور مختلفة لكل حساب، وفعّل المصادقة الثنائية (2FA) لحماية نفسك.",
    "🤖 **الذكاء الاصطناعي**: النماذج اللغوية الكبيرة (LLMs) مثل GPT و Gemini و DeepSeek تتعلم من كميات هائلة من النصوص لتوليد ردود طبيعية.",
    "🛡️ **الأمن السيبراني**: احذر من رسائل التصيد (Phishing) التي تبدو وكأنها من مصادر موثوقة. تحقق من الروابط قبل النقر.",
    "📊 **تقنية حديثة**: الحوسبة الكمومية (Quantum Computing) تعد بتغيير قواعد اللعبة في مجالات التشفير والمحاكاة.",
    "🚀 **الذكاء الاصطناعي**: يمكن للـ AI تحسين كفاءة الأعمال من خلال أتمتة المهام المتكررة وتحليل البيانات الضخمة.",
    "🔒 **الأمن السيبراني**: حافظ على تحديث برامجك وأنظمتك باستمرار، فالتحديثات غالباً ما تسد ثغرات أمنية.",
    "🧠 **الذكاء الاصطناعي**: الشبكات العصبية العميقة (Deep Neural Networks) مستوحاة من بنية الدماغ البشري.",
    "📱 **تقنية حديثة**: تقنية الجيل الخامس (5G) تقدم سرعات إنترنت فائقة ووقت استجابة منخفض، مما يفتح آفاقاً جديدة للإنترنت.",
    "🔎 **الأمن السيبراني**: استخدم متصفحاً يحترم خصوصيتك، وفكر في استخدام VPN لتشفير اتصالك.",
]

# =============================
# لوحة المفاتيح: تعتمد على المجموعة
# =============================
def admin_keyboard(chat_id: int):
    basic_buttons = [
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
    if chat_id == OWNER_GROUP_ID:
        extra_buttons = [
            [
                InlineKeyboardButton(text="✅ تفعيل /ask", callback_data="enable_ask"),
                InlineKeyboardButton(text="❌ تعطيل /ask", callback_data="disable_ask")
            ],
            [
                InlineKeyboardButton(text="💡 تفعيل النصائح", callback_data="enable_tips"),
                InlineKeyboardButton(text="🔇 تعطيل النصائح", callback_data="disable_tips")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=basic_buttons + extra_buttons)
    else:
        return InlineKeyboardMarkup(inline_keyboard=basic_buttons)

# =============================
# Admin check
# =============================
async def is_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# =============================
# Time check
# =============================
def is_closed_time():
    now = mecca_now()
    return now.hour >= 23 or now.hour < 7

# =============================
# Group open/close functions
# =============================
async def auto_close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(
        chat_id,
        "🔴 القروب مغلق الآن\n⏰ من الساعة 11 مساءً إلى 7 صباحاً\nبتوقيت مكة المكرمة"
    )
    cursor.execute("UPDATE settings SET closed=1, manually_closed=0, manually_opened=0 WHERE chat_id=?", (chat_id,))
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
    cursor.execute("UPDATE settings SET closed=0, manually_closed=0, manually_opened=0 WHERE chat_id=?", (chat_id,))
    conn.commit()

async def manual_close_group(chat_id):
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await bot.send_message(chat_id, "✅ تم قفل المجموعة بنجاح")
    cursor.execute("UPDATE settings SET closed=1, manually_closed=1, manually_opened=0 WHERE chat_id=?", (chat_id,))
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
    cursor.execute("UPDATE settings SET closed=0, manually_closed=0, manually_opened=1 WHERE chat_id=?", (chat_id,))
    conn.commit()

# =============================
# Scheduler (للقفل التلقائي)
# =============================
async def scheduler():
    print("🚀 بدأ المجدول التلقائي - توقيت مكة المكرمة (UTC+3)")
    while True:
        now = mecca_now()
        print(f"🕐 توقيت مكة الآن: {now.strftime('%Y-%m-%d %H:%M:%S')} - الساعة: {now.hour}")

        cursor.execute("SELECT chat_id, closed, manually_closed, manually_opened FROM settings")
        rows = cursor.fetchall()

        for chat_id, closed, manually_closed, manually_opened in rows:
            if is_closed_time():
                if closed == 0 and manually_opened == 0:
                    await auto_close_group(chat_id)
            else:
                if closed == 1 and manually_closed == 0:
                    await auto_open_group(chat_id)

        await asyncio.sleep(60)

# =============================
# المهمة اليومية للرسالة الترويجية (في المجموعة الخاصة)
# =============================
async def daily_promo():
    """إرسال رسالة ترويجية يومية في المجموعة الخاصة"""
    while True:
        now = mecca_now()
        target_hour = 8
        target_minute = 0
        next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        print(f"📅 الرسالة اليومية سترسل بعد {wait_seconds/3600:.2f} ساعة")
        await asyncio.sleep(wait_seconds)

        try:
            promo_text = (
                "🌞 صباح الخير! أنا بوت **نماذج Ai التعليمية**.\n\n"
                "هل لديك سؤال عن الذكاء الاصطناعي، التعليم، أو أي موضوع آخر؟\n"
                "اكتب الأمر `/ask` ثم سؤالك، وسأجيبك فوراً! (لديك 5 أسئلة يومياً)\n\n"
                "جرب الآن، وأخبرني ماذا تريد أن تتعلم اليوم؟ 🚀"
            )
            await bot.send_message(OWNER_GROUP_ID, promo_text)
        except Exception as e:
            print(f"❌ فشل إرسال الرسالة اليومية: {e}")

        await asyncio.sleep(24 * 3600)

# =============================
# المهمة اليومية للنصائح التقنية (للمجموعة الخاصة فقط)
# =============================
async def daily_tips():
    """إرسال نصائح تقنية يومية للمجموعة الخاصة فقط"""
    while True:
        now = mecca_now()
        target_hour = 10
        target_minute = 0
        next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        print(f"💡 النصائح اليومية سترسل بعد {wait_seconds/3600:.2f} ساعة")
        await asyncio.sleep(wait_seconds)

        tip = random.choice(TIPS)
        try:
            await bot.send_message(OWNER_GROUP_ID, tip)
        except Exception as e:
            print(f"❌ فشل إرسال نصيحة للمجموعة الخاصة: {e}")

        await asyncio.sleep(24 * 3600)

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
# الأمر /start
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
            reply_markup=admin_keyboard(message.chat.id)
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
# الأمر /mute (للمشرفين في أي مجموعة)
# =============================
@dp.message(F.text.startswith("/mute"))
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
        await message.reply("⚠️ يرجى تحديد المدة، مثال: `/mute 1h`")
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
        await message.reply("❌ صيغة المدة غير صحيحة.\nاستخدم `30m`, `1h`, `2d`...")
        return

    target_user = message.reply_to_message.from_user

    if await is_admin(chat_id, target_user.id):
        await message.reply("❌ لا يمكن كتم مشرف.")
        return

    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status != "administrator" or not bot_member.can_restrict_members:
            await message.reply("❌ البوت ليس لديه صلاحية كتم الأعضاء. قم برفعه مشرف مع صلاحية 'تقييد الأعضاء'.")
            return
    except:
        pass

    until = int((utc_now() + delta).timestamp())
    try:
        await bot.restrict_chat_member(
            chat_id,
            target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await message.reply(f"🔇 تم كتم {target_user.first_name} لمدة {duration_str}.")
    except Exception as e:
        await message.reply(f"❌ فشل الكتم: {e}")

# =============================
# الأمر /ask (يعمل فقط في المجموعة الخاصة)
# =============================
@dp.message(F.text.startswith("/ask"))
async def ask_command(message: types.Message):
    print("🔥 دالة ask_command استدعيت!")
    print(f"📌 النص: {message.text}")
    print(f"👤 المستخدم: {message.from_user.id}")
    print(f"💬 المجموعة: {message.chat.id}")

    chat_id = message.chat.id
    if chat_id != OWNER_GROUP_ID:
        await message.reply("❌ هذه الميزة متاحة فقط في المجموعة الرسمية.")
        return

    user_id = message.from_user.id
    question = message.text.replace("/ask", "", 1).strip()
    if not question:
        await message.reply("❌ يرجى كتابة سؤالك بعد الأمر.\nمثال: `/ask ما هو الذكاء الاصطناعي؟`")
        return

    today = today_str()
    cursor.execute(
        "SELECT count FROM ask_usage WHERE chat_id=? AND user_id=? AND date=?",
        (chat_id, user_id, today)
    )
    row = cursor.fetchone()
    current_usage = row[0] if row else 0

    if current_usage >= 5:
        await message.reply(
            "🌼 شكراً لك على تفاعلك! لقد استهلكت اليوم جميع محاولاتك المتاحة (5/5).\n"
            "نراكم غداً مع المزيد من المعرفة! 📚"
        )
        return

    processing_msg = await message.reply("⏳ جاري البحث عن إجابة...")

    answer = await ask_deepseek(question)

    if row:
        cursor.execute(
            "UPDATE ask_usage SET count = count + 1 WHERE chat_id=? AND user_id=? AND date=?",
            (chat_id, user_id, today)
        )
    else:
        cursor.execute(
            "INSERT INTO ask_usage (chat_id, user_id, date, count) VALUES (?, ?, ?, 1)",
            (chat_id, user_id, today)
        )
    conn.commit()

    remaining = 5 - (current_usage + 1)
    user_name = message.from_user.first_name
    thanks = f"شكراً لك {user_name}! 🤍 تبقى لديك {remaining} أسئلة لهذا اليوم."
    final_answer = f"{thanks}\n\n{answer}"

    await processing_msg.delete()
    await message.reply(final_answer)

# =============================
# Security (الحماية التلقائية للجميع) - يجب أن يكون بعد معالجات الأوامر
# =============================
@dp.message(F.text)
async def security(message: types.Message):
    if message.text.startswith("/"):
        return

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
            until = int((utc_now() + timedelta(hours=1)).timestamp())
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await message.answer("🔇 تم كتم العضو ساعة واحدة")
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
    elif call.data in ["enable_ask", "disable_ask", "enable_tips", "disable_tips"]:
        if chat_id != OWNER_GROUP_ID:
            await call.answer("❌ هذه الإعدادات غير متاحة في هذه المجموعة.", show_alert=True)
            return
        if call.data == "enable_ask":
            await call.message.answer("✅ تم تفعيل الأمر /ask في المجموعة الخاصة.")
        elif call.data == "disable_ask":
            await call.message.answer("🔒 تم تعطيل الأمر /ask في المجموعة الخاصة.")
        elif call.data == "enable_tips":
            await call.message.answer("💡 تم تفعيل النصائح اليومية في المجموعة الخاصة.")
        elif call.data == "disable_tips":
            await call.message.answer("🔇 تم تعطيل النصائح اليومية في المجموعة الخاصة.")
    await call.answer()

# =============================
# Main
# =============================
async def main():
    print("🔥 بوت الحماية شغال - توقيت UTC معتمد")
    asyncio.create_task(scheduler())
    asyncio.create_task(daily_promo())
    asyncio.create_task(daily_tips())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
