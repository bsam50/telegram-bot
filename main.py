import os
import json
import random
import logging
from datetime import timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في متغيرات البيئة")

# =========================================================
# الملفات
# =========================================================

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


users = set(load_json("users.json", []))
groups = set(load_json("groups.json", []))

replies = load_json(
    "replies.json",
    {
        "السلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
        "سلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
        "كيفك": ["الحمد لله بخير وأنت 😊"],
        "كيف الحال": ["الحمد لله بخير وأنت 😊"],
    },
)

# الرتب الخاصة بكل مجموعة
ranks = load_json("ranks.json", {})

# التحذيرات
warnings = load_json("warnings.json", {})

# إعدادات بسيطة
settings = load_json("settings.json", {})

# حالة إضافة الرد
reply_state = {}


# =========================================================
# النكت
# =========================================================

jokes = [
    "😂 فيه اثنين مشوا سوا... رجعوا موبايلي.",
    "🤣 فيه نملة ماسكة عود أسنان... ليه؟ ترقص إماراتي.",
    "😂 فيه نملة ماسكة ملعقة... ليه؟ داخلة معركة.",
    "🤣 فيه واحد اسمه سامي كبر... صار سماوي.",
    "😂 فيه وحدة اسمها سارة كبرت... صارت سيارة.",
    "🤣 فيه واحد اسمه سالم طاح... صار مصاب.",
    "😂 فيه واحد اسمه خالد مات... صار خالد الذكر.",
    "🤣 فيه بطة لابسة نظارة... ليه؟ تشوف البط أوضح.",
    "😂 فيه دجاجة راحت المحكمة... تبي تبيض وجهها.",
    "🤣 فيه سمكة طلعت البر... قالت: يا ليتني ما طلعت.",
    "😂 فيه واحد دخل مطعم وسأل: عندكم رز؟ قالوا: نعم، قال: سلموا عليه.",
    "🤣 فيه واحد راح للدكتور قال: كل ما أشرب شاي توجعني عيني، قال: شيل الملعقة من الكوب.",
]


# =========================================================
# الرتب
# =========================================================

RANKS = [
    "مالك اساسي",
    "مالك",
    "منشئ",
    "مدير",
    "ادمن",
    "مميز",
]

RANK_LEVEL = {
    "عضو": 0,
    "مميز": 1,
    "ادمن": 2,
    "مدير": 3,
    "منشئ": 4,
    "مالك": 5,
    "مالك اساسي": 6,
}


def group_key(chat_id):
    return str(chat_id)


def get_group_ranks(chat_id):
    key = group_key(chat_id)

    if key not in ranks:
        ranks[key] = {
            "مالك اساسي": [],
            "مالك": [],
            "منشئ": [],
            "مدير": [],
            "ادمن": [],
            "مميز": [],
        }

    return ranks[key]


def save_ranks():
    save_json("ranks.json", ranks)


def get_user_rank(chat_id, user_id):
    # المالك الأساسي العام
    if user_id == OWNER_ID:
        return "مالك اساسي"

    data = get_group_ranks(chat_id)

    for rank in RANKS:
        if user_id in data.get(rank, []):
            return rank

    return "عضو"


def rank_level(rank):
    return RANK_LEVEL.get(rank, 0)


def can_manage(chat_id, user_id, required_rank="ادمن"):
    user_rank = get_user_rank(chat_id, user_id)
    return rank_level(user_rank) >= rank_level(required_rank)


# =========================================================
# التحقق من المشرف الحقيقي في تيليجرام
# =========================================================

async def is_real_admin(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not chat or chat.type not in ("group", "supergroup"):
        return False

    if user.id == OWNER_ID:
        return True

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def bot_is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            context.bot.id,
        )
        return member.status in ("administrator", "creator")
    except Exception:
        return False


# =========================================================
# معرفة العضو المستهدف بالرد
# =========================================================

async def get_target(update):
    if not update.message:
        return None

    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user

    return None


