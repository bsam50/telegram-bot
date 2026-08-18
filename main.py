import os
import re
import sqlite3
import random
import time

from dotenv import load_dotenv
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)

DEV_IDS = {
    int(x.strip())
    for x in os.getenv("DEV_IDS", "").split(",")
    if x.strip().isdigit()
}

if OWNER_ID:
    DEV_IDS.add(OWNER_ID)

DB = "bot_data.db"


# =========================================================
# الرتب
# =========================================================

RANKS = {
    "عضو": 0,
    "مميز": 1,
    "ادمن": 2,
    "مدير": 3,
    "منشئ": 4,
    "مالك": 5,
    "مالك اساسي": 6,
}

ALIASES = {
    "الأدمن": "ادمن",
    "الادمن": "ادمن",
    "المالك": "مالك",
    "المالك الأساسي": "مالك اساسي",
    "المالك الاساسي": "مالك اساسي",
}


# =========================================================
# القفل
# =========================================================

LOCKS = [
    "جمثون",
    "السب",
    "الايرانيه",
    "الكتابة",
    "الاباحي",
    "تعديل الميديا",
    "التعديل",
    "الفيديو",
    "الصور",
    "الملصقات",
    "المتحركه",
    "الدردشه",
    "الروابط",
    "التاك",
    "البوتات",
    "المعرفات",
    "الكلايش",
    "التكرار",
    "التوجيه",
    "الانلاين",
    "الجهات",
    "الدخول",
    "الصوت",
    "الفويس",
    "التوجيه بالتقييد",
    "الروابط بالتقييد",
    "المتحركه بالتقييد",
    "الصور بالتقييد",
    "الفيديو بالتقييد",
]


FEATURES = [
    "ضافني",
    "الاذكار",
    "الثنائي",
    "افتاري",
    "التسليه",
    "الكت",
    "الترحيب",
    "الردود",
    "الانذار",
    "التحذير",
    "الايدي",
    "الرابط",
    "اطردني",
    "الحظر",
    "الرفع",
    "التنزيل",
    "التحويل",
    "الحمايه",
    "المنشن",
    "وضع الاقتباسات",
    "الخدميه",
    "اليوتيوب",
    "الايدي بالصوره",
    "التحقق",
    "ردود السورس",
    "ردود MY",
    "الاحصائيات",
]


# =========================================================
# قاعدة البيانات
# =========================================================

