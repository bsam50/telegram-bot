import json
import os
import re
import logging
from datetime import datetime, timedelta
from functools import wraps

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ChatMemberHandler,
    filters,
)

# ============================================================
# إعدادات
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()

# يمكنك وضع آيدي المطور في Railway باسم DEV_ID
try:
    DEV_ID = int(os.getenv("DEV_ID", "0"))
except ValueError:
    DEV_ID = 0

DATA_FILE = "bot_data.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# قاعدة البيانات البسيطة
# ============================================================

DEFAULT_DATA = {
    "users": {},
    "groups": {},
    "global_ban": [],
    "global_mute": [],
    "global_ranks": {},
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, value in DEFAULT_DATA.items():
            if key not in data:
                data[key] = value

        return data

    except Exception as e:
        logger.error("فشل تحميل البيانات: %s", e)
        return DEFAULT_DATA.copy()


DATA = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DATA, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("فشل حفظ البيانات: %s", e)


# ============================================================
# أدوات عامة
# ============================================================

def get_group(chat_id):
    key = str(chat_id)

    if key not in DATA["groups"]:
        DATA["groups"][key] = {
            "owners": [],
            "main_owners": [],
            "creators": [],
            "managers": [],
            "admins": [],
            "vips": [],
            "banned": [],
            "muted": [],
            "rules": "لم يتم تعيين القوانين بعد.",
            "welcome": True,
            "welcome_text": "أهلًا بك {name} في {title} ❤️",
            "link": "",
            "replies": {},
            "special_replies": {},
            "multi_replies": {},
            "locks": {},
            "channels": [],
            "settings": {},
        }
        save_data()

    return DATA["groups"][key]


def user_id(update):
    if update.effective_user:
        return update.effective_user.id
    return 0


def is_dev(update):
    return user_id(update) == DEV_ID and DEV_ID != 0


def normalize(text):
    if not text:
        return ""

    return (
        text.strip()
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
    )


async def send(update, text, **kwargs):
    if update.message:
        return await update.message.reply_text(text, **kwargs)

    if update.callback_query:
        return await update.callback_query.message.reply_text(text, **kwargs)

    return None


# ============================================================
# نظام الرتب
# ============================================================

RANKS = {
    "عضو": 0,
    "مميز": 1,
    "ادمن": 2,
    "مدير": 3,
    "منشئ": 4,
    "مالك": 5,
    "مالك اساسي": 6,
    "مطوّر": 7,
}


def get_rank(chat_id, uid):
    if uid == DEV_ID and DEV_ID != 0:
        return "مطوّر"

    group = get_group(chat_id)
    sid = str(uid)

    if sid in map(str, group["main_owners"]):
        return "مالك اساسي"

    if sid in map(str, group["owners"]):
        return "مالك"

    if sid in map(str, group["creators"]):
        return "منشئ"

    if sid in map(str, group["managers"]):
        return "مدير"

    if sid in map(str, group["admins"]):
        return "ادمن"

    if sid in map(str, group["vips"]):
        return "مميز"

    return "عضو"


def rank_level(rank):
    return RANKS.get(normalize(rank), 0)


def can_manage(chat_id, uid):
    return rank_level(get_rank(chat_id, uid)) >= RANKS["ادمن"]


def can_promote(chat_id, uid):
    return rank_level(get_rank(chat_id, uid)) >= RANKS["مدير"]


def can_owner(chat_id, uid):
    return rank_level(get_rank(chat_id, uid)) >= RANKS["مالك"]


async def require_group(update, context):
    if not update.effective_chat or update.effective_chat.type == "private":
        await send(update, "هذا الأمر يعمل داخل المجموعات فقط.")
        return False
    return True


# ============================================================
# حفظ دخول المستخدم
# ============================================================

async def remember_user(update, context):
    user = update.effective_user

    if not user:
        return

    uid = str(user.id)

    DATA["users"][uid] = {
        "id": user.id,
        "username": user.username or "",
        "name": user.full_name,
        "last_seen": datetime.utcnow().isoformat(),
    }

    save_data()


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await remember_user(update, context)

    user = update.effective_user

    if update.effective_chat.type == "private":
        keyboard = [
            [
                InlineKeyboardButton(
                    "📚 أوامر البوت",
                    callback_data="commands",
                )
            ],
            [
                InlineKeyboardButton(
                    "👨‍💻 المطور",
                    callback_data="developer",
                )
            ],
        ]

        text = (
            f"مرحبًا {user.first_name} ❤️\n\n"
            "أنا بوت لينا 🤖\n"
            "بوت إدارة وحماية وترفيه للمجموعات.\n\n"
            "أستطيع مساعدتك في:\n"
            "• إدارة المجموعة والصلاحيات\n"
            "• الحظر والكتم والطرد\n"
            "• الردود العامة والمميزة\n"
            "• الهمسات\n"
            "• الترحيب والقوانين\n"
            "• القفل والفتح\n"
            "• الألعاب والترفيه\n"
            "• الخدمات والأوامر المختلفة\n\n"
            "اضغط على «أوامر البوت» لرؤية القائمة."
        )

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    else:
        await update.message.reply_text(
            f"أهلًا {user.first_name} ❤️\n"
            "أنا بوت لينا لحماية وإدارة المجموعة."
        )


# ============================================================
# قائمة الأوامر
# ============================================================

COMMANDS_TEXT = """
🤖 أوامر بوت لينا

━━━ 👑 الإدارة ━━━

رتبتي
معلوماتي
رفع مميز
تنزيل مميز
رفع ادمن
تنزيل ادمن
رفع مدير
تنزيل مدير
رفع منشئ
تنزيل منشئ
رفع مالك
تنزيل مالك

━━━ 🛡️ الحماية ━━━

حظر
فك حظر
طرد
كتم
فك كتم
تقييد
تحذير
مسح
المحظورين
المكتومين

━━━ 🔒 القفل والفتح ━━━

قفل الروابط
فتح الروابط
قفل الصور
فتح الصور
قفل الفيديو
فتح الفيديو
قفل الصوت
فتح الصوت
قفل الملصقات
فتح الملصقات
قفل المتحركة
فتح المتحركة
قفل المنشن
فتح المنشن
قفل التاك
فتح التاك
قفل البوتات
فتح البوتات
قفل التوجيه
فتح التوجيه
قفل التعديل
فتح التعديل
قفل الكتابة
فتح الكتابة
قفل الكل
فتح الكل

━━━ 💬 الردود ━━━

اضف رد
اضف رد عام
اضف رد مميز
اضف رد متعدد
حذف رد
حذف رد عام
حذف رد مميز
الردود
الردود العامة
الردود المميزة

━━━ ⚙️ الإعدادات ━━━

الرابط
ضع رابط
حذف الرابط
القوانين
ضع قوانين
الترحيب
ضع ترحيب
حذف الترحيب
ايدي المجموعة
معلومات المجموعة
الاعدادات

━━━ 💌 الهمسات ━━━

اهمس
همسة

━━━ 🎮 الترفيه ━━━

نسبة الحب
تحبه
هطف
بثر
حمار
زواج
طلاق

━━━ 👨‍💻 المطور ━━━

لوحة المطور
احصائيات
اذاعة
اضف رد للمطور
حذف رد للمطور
اضف لعبة
حذف لعبة
تفعيل الردود
تعطيل الردود
حظر عام
فك حظر عام
كتم عام
فك كتم عام
"""


async def commands(update, context):
    await send(update, COMMANDS_TEXT)


# ============================================================
# معلومات المستخدم ورتبته
# ============================================================

async def my_rank(update, context):
    if not await require_group(update, context):
        return

    uid = user_id(update)
    chat_id = update.effective_chat.id
    rank = get_rank(chat_id, uid)

    await send(
        update,
        f"👤 الاسم: {update.effective_user.full_name}\n"
        f"🆔 الآيدي: `{uid}`\n"
        f"🎖️ رتبتك: **{rank}**",
        parse_mode="Markdown",
    )


async def my_info(update, context):
    if not await require_group(update, context):
        return

    uid = user_id(update)
    chat_id = update.effective_chat.id

    await send(
        update,
        f"👤 الاسم: {update.effective_user.full_name}\n"
        f"🔹 المستخدم: @{update.effective_user.username or 'لا يوجد'}\n"
        f"🆔 الآيدي: `{uid}`\n"
        f"🎖️ الرتبة: {get_rank(chat_id, uid)}",
        parse_mode="Markdown",
    )


# ============================================================
# استخراج المستخدم المستهدف
# ============================================================

async def get_target(update, context):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user

    if context.args:
        value = context.args[0]

        if value.isdigit():
            try:
                member = await context.bot.get_chat_member(
                    update.effective_chat.id,
                    int(value),
                )
                return member.user
            except Exception:
                return None

        username = value.lstrip("@")

        try:
            member = await context.bot.get_chat_member(
                update.effective_chat.id,
                username,
            )
            return member.user
        except Exception:
            return None

    return None


# ============================================================
# الرتب
# ============================================================

async def promote(update, context, rank_name):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id
    uid = user_id(update)

    if not can_promote(chat_id, uid):
        await send(update, "❌ ليس لديك صلاحية استخدام هذا الأمر.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو أو اكتب آيديه.")
        return

    group = get_group(chat_id)
    tid = target.id

    lists = {
        "مميز": "vips",
        "ادمن": "admins",
        "مدير": "managers",
        "منشئ": "creators",
        "مالك": "owners",
        "مالك اساسي": "main_owners",
    }

    key = lists[rank_name]

    for other_key in lists.values():
        if tid in group[other_key] and other_key != key:
            group[other_key].remove(tid)

    if tid not in group[key]:
        group[key].append(tid)

    save_data()

    await send(
        update,
        f"✅ تم رفع {target.full_name} إلى رتبة **{rank_name}**.",
        parse_mode="Markdown",
    )


async def demote(update, context, rank_name):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id
    uid = user_id(update)

    if not can_promote(chat_id, uid):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    group = get_group(chat_id)

    lists = {
        "مميز": "vips",
        "ادمن": "admins",
        "مدير": "managers",
        "منشئ": "creators",
        "مالك": "owners",
        "مالك اساسي": "main_owners",
    }

    key = lists[rank_name]

    if target.id in group[key]:
        group[key].remove(target.id)

    save_data()

    await send(
        update,
        f"✅ تم تنزيل رتبة {target.full_name}.",
    )


# ============================================================
# الحظر والطرد والكتم
# ============================================================

async def ban(update, context):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id

    if not can_manage(chat_id, user_id(update)):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    try:
        await context.bot.ban_chat_member(
            chat_id,
            target.id,
        )

        group = get_group(chat_id)

        if target.id not in group["banned"]:
            group["banned"].append(target.id)

        save_data()

        await send(
            update,
            f"🚫 تم حظر {target.full_name}.",
        )

    except Exception as e:
        logger.error(e)
        await send(update, "❌ لا أستطيع حظر العضو. تأكد أن البوت مشرف.")


async def unban(update, context):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id

    if not can_manage(chat_id, user_id(update)):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    try:
        await context.bot.unban_chat_member(
            chat_id,
            target.id,
            only_if_banned=True,
        )

        group = get_group(chat_id)

        if target.id in group["banned"]:
            group["banned"].remove(target.id)

        save_data()

        await send(update, "✅ تم فك الحظر.")

    except Exception:
        await send(update, "❌ حدث خطأ أثناء فك الحظر.")


async def kick(update, context):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id

    if not can_manage(chat_id, user_id(update)):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        await context.bot.unban_chat_member(chat_id, target.id)

        await send(
            update,
            f"👢 تم طرد {target.full_name}.",
        )

    except Exception:
        await send(update, "❌ لم أستطع طرد العضو.")


async def mute(update, context):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id

    if not can_manage(chat_id, user_id(update)):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    permissions = ChatPermissions(can_send_messages=False)

    try:
        await context.bot.restrict_chat_member(
            chat_id,
            target.id,
            permissions=permissions,
        )

        group = get_group(chat_id)

        if target.id not in group["muted"]:
            group["muted"].append(target.id)

        save_data()

        await send(
            update,
            f"🔇 تم كتم {target.full_name}.",
        )

    except Exception:
        await send(update, "❌ تأكد أن البوت مشرف ولديه صلاحية التقييد.")


async def unmute(update, context):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id

    if not can_manage(chat_id, user_id(update)):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
    )

    try:
        await context.bot.restrict_chat_member(
            chat_id,
            target.id,
            permissions=permissions,
        )

        group = get_group(chat_id)

        if target.id in group["muted"]:
            group["muted"].remove(target.id)

        save_data()

        await send(update, "🔊 تم فك الكتم.")

    except Exception:
        await send(update, "❌ حدث خطأ.")