# =========================================================
# /start
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    users.add(user.id)
    save_json("users.json", list(users))

    if chat.type in ("group", "supergroup"):
        groups.add(chat.id)
        save_json("groups.json", list(groups))

    await update.message.reply_text(
        f"أهلاً وسهلاً {user.first_name} 🌹\n"
        "نورت البوت ❤️\n\n"
        "اكتب: الاوامر"
    )


# =========================================================
# قائمة الأوامر الرئيسية
# =========================================================

async def commands_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "⚠️ هذا الأمر خاص بالمجموعات."
        )
        return

    rank = get_user_rank(chat.id, user.id)

    if rank_level(rank) >= 2:
        text = """
‌‌‏أهلاً بك عزيزي في قائمة الاوامر :
━━━━━━━━━━━━
◂ م1 : اوامر الادمنيه
◂ م2 : اوامر الاعدادات
◂ م3 : اوامر القفل - الفتح
◂ م4 : اوامر التسليه
◂ م6 : الاوامر الخدميه
━━━━━━━━━━━━
"""
    else:
        text = """
‌‌‏أهلاً بك عزيزي في قائمة الاوامر :
━━━━━━━━━━━━
◂ م4 : اوامر التسليه
◂ م6 : الاوامر الخدميه
━━━━━━━━━━━━
"""

    await update.message.reply_text(text)


# =========================================================
# م1
# =========================================================

async def m1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        return

    rank = get_user_rank(chat.id, user.id)

    if rank_level(rank) < 2:
        await update.message.reply_text(
            "❌ هذا القسم خاص بالأدمنية والمشرفين."
        )
        return

    text = """
👮 قائمة اوامر الادمنيه
━━━━━━━━━━━━

• اوامر الرفع والتنزيل :

رفع / تنزيل مالك اساسي
رفع / تنزيل مالك
رفع / تنزيل منشئ
رفع / تنزيل مدير
رفع / تنزيل ادمن
رفع / تنزيل مميز
تنزيل الكل

• اوامر المسح :

مسح الكل
مسح المنشئين
مسح المدراء
مسح المالكين
مسح الادمنيه
مسح المميزين
مسح المحظورين
مسح المكتومين
مسح قائمه المنع
مسح الردود
مسح الاوامر المضافه
مسح + عدد
مسح بالرد
مسح الايدي
مسح الترحيب
مسح الرابط

• اوامر الطرد والحظر :

تقييد
حظر
طرد
كتم
الغاء الحظر
الغاء الكتم
فك التقييد
رفع القيود
منع بالرد
الغاء منع بالرد
طرد البوتات
طرد المحذوفين
كشف البوتات
━━━━━━━━━━━━
"""

    await update.message.reply_text(text)


# =========================================================
# رفع رتبة
# =========================================================

async def promote_rank(update, context, rank):
    chat = update.effective_chat
    user = update.effective_user

    if rank not in RANKS:
        return

    if not can_manage(chat.id, user.id, rank):
        await update.message.reply_text(
            "❌ رتبتك لا تسمح لك برفع هذه الرتبة."
        )
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد على رسالة الشخص."
        )
        return

    if target.id == user.id:
        await update.message.reply_text(
            "❌ لا يمكنك رفع رتبتك بنفسك."
        )
        return

    target_rank = get_user_rank(chat.id, target.id)

    if rank_level(target_rank) >= rank_level(rank):
        await update.message.reply_text(
            "❌ رتبة الشخص أعلى أو مساوية لهذه الرتبة."
        )
        return

    data = get_group_ranks(chat.id)

    # إزالة العضو من جميع الرتب
    for r in RANKS:
        if target.id in data[r]:
            data[r].remove(target.id)

    data[rank].append(target.id)
    save_ranks()

    await update.message.reply_text(
        f"✅ تم رفع {target.first_name} إلى رتبة: {rank}"
    )


# =========================================================
# تنزيل رتبة
# =========================================================

async def demote_rank(update, context, rank):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, rank):
        await update.message.reply_text(
            "❌ رتبتك لا تسمح لك بتنزيل هذه الرتبة."
        )
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد على رسالة الشخص."
        )
        return

    target_rank = get_user_rank(chat.id, target.id)

    if target_rank != rank:
        await update.message.reply_text(
            f"❌ الشخص ليس برتبة {rank}."
        )
        return

    data = get_group_ranks(chat.id)
    data[rank].remove(target.id)

    save_ranks()

    await update.message.reply_text(
        f"✅ تم تنزيل رتبة {target.first_name}."
    )


