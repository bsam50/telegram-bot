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
    if chat.type == "private":
        return

    group = get_group(chat.id)

    text = update.message.text.strip()

    # الردود المميزة تتطلب رتبة
    if text in group["special_replies"]:
        uid = user_id(update)

        if rank_level(get_rank(chat.id, uid)) >= RANKS["مميز"]:
            await update.message.reply_text(
                group["special_replies"][text]
            )
        return

    if text in group["replies"]:
        await update.message.reply_text(
            group["replies"][text]
        )
        return

    if text in group["multi_replies"]:
        await update.message.reply_text(
            group["multi_replies"][text]
        )


# ============================================================
# الهمسات
# ============================================================

async def whisper(update, context):
    if not await require_group(update, context):
        return

    target = await get_target(update, context)

    if not target:
        await send(
            update,
            "💌 طريقة الهمسة:\n"
            "قم بالرد على العضو واكتب:\n"
            "اهمس\n\n"
            "ثم سيرسل لك البوت الهمسة في الخاص.",
        )
        return

    user = update.effective_user

    text = (
        "💌 همسة من المجموعة\n\n"
        f"المجموعة: {update.effective_chat.title}\n"
        f"المرسل: {user.full_name}\n\n"
        "أرسل رسالتك هنا وسأقوم بإرسالها للمجموعة."
    )

    context.user_data["whisper_chat"] = update.effective_chat.id
    context.user_data["whisper_target"] = target.id

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
        )

        await send(
            update,
            "💌 تم فتح الهمسة في الخاص. أرسل رسالتك للبوت هناك.",
        )

    except Exception:
        await send(
            update,
            "❌ لم أستطع مراسلتك في الخاص.\n"
            "افتح محادثة البوت واضغط Start أولًا.",
        )


async def whisper_private(update, context):
    if update.effective_chat.type != "private":
        return

    if "whisper_chat" not in context.user_data:
        return

    if not update.message:
        return

    chat_id = context.user_data["whisper_chat"]
    target_id = context.user_data.get("whisper_target")

    text = update.message.text or ""

    if not text:
        return

    sender = update.effective_user

    message = (
        "💌 **همسة**\n\n"
        f"من: {sender.full_name}\n"
        f"إلى: {target_id}\n\n"
        f"{text}"
    )

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
        )

        await update.message.reply_text(
            "✅ تم إرسال الهمسة إلى المجموعة."
        )

        context.user_data.pop("whisper_chat", None)
        context.user_data.pop("whisper_target", None)

    except Exception:
        await update.message.reply_text(
            "❌ لم أستطع إرسال الهمسة."
        )


# ============================================================
# القوانين والرابط
# ============================================================

async def rules(update, context):
    if not await require_group(update, context):
        return

    group = get_group(update.effective_chat.id)

    await send(
        update,
        f"📜 قوانين المجموعة:\n\n{group['rules']}",
    )


async def set_rules(update, context):
    if not await require_group(update, context):
        return

    if not can_manage(
        update.effective_chat.id,
        user_id(update),
    ):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    if not context.args:
        await send(update, "اكتب القوانين بعد الأمر.")
        return

    group = get_group(update.effective_chat.id)
    group["rules"] = " ".join(context.args)

    save_data()

    await send(update, "✅ تم حفظ قوانين المجموعة.")


async def group_link(update, context):
    if not await require_group(update, context):
        return

    group = get_group(update.effective_chat.id)

    if group["link"]:
        await send(
            update,
            f"🔗 رابط المجموعة:\n{group['link']}",
        )
    else:
        try:
            link = await context.bot.create_chat_invite_link(
                update.effective_chat.id
            )

            group["link"] = link.invite_link
            save_data()

            await send(
                update,
                f"🔗 رابط المجموعة:\n{link.invite_link}",
            )

        except Exception:
            await send(
                update,
                "❌ لا أستطيع إنشاء الرابط. "
                "تأكد أن البوت مشرف.",
            )