# ============================================================
# الردود
# ============================================================

async def add_reply(update, context, reply_type="normal"):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id
    uid = user_id(update)

    if not can_manage(chat_id, uid):
        await send(update, "❌ تحتاج إلى رتبة إدارية لإضافة رد.")
        return

    if len(context.args) < 2:
        await send(
            update,
            "الاستخدام:\n"
            "اضف رد الكلمة الرد\n\n"
            "مثال:\n"
            "اضف رد هلا هلا والله ❤️",
        )
        return

    keyword = context.args[0].strip()
    response = " ".join(context.args[1:]).strip()

    group = get_group(chat_id)

    if reply_type == "normal":
        group["replies"][keyword] = response
        title = "الرد"

    elif reply_type == "special":
        group["special_replies"][keyword] = response
        title = "الرد المميز"

    else:
        group["multi_replies"][keyword] = response
        title = "الرد المتعدد"

    save_data()

    await send(
        update,
        f"✅ تم حفظ {title}:\n"
        f"الكلمة: {keyword}\n"
        f"الرد: {response}",
    )


async def delete_reply(update, context):
    if not await require_group(update, context):
        return

    if not can_manage(
        update.effective_chat.id,
        user_id(update),
    ):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    if not context.args:
        await send(update, "اكتب كلمة الرد التي تريد حذفها.")
        return

    keyword = context.args[0]
    group = get_group(update.effective_chat.id)

    deleted = False

    for key in [
        "replies",
        "special_replies",
        "multi_replies",
    ]:
        if keyword in group[key]:
            del group[key][keyword]
            deleted = True

    save_data()

    if deleted:
        await send(update, f"✅ تم حذف الرد: {keyword}")
    else:
        await send(update, "❌ الرد غير موجود.")


async def show_replies(update, context):
    if not await require_group(update, context):
        return

    group = get_group(update.effective_chat.id)

    lines = ["💬 الردود الموجودة:\n"]

    if group["replies"]:
        lines.append("━━ الردود العادية ━━")
        for key in group["replies"]:
            lines.append(f"• {key}")

    if group["special_replies"]:
        lines.append("\n━━ الردود المميزة ━━")
        for key in group["special_replies"]:
            lines.append(f"• {key}")

    if group["multi_replies"]:
        lines.append("\n━━ الردود المتعددة ━━")
        for key in group["multi_replies"]:
            lines.append(f"• {key}")

    if len(lines) == 1:
        lines.append("لا توجد ردود.")

    await send(update, "\n".join(lines))


# ============================================================
# معالجة الردود تلقائيًا
# ============================================================

async def automatic_replies(update, context):
    if not update.message or not update.message.text:
        return

    await remember_user(update, context)

    chat = update.effective_chat

    if not chat:
        return

    # في الخاص لا نستخدم ردود المجموعة
    if chat.type == "private