# =========================================================
# حظر
# =========================================================

async def ban_user(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد على رسالة العضو."
        )
        return

    if rank_level(get_user_rank(chat.id, target.id)) >= rank_level(
        get_user_rank(chat.id, user.id)
    ):
        await update.message.reply_text(
            "❌ لا يمكنك تنفيذ الأمر على شخص رتبته مساوية أو أعلى."
        )
        return

    if not await bot_is_admin(update, context):
        await update.message.reply_text(
            "❌ يجب أن يكون البوت مشرفًا."
        )
        return

    try:
        await context.bot.ban_chat_member(
            chat_id=chat.id,
            user_id=target.id,
        )

        await update.message.reply_text(
            f"🚫 تم حظر {target.first_name}"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ لم أستطع حظر العضو.\n{e}"
        )


# =========================================================
# فك الحظر
# =========================================================

async def unban_user(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد على رسالة العضو."
        )
        return

    try:
        await context.bot.unban_chat_member(
            chat_id=chat.id,
            user_id=target.id,
            only_if_banned=True,
        )

        await update.message.reply_text(
            f"✅ تم فك حظر {target.first_name}"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ تعذر فك الحظر.\n{e}"
        )


# =========================================================
# طرد
# =========================================================

async def kick_user(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد."
        )
        return

    try:
        await context.bot.ban_chat_member(
            chat.id,
            target.id,
        )

        await context.bot.unban_chat_member(
            chat.id,
            target.id,
        )

        await update.message.reply_text(
            f"👢 تم طرد {target.first_name}"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ تعذر طرد العضو.\n{e}"
        )


# =========================================================
# كتم
# =========================================================

async def mute_user(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد."
        )
        return

    try:
        from telegram import ChatPermissions

        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
            ),
        )

        await update.message.reply_text(
            f"🔇 تم كتم {target.first_name}"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ تعذر كتم العضو.\n{e}"
        )


# =========================================================
# فك الكتم
# =========================================================

async def unmute_user(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد."
        )
        return

    try:
        from telegram import ChatPermissions

        await context.bot.restrict_chat_member(
            chat.id,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )

        await update.message.reply_text(
            f"🔊 تم فك كتم {target.first_name}"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ تعذر فك الكتم.\n{e}"
        )


# =========================================================
# تحذير
# =========================================================

async def warn_user(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد."
        )
        return

    key = f"{chat.id}:{target.id}"

    warnings[key] = warnings.get(key, 0) + 1
    save_json("warnings.json", warnings)

    count = warnings[key]

    if count >= 3:
        try:
            await context.bot.ban_chat_member(
                chat.id,
                target.id,
            )

            warnings[key] = 0
            save_json("warnings.json", warnings)

            await update.message.reply_text(
                f"🚫 {target.first_name} وصل إلى 3 تحذيرات وتم حظره."
            )
            return
        except Exception:
            pass

    await update.message.reply_text(
        f"⚠️ تم تحذير {target.first_name}\n"
        f"عدد التحذيرات: {count}/3"
    )


# =========================================================
# مسح التحذيرات
# =========================================================

async def clear_warn(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    target = await get_target(update)

    if not target:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد."
        )
        return

    key = f"{chat.id}:{target.id}"

    warnings[key] = 0
    save_json("warnings.json", warnings)

    await update.message.reply_text(
        f"✅ تم مسح تحذيرات {target.first_name}"
    )


# =========================================================
# حذف رسالة بالرد
# =========================================================

async def delete_reply(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد على الرسالة."
        )
        return

    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()
    except Exception as e:
        await update.message.reply_text(
            f"❌ تعذر حذف الرسالة.\n{e}"
        )


# =========================================================
# تثبيت
# =========================================================