async def set_link(update, context):
    if not await require_group(update, context):
        return

    if not can_owner(
        update.effective_chat.id,
        user_id(update),
    ):
        await send(update, "❌ هذا الأمر للمالك.")
        return

    if not context.args:
        await send(update, "اكتب الرابط بعد الأمر.")
        return

    group = get_group(update.effective_chat.id)
    group["link"] = context.args[0]

    save_data()

    await send(update, "✅ تم حفظ الرابط.")


async def delete_link(update, context):
    if not await require_group(update, context):
        return

    if not can_owner(
        update.effective_chat.id,
        user_id(update),
    ):
        await send(update, "❌ هذا الأمر للمالك.")
        return

    group = get_group(update.effective_chat.id)
    group["link"] = ""

    save_data()

    await send(update, "✅ تم حذف الرابط.")


# ============================================================
# الترحيب
# ============================================================

async def set_welcome(update, context):
    if not await require_group(update, context):
        return

    if not can_manage(
        update.effective_chat.id,
        user_id(update),
    ):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    if not context.args:
        await send(update, "اكتب رسالة الترحيب بعد الأمر.")
        return

    group = get_group(update.effective_chat.id)
    group["welcome_text"] = " ".join(context.args)

    save_data()

    await send(update, "✅ تم تغيير رسالة الترحيب.")


async def welcome_status(update, context):
    if not await require_group(update, context):
        return

    group = get_group(update.effective_chat.id)

    status = "مفعل ✅" if group["welcome"] else "معطل ❌"

    await send(
        update,
        f"👋 الترحيب: {status}\n\n"
        f"{group['welcome_text']}",
    )


async def new_member(update, context):
    if not update.chat_member:
        return

    member = update.chat_member.new_chat_member

    if member.status not in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
    ]:
        return

    group = get_group(update.effective_chat.id)

    if not group["welcome"]:
        return

    user = member.user

    text = group["welcome_text"].format(
        name=user.full_name,
        title=update.effective_chat.title or "",
    )

    try:
        await context.bot.send_message(
            update.effective_chat.id,
            text,
        )
    except Exception as e:
        logger.error(e)


# ============================================================
# القفل والفتح
# ============================================================

LOCK_TYPES = {
    "الروابط": "links",
    "الصور": "photos",
    "الفيديو": "videos",
    "الصوت": "audio",
    "الملصقات": "stickers",
    "المتحركة": "animations",
    "المنشن": "mentions",
    "التاك": "tags",
    "البوتات": "bots",
    "التوجيه": "forward",
    "التعديل": "edit",
    "الكتابة": "text",
    "الجهات": "contacts",
}


async def set_lock(update, context, enabled):
    if not await require_group(update, context):
        return

    chat_id = update.effective_chat.id

    if not can_manage(chat_id, user_id(update)):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    if not context.args:
        await send(
            update,
            "اكتب نوع القفل.\n"
            "مثال: قفل الروابط",
        )
        return

    lock_name = normalize(" ".join(context.args))

    if lock_name == "الكل":
        for key in LOCK_TYPES.values():
            get_group(chat_id)["locks"][key] = enabled

        save_data()

        await send(
            update,
            "🔒 تم قفل جميع أنواع المحتوى."
            if enabled
            else "🔓 تم فتح جميع أنواع المحتوى.",
        )
        return

    key = LOCK_TYPES.get(lock_name)

    if not key:
        await send(update, "❌ نوع القفل غير معروف.")
        return

    group = get_group(chat_id)
    group["locks"][key] = enabled

    save_data()

    await send(
        update,
        f"{'🔒 تم قفل' if enabled else '🔓 تم فتح'} {lock_name}.",
    )


# ============================================================
# مراقبة المحتوى المقفول
# ============================================================