def DBconn():
    c = sqlite3.connect(DB)

    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            first_seen INTEGER,
            last_seen INTEGER
        );

        CREATE TABLE IF NOT EXISTS ranks(
            chat INTEGER,
            user INTEGER,
            rank TEXT,
            PRIMARY KEY(chat,user)
        );

        CREATE TABLE IF NOT EXISTS settings(
            chat INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY(chat,key)
        );

        CREATE TABLE IF NOT EXISTS replies(
            chat INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY(chat,key)
        );

        CREATE TABLE IF NOT EXISTS multi(
            chat INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY(chat,key)
        );

        CREATE TABLE IF NOT EXISTS special(
            chat INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY(chat,key)
        );

        CREATE TABLE IF NOT EXISTS global_replies(
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS global_multi(
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS global_special(
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS games(
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS warnings(
            chat INTEGER,
            user INTEGER,
            count INTEGER,
            PRIMARY KEY(chat,user)
        );

        CREATE TABLE IF NOT EXISTS global_bans(
            user INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS global_mutes(
            user INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS whispers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat INTEGER,
            sender INTEGER,
            text TEXT,
            created INTEGER
        );

        CREATE TABLE IF NOT EXISTS pending_whispers(
            user INTEGER PRIMARY KEY,
            chat INTEGER,
            created INTEGER
        );

        CREATE TABLE IF NOT EXISTS money(
            chat INTEGER,
            user INTEGER,
            coins INTEGER,
            bank INTEGER,
            PRIMARY KEY(chat,user)
        );

        CREATE TABLE IF NOT EXISTS marriages(
            chat INTEGER,
            user1 INTEGER,
            user2 INTEGER,
            PRIMARY KEY(chat,user1)
        );

        CREATE TABLE IF NOT EXISTS fun(
            chat INTEGER,
            user INTEGER,
            kind TEXT,
            PRIMARY KEY(chat,user,kind)
        );
        """
    )

    c.commit()
    return c


DBconn().close()


# =========================================================
# أدوات قاعدة البيانات
# =========================================================

def one(sql, args=()):
    c = DBconn()
    result = c.execute(sql, args).fetchone()
    c.close()
    return result


def many(sql, args=()):
    c = DBconn()
    result = c.execute(sql, args).fetchall()
    c.close()
    return result


def put(sql, args=()):
    c = DBconn()
    c.execute(sql, args)
    c.commit()
    c.close()


def setv(chat, key, value):
    put(
        "INSERT OR REPLACE INTO settings(chat,key,value) VALUES(?,?,?)",
        (chat, key, str(value)),
    )


def getv(chat, key, default="0"):
    result = one(
        "SELECT value FROM settings WHERE chat=? AND key=?",
        (chat, key),
    )
    return result[0] if result else default


def save_user(user):
    if not user:
        return

    now = int(time.time())

    old = one(
        "SELECT user_id FROM users WHERE user_id=?",
        (user.id,),
    )

    if old:
        put(
            """
            UPDATE users
            SET username=?, name=?, last_seen=?
            WHERE user_id=?
            """,
            (
                user.username or "",
                user.full_name or "",
                now,
                user.id,
            ),
        )
    else:
        put(
            """
            INSERT INTO users
            (user_id,username,name,first_seen,last_seen)
            VALUES(?,?,?,?,?)
            """,
            (
                user.id,
                user.username or "",
                user.full_name or "",
                now,
                now,
            ),
        )


def getrank(chat, user):
    result = one(
        "SELECT rank FROM ranks WHERE chat=? AND user=?",
        (chat, user),
    )
    return result[0] if result else "عضو"


def isdev(user_id):
    return user_id in DEV_IDS


# =========================================================
# الصلاحيات
# =========================================================

async def is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id,
        )

        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except Exception:
        return False


async def can(update, context, needed):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if isdev(user_id):
        return True

    rank = getrank(chat_id, user_id)

    if RANKS.get(rank, 0) >= needed:
        return True

    if needed <= 3:
        return await is_admin(update, context)

    return False


def target(update):
    if (
        update.message
        and update.message.reply_to_message
        and update.message.reply_to_message.from_user
    ):
        return update.message.reply_to_message.from_user

    return None


async def say(update, text, **kwargs):
    return await update.message.reply_text(text, **kwargs)


# =========================================================
# القوائم
# =========================================================

def menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👑 م1 الإدارة", callback_data="m1"),
                InlineKeyboardButton("⚙️ م2 الإعدادات", callback_data="m2"),
            ],
            [
                InlineKeyboardButton("🔒 م3 القفل والفتح", callback_data="m3"),
                InlineKeyboardButton("🎮 م4 التسلية", callback_data="m4"),
            ],
            [
                InlineKeyboardButton("👨‍💻 م5 المطور", callback_data="m5"),
                InlineKeyboardButton("🛠️ م6 الخدمات", callback_data="m6"),
            ],
        ]
    )


MENUS = {
    "m1": """
👑 م1 الإدارة

• رتبتي
• معلوماتي
• الرتب
• المالك
• رفع مميز
• رفع ادمن
• رفع مدير
• رفع منشئ
• رفع مالك
• رفع مالك اساسي
• تنزيل
• حظر
• طرد
• كتم
• فك الحظر
• فك الكتم
""",

    "m2": """
⚙️ م2 الإعدادات

• الرابط
• القوانين
• الترحيب
• الردود
• الردود المميزة
• الردود المتعددة
• إضافة رد
• إضافة رد مميز
• إضافة رد متعدد
""",

    "m3": """
🔒 م3 القفل والفتح

• قفل الروابط
• فتح الروابط
• قفل الصور
• فتح الصور
• قفل الفيديو
• فتح الفيديو
• قفل الملصقات
• فتح الملصقات
• قفل المتحركة
• فتح المتحركة
• قفل الكل
• فتح الكل

⚙️ التفعيل والتعطيل

• تفعيل الترحيب
• تعطيل الترحيب
• تفعيل الردود
• تعطيل الردود
• تفعيل الحماية
• تعطيل الحماية
""",

    "m4": """
🎮 م4 التسلية

• نسبة الحب
• بنك
• رصيدي
• راتب
• ايداع
• سحب
• ألعاب
""",

    "m5": """
👨‍💻 م5 المطور

• إضافة رد عام
• إضافة رد مميز
• إضافة رد متعدد عام
• حذف رد عام
• حذف رد مميز
• حذف رد متعدد عام
• الردود العامة
• الردود المميزة
• الردود المتعددة العامة
• إضافة لعبة
• حذف لعبة
• الألعاب
• الإحصائيات
""",

    "m6": """
🛠️ م6 الخدمات

• آيدي
• معلوماتي
• قرآن
• أذكار
• اقتباسات
• همسة
""",
}


# =========================================================
# START
# =========================================================

async def start(update, context):
    save_user(update.effective_user)

    chat = update.effective_chat

    # -----------------------------------------
    # خاص البوت
    # -----------------------------------------

    if chat.type == "private":

        args = context.args

        # رابط الهمسة
        if args and args[0].startswith("whisper_"):
            try:
                group_id = int(args[0].replace("whisper_", ""))

                put(
                    """
                    INSERT OR REPLACE INTO pending_whispers
                    (user,chat,created)
                    VALUES(?,?,?)
                    """,
                    (
                        update.effective_user.id,
                        group_id,
                        int(time.time()),
                    ),
                )

                await update.message.reply_text(
                    "💌 تم فتح الهمسة.\n\n"
                    "أرسل الآن الكلام الذي تريد إرساله للمجموعة.\n"
                    "سيتم نشره في المجموعة كـ **همسة مجهولة**."
                )

                return

            except Exception:
                pass

        if isdev(update.effective_user.id):
            return await dev_panel(update)

        await update.message.reply_text(
            "👋 أهلاً بك في **بوت لينا** 🌷\n\n"
            "🤖 أنا بوت إدارة وترفيه للمجموعات.\n\n"
            "أستطيع مساعدتك في:\n"
            "• إدارة المجموعة والصلاحيات\n"
            "• الردود التلقائية\n"
            "• الردود المميزة والمتعددة\n"
            "• القفل والحماية\n"
            "• الألعاب والتسلية\n"
            "• الهمسات\n"
            "• الخدمات المختلفة\n\n"
            "أضفني إلى مجموعتك وامنحني الصلاحيات المناسبة للاستفادة من الميزات."
        )

        return

    # -----------------------------------------
    # المجموعة
    # -----------------------------------------

    rank = getrank(
        chat.id,
        update.effective_user.id,
    )

    if rank == "عضو" and not await is_admin(update, context):
        return await update.message.reply_text(
            "👋 أهلاً بك.\n"
            "الأوامر الإدارية تظهر فقط لأصحاب الرتب."
        )

    await update.message.reply_text(
        "👋 أهلاً بك في بوت لينا.\n\n"
        "اختر القائمة:",
        reply_markup=menu(),
    )


# =========================================================
# لوحة المطور
# =========================================================

async def dev_panel(update):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ رد عام",
                    callback_data="dev_add_global",
                ),
                InlineKeyboardButton(
                    "⭐ رد مميز",
                    callback_data="dev_add_special",
                ),
            ],
            [
                InlineKeyboardButton(
                    "💬 رد متعدد عام",
                    callback_data="dev_add_multi",
                ),
                InlineKeyboardButton(
                    "🎮 الألعاب",
                    callback_data="dev_games",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 الردود",
                    callback_data="dev_lists",
                ),
                InlineKeyboardButton(
                    "📊 الإحصائيات",
                    callback_data="dev_stats",
                ),
            ],
        ]
    )

    return await update.message.reply_text(
        "👨‍💻 أهلاً بك عزيزي المطور\n\n"
        "من هنا تستطيع إدارة البوت والردود والألعاب والميزات.",
        reply_markup=keyboard,
    )


# =========================================================
# أزرار القوائم
# =========================================================

async def callbacks(update, context):
    query = update.callback_query

    await query.answer()

    data = query.data

    if data == "home":
        return await query.edit_message_text(
            "اختر القائمة:",
            reply_markup=menu(),
        )

    if data in MENUS:
        return await query.edit_message_text(
            MENUS[data],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↩️ رجوع",
                            callback_data="home",
                        )
                    ]
                ]
            ),
        )

    # لوحة المطور
    if data.startswith("dev_"):

        if not isdev(update.effective_user.id):
            return

        if data == "dev_home":
            return await query.edit_message_text(
                "👨‍💻 لوحة المطور",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ رد عام",
                                callback_data="dev_add_global",
                            ),
                            InlineKeyboardButton(
                                "⭐ رد مميز",
                                callback_data="dev_add_special",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "💬 رد متعدد عام",
                                callback_data="dev_add_multi",
                            ),
                        ],
                    ]
                ),
            )

        if data == "dev_add_global":
            return await query.edit_message_text(
                "➕ إضافة رد عام\n\n"
                "أرسل الرسالة التي تريد أن تكون ردًا.\n"
                "ثم اعمل لها رد واكتب:\n\n"
                "اضف رد عام الكلمة"
            )

        if data == "dev_add_special":
            return await query.edit_message_text(
                "⭐ إضافة رد مميز\n\n"
                "اعمل ردًا على الرسالة التي تريد حفظها ثم اكتب:\n\n"
                "اضف رد مميز الكلمة"
            )

        if data == "dev_add_multi":
            return await query.edit_message_text(
                "💬 إضافة رد متعدد عام\n\n"
                "اعمل ردًا على الرسالة ثم اكتب:\n\n"
                "اضف رد متعدد عام الكلمة"
            )

        if data == "dev_games":
            return await query.edit_message_text(
                "🎮 الألعاب\n\n"
                "إضافة لعبة:\n"
                "اضف لعبة اسم اللعبة | نص اللعبة\n\n"
                "حذف لعبة:\n"
                "مسح لعبة اسم اللعبة\n\n"
                "عرض الألعاب:\n"
                "الالعاب"
            )

        if data == "dev_lists":

            general = many(
                "SELECT key FROM global_replies ORDER BY key"
            )

            special = many(
                "SELECT key FROM global_special ORDER BY key"
            )

            multi = many(
                "SELECT key FROM global_multi ORDER BY key"
            )

            text = "📋 الردود العامة:\n"

            text += (
                "\n".join("• " + x[0] for x in general)
                if general
                else "لا توجد"
            )

            text += "\n\n⭐ الردود المميزة:\n"

            text += (
                "\n".join("• " + x[0] for x in special)
                if special
                else "لا توجد"
            )

            text += "\n\n💬 الردود المتعددة:\n"

            text += (
                "\n".join("• " + x[0] for x in multi)
                if multi
                else "لا توجد"
            )

            return await query.edit_message_text(text)

        if data == "dev_stats":

            users = one(
                "SELECT COUNT(*) FROM users"
            )[0]

            general = one(
                "SELECT COUNT(*) FROM global_replies"
            )[0]

            special = one(
                "SELECT COUNT(*) FROM global_special"
            )[0]

            multi = one(
                "SELECT COUNT(*) FROM global_multi"
            )[0]

            games = one(
                "SELECT COUNT(*) FROM games"
            )[0]

            return await query.edit_message_text(
                "📊 إحصائيات البوت\n\n"
                f"👥 المستخدمون: {users}\n"
                f"💬 الردود العامة: {general}\n"
                f"⭐ الردود المميزة: {special}\n"
                f"🔄 الردود المتعددة: {multi}\n"
                f"🎮 الألعاب: {games}"
            )


# =========================================================
# المطور
# =========================================================

async def developer(update, context):

    if not isdev(update.effective_user.id):
        return await say(
            update,
            "❌ هذا الأمر للمطور فقط.",
        )

    try:

        user = await context.bot.get_chat(OWNER_ID)

        username = (
            "@" + user.username
            if user.username
            else "بدون يوزر"
        )

        text = (
            "👨‍💻 المطور الأساسي\n\n"
            f"👤 الاسم: {user.full_name}\n"
            f"🔗 اليوزر: {username}\n"
            f"🆔 الآيدي: {OWNER_ID}"
        )

        photos = await context.bot.get_user_profile_photos(
            OWNER_ID,
            limit=1,
        )

        if photos.total_count:

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👨‍💻 لوحة المطور",
                            callback_data="dev_home",
                        )
                    ]
                ]
            )

            return await update.message.reply_photo(
                photos.photos[0][-1].file_id,
                caption=text,
                reply_markup=keyboard,
            )

        return await say(u