async def pin_message(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "مدير"):
        await update.message.reply_text(
            "❌ تحتاج رتبة مدير أو أعلى."
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ استخدم الأمر بالرد على الرسالة."
        )
        return

    try:
        await update.message.reply_to_message.pin(
            disable_notification=False
        )

        await update.message.reply_text("📌 تم تثبيت الرسالة.")
    except Exception as e:
        await update.message.reply_text(
            f"❌ تعذر التثبيت.\n{e}"
        )


# =========================================================
# تنزيل الكل
# =========================================================

async def demote_all(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "مالك"):
        await update.message.reply_text(
            "❌ تحتاج رتبة مالك."
        )
        return

    data = get_group_ranks(chat.id)

    for rank in RANKS:
        if rank != "مالك اساسي":
            data[rank] = []

    save_ranks()

    await update.message.reply_text(
        "✅ تم تنزيل جميع الرتب التي يسمح لك بتنزيلها."
    )


# =========================================================
# عرض الرتب
# =========================================================

async def show_ranks(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if not can_manage(chat.id, user.id, "ادمن"):
        await update.message.reply_text(
            "❌ هذا الأمر للأدمنية فقط."
        )
        return

    data = get_group_ranks(chat.id)

    text = "👑 رتب المجموعة\n━━━━━━━━━━━━\n"

    for rank in RANKS:
        ids = data.get(rank, [])

        text += f"\n{rank}: {len(ids)}"

        for uid in ids[:20]:
            try:
                member = await context.bot.get_chat_member(
                    chat.id,
                    uid,
                )
                name = member.user.first_name
                text += f"\n  • {name}"
            except Exception:
                text += f"\n  • {uid}"

    await update.message.reply_text(text)


# =========================================================
# م4
# =========================================================

async def m4(update, context):
    await update.message.reply_text(
        """
🎮 اوامر التسليه
━━━━━━━━━━━━

• رفع هطف
• تنزيل هطف
• رفع بثر
• تنزيل بثر
• رفع حمار
• تنزيل حمار
• رفع كلب
• تنزيل كلب
• رفع كلبه
• تنزيل كلبه
• رفع عتوي
• تنزيل عتوي
• رفع لحجي
• تنزيل لحجي
• رفع خروف
• تنزيل خروف

• طلاق
• زواج
• زوجي
• زوجتي
• تتزوجني

• اكتموه
━━━━━━━━━━━━
"""
    )


# =========================================================
# م6
# =========================================================

async def m6(update, context):
    await update.message.reply_text(
        """
🧰 الاوامر الخدميه
━━━━━━━━━━━━

• نسبة الحب
• تحبه
• شبيهي
• شبيهتي
• شرايك في افتاري
• افتاره
• البايو
• قوقل + البحث
• تطبيق + اسم التطبيق
• تحميل لعبة + اسم اللعبة
• قران
• اذكار
• شعر
• قصائد
• اقتباسات
• ثريد
• قصص
• كتب
• من ضافني
• اضف رد انلاين
• اضف رد متعدد
━━━━━━━━━━━━
"""
    )


# =========================================================
# الردود
# =========================================================

async def addreply(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    reply_state[update.effective_user.id] = {
        "step": "question"
    }

    await update.message.reply_text(
        "✏️ أرسل الكلمة أو السؤال."
    )


async def delreply(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    key = " ".join(context.args).lower()

    if key in replies:
        del replies[key]
        save_json("replies.json", replies)

        await update.message.reply_text(
            "🗑 تم حذف الرد."
        )
    else:
        await update.message.reply_text(
            "❌ الرد غير موجود."
        )


async def listreply(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    if not replies:
        await update.message.reply_text(
            "لا توجد ردود."
        )
        return

    text = "\n".join(replies.keys())

    await update.message.reply_text(
        "📋 الردود:\n\n" + text
    )


# =========================================================
# الردود التلقائية
# =========================================================

async def reply_handler(update, context):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if user_id in reply_state:

        state = reply_state[user_id]

        if state["step"] == "question":
            state["question"] = text
            state["step"] = "answer"

            await update.message.reply_text(
                "💬 الآن أرسل الرد."
            )
            return

        if state["step"] == "answer":
            question = state["question"]

            if question not in replies:
                replies[question] = []

            replies[question].append(text)

            save_json("replies.json", replies)

            del reply_state[user_id]

            await update.message.reply_text(
                "✅ تم حفظ الرد."
            )
            return

    if text in ("نكته", "نكتة", "ضحكني"):
        await update.message.reply_text(
            random.choice(jokes)
        )
        return

    if text in replies:
        await update.message.reply_text(
            random.choice(replies[text])
        )


# =========================================================
# إحصائيات
# =========================================================

async def stats(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text(
        f"📊 عدد المستخدمين: {len(users)}\n"
        f"📊 عدد المجموعات: {len(groups)}"
    )


# =========================================================
# المستخدمون
# =========================================================

async def userscmd(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    if not users:
        await update.message.reply_text(
            "لا يوجد مستخدمون."
        )
        return

    text = "\n".join(str(user) for user in users)

    await update.message.reply_text(
        f"👥 المستخدمون:\n\n{text}"
    )


# =========================================================
# البث
# =========================================================

async def broadcast(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/broadcast الرسالة"
        )
        return

    message = " ".join(context.args)

    sent = 0

    for user in list(users):
        try:
            await context.bot.send_message(
                chat_id=user,
                text=message,
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ تم إرسال الرسالة إلى {sent} مستخدم."
    )


# =========================================================
# المساعدة
# =========================================================

async def helpcmd(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text(
        """
👑 أوامر المالك:

/addreply
/delreply
/listreply
/stats
/users
/broadcast

وفي المجموعات:

الاوامر
م1
م4
م6
"""
    )


# =========================================================
# معالجة الأوامر العربية
# =========================================================

async def text_commands(update, context):

    if not update.message or not update.message.text:
        return

    text = update.message.text.strip().lower()

    # القائمة
    if text in ("الاوامر", "الـاوامر"):
        await commands_menu(update, context)
        return

    if text in ("م1", "م 1"):
        await m1(update, context)
        return

    if text in ("م4", "م 4"):
        await m4(update, context)
        return

    if text in ("م6", "م 6"):
        await m6(update, context)
        return

    # عرض الرتب
    if text in ("الرتب", "المشرفين"):
        await show_ranks(update, context)
        return

    # -----------------------------------------------------
    # رفع الرتب
    # -----------------------------------------------------

    for rank in RANKS:

        if text == f"رفع {rank}":
            await promote_rank(
                update,
                context,
                rank,
            )
            return

        if text == f"تنزيل {rank}":
            await demote_rank(
                update,
                context,
                rank,
            )
            return

    if text == "تنزيل الكل":
        await demote_all(update, context)
        return

    # -----------------------------------------------------
    # الإدارة
    # -----------------------------------------------------

    if text == "حظر":
        await ban_user(update, context)
        return

    if text in ("الغاء الحظر", "فك الحظر"):
        await unban_user(update, context)
        return

    if text == "طرد":
        await kick_user(update, context)
        return

    if text == "كتم":
        await mute_user(update, context)
        return

    if text in ("الغاء الكتم", "فك الكتم"):
        await unmute_user(update, context)
        return

    if text in ("تحذير", "انذار"):
        await warn_user(update, context)
        return

    if text in ("مسح التحذيرات", "مسح التحذير"):
        await clear_warn(update, context)
        return

    if text in ("حذف", "مسح بالرد"):
        await delete_reply(update, context)
        return

    if text in ("تثبيت", "ثبت"):
        await pin_message(update, context)
        return


# =========================================================
# تشغيل البوت
# =========================================================

def main():

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # أوامر Telegram
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("addreply", addreply)
    )

    app.add_handler(
        CommandHandler("delreply", delreply)
    )

    app.add_handler(
        CommandHandler("listreply", listreply)
    )

    app.add_handler(
        CommandHandler("stats", stats)
    )

    app.add_handler(
        CommandHandler("users", userscmd)
    )

    app.add_handler(
        CommandHandler("broadcast", broadcast)
    )

    app.add_handler(
        CommandHandler("help", helpcmd)
    )

    # الأوامر العربية
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_commands,
        ),
        group=0,
    )

    # الردود التلقائية
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            reply_handler,
        ),
        group=1,
    )

    print("Bot is running...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