async def lock_filter(update, context):
    if not update.message:
        return

    chat = update.effective_chat

    if chat.type == "private":
        return

    group = get_group(chat.id)
    message = update.message
    uid = user_id(update)

    # المدراء لا تطبق عليهم الأقفال
    if can_manage(chat.id, uid):
        return

    checks = []

    if message.photo:
        checks.append(("photos", "الصور"))

    if message.video:
        checks.append(("videos", "الفيديو"))

    if message.animation:
        checks.append(("animations", "المتحركة"))

    if message.sticker:
        checks.append(("stickers", "الملصقات"))

    if message.voice or message.audio:
        checks.append(("audio", "الصوت"))

    if message.contact:
        checks.append(("contacts", "الجهات"))

    if message.text:
        text = message.text

        if re.search(r"https?://|t\.me/|www\.", text):
            checks.append(("links", "الروابط"))

        if "@" in text:
            checks.append(("mentions", "المنشن"))

    if message.forward_origin:
        checks.append(("forward", "التوجيه"))

    for key, name in checks:
        if group["locks"].get(key, False):
            try:
                await message.delete()
            except Exception:
                pass

            return


# ============================================================
# مسح
# ============================================================

async def clear(update, context):
    if not await require_group(update, context):
        return

    if not can_manage(
        update.effective_chat.id,
        user_id(update),
    ):
        await send(update, "❌ ليس لديك صلاحية.")
        return

    if not update.message.reply_to_message:
        await send(
            update,
            "❌ قم بالرد على الرسالة التي تريد بدء المسح منها.",
        )
        return

    start_id = update.message.reply_to_message.message_id
    end_id = update.message.message_id

    deleted = 0

    for message_id in range(start_id, end_id + 1):
        try:
            await context.bot.delete_message(
                update.effective_chat.id,
                message_id,
            )
            deleted += 1
        except Exception:
            pass

    await send(
        update,
        f"🧹 تم مسح {deleted} رسالة.",
    )


# ============================================================
# الترفيه
# ============================================================

async def love(update, context):
    target = await get_target(update, context)

    if target:
        name = target.full_name
    else:
        name = update.effective_user.full_name

    # ثابت لكل مستخدم/هدف حتى لا تتغير النتيجة كل مرة
    value = (abs(hash(f"{name}{update.effective_chat.id}")) % 101)

    await send(
        update,
        f"❤️ نسبة الحب بينك وبين {name}: {value}%",
    )


async def simple_fun(update, context, title):
    target = await get_target(update, context)

    if target:
        name = target.full_name
    else:
        name = update.effective_user.full_name

    await send(
        update,
        f"🎮 {title}\n\n"
        f"النتيجة على {name}: "
        f"{abs(hash(name + title)) % 101}%",
    )


# ============================================================
# إحصائيات
# ============================================================

async def stats(update, context):
    if not is_dev(update):
        await send(update, "❌ هذا الأمر للمطور فقط.")
        return

    users = len(DATA["users"])
    groups = len(DATA["groups"])

    await send(
        update,
        "📊 إحصائيات بوت لينا\n\n"
        f"👤 المستخدمون: {users}\n"
        f"👥 المجموعات: {groups}\n"
        f"🚫 الحظر العام: {len(DATA['global_ban'])}\n"
        f"🔇 الكتم العام: {len(DATA['global_mute'])}",
    )


# ============================================================
# لوحة المطور
# ============================================================

async def developer_panel(update, context):
    if not is_dev(update):
        await send(update, "❌ هذه اللوحة للمطور فقط.")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 الإحصائيات",
                callback_data="dev_stats",
            )
        ],
        [
            InlineKeyboardButton(
                "💬 الردود",
                callback_data="dev_replies",
            ),
            InlineKeyboardButton(
                "🎮 الألعاب",
                callback_data="dev_games",
            ),
        ],
        [
            InlineKeyboardButton(
                "⚙️ الإعدادات",
                callback_data="dev_settings",
            )
        ],
    ]

    await send(
        update,
        "👨‍💻 لوحة مطور بوت لينا\n\n"
        "من هنا يمكنك إدارة الميزات والردود والإحصائيات.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def developer_info(update, context):
    if not is_dev(update):
        return

    user = update.effective_user

    await send(
        update,
        "👨‍💻 معلومات المطور\n\n"
        f"الاسم: {user.full_name}\n"
        f"اليوزر: @{user.username or 'لا يوجد'}\n"
        f"الآيدي: `{user.id}`",
        parse_mode="Markdown",
    )


# ============================================================
# الأوامر العالمية
# ============================================================

async def global_ban(update, context):
    if not is_dev(update):
        await send(update, "❌ للمطور فقط.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    if target.id not in DATA["global_ban"]:
        DATA["global_ban"].append(target.id)

    save_data()

    await send(
        update,
        f"🌍 تم حظر {target.full_name} عالميًا.",
    )


async def global_unban(update, context):
    if not is_dev(update):
        await send(update, "❌ للمطور فقط.")
        return

    target = await get_target(update, context)

    if not target:
        await send(update, "❌ قم بالرد على العضو.")
        return

    if target.id in DATA["global_ban"]:
        DATA["global_ban"].remove(target.id)

    save_data()

    await send(update, "✅ تم فك الحظر العام.")


# ============================================================
# زر القائمة
# ============================================================

async def buttons(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "commands":
        await query.message.reply_text(COMMANDS_TEXT)

    elif query.data == "developer":
        await query.message.reply_text(
            "👨‍💻 مطور بوت لينا\n\n"
            f"آيدي المطور: {DEV_ID}"
        )

    elif query.data == "dev_stats":
        await stats(update, context)

    elif query.data == "dev_replies":
        await query.message.reply_text(
            "💬 إدارة الردود من داخل المجموعة:\n\n"
            "اضف رد الكلمة الرد\n"
            "اضف رد مميز الكلمة الرد\n"
            "حذف رد الكلمة\n"
            "الردود"
        )

    elif query.data == "dev_games":
        await query.message.reply_text(
            "🎮 قسم الألعاب قيد إدارة المطور."
        )

    elif query.data == "dev_settings":
        await query.message.reply_text(
            "⚙️ إعدادات المطور جاهزة."
        )


# ============================================================
# معالجة الأوامر العربية
# ============================================================

async def text_command_router(update, context):
    if not update.message or not update.message.text:
        return

    text = normalize(update.message.text)

    # الردود أولًا
    await automatic_replies(update, context)

    # رتبة
    if text == "رتبتي":
        await my_rank(update, context)
        return

    if text in ["معلوماتي", "معلوماتي الشخصيه"]:
        await my_info(update, context)
        return

    # الردود
    if text.startswith("اضف رد عام "):
        context.args = text.split()[3:]
        await add_reply(update, context, "normal")
        return

    if text.startswith("اضف رد مميز "):
        context.args = text.split()[3:]
        await add_reply(update, context, "special")
        return

    if text.startswith("اضف رد متعدد "):
        context.args = text.split()[3:]
        await add_reply(update, context, "multi")
        return

    if text.startswith("اضف رد "):
        context.args = text.split()[2:]
        await add_reply(update, context, "normal")
        return

    if text.startswith("حذف رد "):
        context.args = text.split()[2:]
        await delete_reply(update, context)
        return

    if text in ["الردود", "الردود العامه", "الردود المميزه"]:
        await show_replies(update, context)
        return

    # همسات
    if text.startswith("اهمس"):
        context.args = text.split()[1:]
        await whisper(update, context)
        return

    # قوانين
    if text == "القوانين":
        await rules(update, context)
        return

    if text.startswith("ضع قوانين "):
        context.args = text.split()[2:]
        await set_rules(update, context)
        return

    # الرابط
    if text == "الرابط":
        await group_link(update, context)
        return

    if text.startswith("ضع رابط "):
        context.args = text.split()[2:]
        await set_link(update, context)
        return

    if text == "حذف الرابط":
        await delete_link(update, context)
        return

    # الترحيب
    if text == "الترحيب":
        await welcome_status(update, context)
        return

    if text.startswith("ضع ترحيب "):
        context.args = text.split()[2:]
        await set_welcome(update, context)
        return

    # قفل
    if text.startswith("قفل "):
        context.args = text.split()[1:]
        await set_lock(update, context, True)
        return

    if text.startswith("فتح "):
        context.args = text.split()[1:]
        await set_lock(update, context, False)
        return

    # الإدارة
    if text == "حظر":
        await ban(update, context)
        return

    if text == "فك حظر":
        await unban(update, context)
        return

    if text == "طرد":
        await kick(update, context)
        return

    if text == "كتم":
        await mute(update, context)
        return

    if text == "فك كتم":
        await unmute(update, context)
        return

    if text == "مسح":
        await clear(update, context)
        return

    # الترفيه
    if text == "نسبة الحب":
        await love(update, context)
        return

    if text == "تحبه":
        await simple_fun(update, context, "تحبه")
        return

    if text == "هطف":
        await simple_fun(update, context, "هطف")
        return

    if text == "بثر":
        await simple_fun(update, context, "بثر")
        return

    if text == "حمار":
        await simple_fun(update, context, "حمار")
        return

    if text == "زواج":
        await simple_fun(update, context, "الزواج")
        return

    if text == "طلاق":
        await simple_fun(update, context, "الطلاق")
        return

    # لوحة المطور
    if text in ["لوحة المطور", "لوحه المطور"]:
        await developer_panel(update, context)
        return

    if text == "احصائيات":
        await stats(update, context)
        return

    if text == "حظر عام":
        await global_ban(update, context)
        return

    if text == "فك حظر عام":
        await global_unban(update, context)
        return


# ============================================================
# تسجيل الرتب بالأوامر
# ============================================================

async def promote_vip(update, context):
    await promote(update, context, "مميز")


async def demote_vip(update, context):
    await demote(update, context, "مميز")


async def promote_admin(update, context):
    await promote(update, context, "ادمن")


async def demote_admin(update, context):
    await demote(update, context, "ادمن")


async def promote_manager(update, context):
    await promote(update, context, "مدير")


async def demote_manager(update, context):
    await demote(update, context, "مدير")


async def promote_creator(update, context):
    await promote(update, context, "منشئ")


async def demote_creator(update, context):
    await demote(update, context, "منشئ")


async def promote_owner(update, context):
    await promote(update, context, "مالك")


async def demote_owner(update, context):
    await demote(update, context, "مالك")


async def promote_main_owner(update, context):
    await promote(update, context, "مالك اساسي")


async def demote_main_owner(update, context):
    await demote(update, context, "مالك اساسي")


# ============================================================
# تشغيل البوت
# ============================================================

def main():
    if not TOKEN:
        raise RuntimeError(
            "لم يتم العثور على BOT_TOKEN. "
            "أضف متغير BOT_TOKEN في Railway."
        )

    application = Application.builder().token(TOKEN).build()

    # Start
    application.add_handler(
        CommandHandler("start", start)
    )

    # الأوامر
    application.add_handler(
        CommandHandler("commands", commands)
    )

    # الرتب
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^رتبتي$"),
            my_rank,
        )
    )

    # أعضاء جدد
    application.add_handler(
        ChatMemberHandler(
            new_member,
            ChatMemberHandler.CHAT_MEMBER,
        )
    )

    # أزرار
    application.add_handler(
        CallbackQueryHandler(buttons)
    )

    # الرسائل الخاصة للهمسات
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT,
            whisper_private,
        ),
        group=5,
    )

    # مراقبة الأقفال
    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            lock_filter,
        ),
        group=10,
    )

    # الأوامر العربية
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
            text_command_router,
        ),
        group=20,
    )

    logger.info("Bot is starting...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
