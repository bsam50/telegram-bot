import os
import json
import random

from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# الإعدادات
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

# ID مالك البوت
OWNER_ID = 8476500086

if not TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Railway")

# =========================================================
# حفظ وتحميل البيانات
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
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


# =========================================================
# البيانات
# =========================================================

users = set(
    load_json("users.json", [])
)

groups = set(
    load_json("groups.json", [])
)

sudo_users = set(
    load_json("sudo_users.json", [])
)

reply_state = {}


# =========================================================
# الردود
# =========================================================

default_replies = {
    "السلام عليكم": [
        "وعليكم السلام ورحمة الله وبركاته"
    ],

    "سلام عليكم": [
        "وعليكم السلام ورحمة الله وبركاته"
    ],

    "كيفك": [
        "الحمد لله بخير وأنت😊"
    ],

    "كيف الحال": [
        "الحمد لله بخير وأنت😊"
    ],
}

replies = load_json(
    "replies.json",
    default_replies
)


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
    "😂 فيه واحد بخيل إذا عطس قال: الحمد لله... وخلاص.",
    "🤣 فيه واحد اشترى مروحة... زعل لأنها ما تطير.",
]


# =========================================================
# الصلاحيات
# =========================================================

def is_owner(user_id):
    return user_id == OWNER_ID


def is_sudo(user_id):
    return (
        user_id == OWNER_ID
        or user_id in sudo_users
    )


async def is_group_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.effective_chat:
        return False

    if update.effective_chat.type not in (
        "group",
        "supergroup"
    ):
        return False

    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )

        return member.status in (
            "administrator",
            "creator"
        )

    except Exception:
        return False


async def can_manage(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if is_sudo(update.effective_user.id):
        return True

    return await is_group_admin(
        update,
        context
    )


async def target_from_reply(update: Update):

    if (
        not update.message
        or not update.message.reply_to_message
    ):
        return None

    return update.message.reply_to_message.from_user


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    users.add(user_id)

    save_json(
        "users.json",
        list(users)
    )

    if update.effective_chat.type in (
        "group",
        "supergroup"
    ):

        groups.add(
            update.effective_chat.id
        )

        save_json(
            "groups.json",
            list(groups)
        )

    await update.message.reply_text(
        f"أهلاً وسهلاً {update.effective_user.first_name} 🌹\n"
        "نورت البوت ❤️"
    )


# =========================================================
# SUDO
# =========================================================

async def addsudo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    target = await target_from_reply(update)

    if target:

        user_id = target.id

    elif context.args:

        try:
            user_id = int(
                context.args[0]
            )

        except ValueError:

            await update.message.reply_text(
                "❌ أرسل ID صحيح."
            )

            return

    else:

        await update.message.reply_text(
            "👑 رد على رسالة المستخدم واكتب:\n"
            "/addsudo"
        )

        return

    sudo_users.add(user_id)

    save_json(
        "sudo_users.json",
        list(sudo_users)
    )

    await update.message.reply_text(
        f"👑 تم إضافة المستخدم {user_id} إلى قائمة المالكين المساعدين."
    )


async def delsudo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    target = await target_from_reply(update)

    if target:

        user_id = target.id

    elif context.args:

        try:
            user_id = int(
                context.args[0]
            )

        except ValueError:

            await update.message.reply_text(
                "❌ ID غير صحيح."
            )

            return

    else:

        await update.message.reply_text(
            "👑 رد على رسالة المستخدم واكتب:\n"
            "/delsudo"
        )

        return

    sudo_users.discard(user_id)

    save_json(
        "sudo_users.json",
        list(sudo_users)
    )

    await update.message.reply_text(
        "✅ تم إزالة المستخدم من قائمة المالكين المساعدين."
    )


async def listsudo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_sudo(
        update.effective_user.id
    ):
        return

    if not sudo_users:

        await update.message.reply_text(
            "لا يوجد مالكون مساعدون."
        )

        return

    text = "\n".join(
        str(x)
        for x in sudo_users
    )

    await update.message.reply_text(
        "👑 المالكين المساعدين:\n\n"
        + text
    )


# =========================================================
# أوامر الإدارة بالعربي
# =========================================================

async def arabic_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    text = (
        update.message.text
        .strip()
        .lower()
    )

    commands = [
        "حظر",
        "فك حظر",
        "طرد",
        "كتم",
        "فك كتم",
        "ترقية",
        "تنزيل",
        "تثبيت",
        "حذف",
    ]

    if text not in commands:
        return

    if update.effective_chat.type not in (
        "group",
        "supergroup"
    ):
        return

    if not await can_manage(
        update,
        context
    ):

        await update.message.reply_text(
            "❌ ليس لديك صلاحية لاستخدام أوامر الإدارة."
        )

        return

    target = await target_from_reply(update)

    # =====================================================
    # الحذف
    # =====================================================

    if text == "حذف":

        if not update.message.reply_to_message:

            await update.message.reply_text(
                "❌ رد على الرسالة التي تريد حذفها."
            )

            return

        try:

            await update.message.reply_to_message.delete()

            await update.message.delete()

        except Exception:
            pass

        return

    # =====================================================
    # باقي الأوامر تحتاج رد
    # =====================================================

    if not target:

        await update.message.reply_text(
            "❌ يجب أن ترد على رسالة العضو."
        )

        return

    # =====================================================
    # حماية المالك
    # =====================================================

    if target.id == OWNER_ID:

        if text in (
            "حظر",
            "طرد",
            "كتم",
            "تنزيل"
        ):

            await update.message.reply_text(
                "❌ لا يمكن تنفيذ هذا الأمر على مالك البوت."
            )

            return

    # =====================================================
    # حظر
    # =====================================================

    if text == "حظر":

        try:

            await context.bot.ban_chat_member(
                update.effective_chat.id,
                target.id
            )

            await update.message.reply_text(
                f"🚫 تم حظر {target.first_name}."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع حظر العضو.\n"
                f"{e}"
            )

    # =====================================================
    # فك الحظر
    # =====================================================

    elif text == "فك حظر":

        try:

            await context.bot.unban_chat_member(
                update.effective_chat.id,
                target.id,
                only_if_banned=True
            )

            await update.message.reply_text(
                f"✅ تم فك حظر {target.first_name}."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع فك الحظر.\n"
                f"{e}"
            )

    # =====================================================
    # طرد
    # =====================================================

    elif text == "طرد":

        try:

            await context.bot.ban_chat_member(
                update.effective_chat.id,
                target.id
            )

            await context.bot.unban_chat_member(
                update.effective_chat.id,
                target.id
            )

            await update.message.reply_text(
                f"👢 تم طرد {target.first_name}."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع طرد العضو.\n"
                f"{e}"
            )

    # =====================================================
    # كتم
    # =====================================================

    elif text == "كتم":

        try:

            permissions = ChatPermissions(
                can_send_messages=False
            )

            await context.bot.restrict_chat_member(
                update.effective_chat.id,
                target.id,
                permissions=permissions
            )

            await update.message.reply_text(
                f"🔇 تم كتم {target.first_name}."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع كتم العضو.\n"
                f"{e}"
            )

    # =====================================================
    # فك الكتم
    # =====================================================

    elif text == "فك كتم":

        try:

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
                can_add_web_page_previews=True
            )

            await context.bot.restrict_chat_member(
                update.effective_chat.id,
                target.id,
                permissions=permissions
            )

            await update.message.reply_text(
                f"🔊 تم فك كتم {target.first_name}."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع فك الكتم.\n"
                f"{e}"
            )

    # =====================================================
    # ترقية
    # =====================================================

    elif text == "ترقية":

        try:

            await context.bot.promote_chat_member(
                update.effective_chat.id,
                target.id,

                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )

            await update.message.reply_text(
                f"⬆️ تم ترقية {target.first_name} إلى مشرف."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع ترقية العضو.\n"
                f"{e}"
            )

    # =====================================================
    # تنزيل
    # =====================================================

    elif text == "تنزيل":

        try:

            await context.bot.promote_chat_member(
                update.effective_chat.id,
                target.id,

                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )

            await update.message.reply_text(
                f"⬇️ تم تنزيل {target.first_name} من الإشراف."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع تنزيل المشرف.\n"
                f"{e}"
            )

    # =====================================================
    # تثبيت
    # =====================================================

    elif text == "تثبيت":

        try:

            await update.message.reply_to_message.pin(
                disable_notification=False
            )

            await update.message.reply_text(
                "📌 تم تثبيت الرسالة."
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ لم أستطع تثبيت الرسالة.\n"
                f"{e}"
            )


# =========================================================
# إضافة الردود
# =========================================================

async def addreply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    reply_state[
        update.effective_user.id
    ] = {
        "step": "question"
    }

    await update.message.reply_text(
        "✏️ أرسل الكلمة أو السؤال الذي تريد إضافة رد له."
    )


async def delreply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    key = " ".join(
        context.args
    ).lower()

    if key in replies:

        del replies[key]

        save_json(
            "replies.json",
            replies
        )

        await update.message.reply_text(
            "🗑 تم حذف الرد."
        )

    else:

        await update.message.reply_text(
            "❌ الرد غير موجود."
        )


async def listreply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    if not replies:

        await update.message.reply_text(
            "لا توجد ردود."
        )

        return

    text = "\n".join(
        replies.keys()
    )

    await update.message.reply_text(
        "📝 الردود:\n\n"
        + text
    )


# =========================================================
# الردود التلقائية والنكت
# =========================================================

async def reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    user_id = update.effective_user.id

    text = (
        update.message.text
        .strip()
        .lower()
    )

    # إضافة رد جديد
    if user_id in reply_state:

        state = reply_state[user_id]

        if state["step"] == "question":

            state["question"] = text
            state["step"] = "answer"

            await update.message.reply_text(
                "💬 الآن أرسل الرد."
            )

            return

        elif state["step"] == "answer":

            question = state["question"]

            if question not in replies:
                replies[question] = []

            replies[question].append(text)

            save_json(
                "replies.json",
                replies
            )

            del reply_state[user_id]

            await update.message.reply_text(
                "✅ تم حفظ الرد."
            )

            return

    # النكت
    if text in (
        "نكته",
        "نكتة",
        "ضحكني"
    ):

        await update.message.reply_text(
            random.choice(jokes)
        )

        return

    # الردود
    if text in replies:

        answer = replies[text]

        if isinstance(answer, list):

            await update.message.reply_text(
                random.choice(answer)
            )

        else:

            await update.message.reply_text(
                str(answer)
            )


# =========================================================
# الإحصائيات
# =========================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    await update.message.reply_text(
        f"👥 عدد المستخدمين: {len(users)}\n"
        f"👨‍👩‍👧‍👦 عدد المجموعات: {len(groups)}\n"
        f"👑 عدد المالكين المساعدين: {len(sudo_users)}"
    )


# =========================================================
# المستخدمون
# =========================================================

async def userscmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    if not users:

        await update.message.reply_text(
            "لا يوجد مستخدمون."
        )

        return

    text = "\n".join(
        str(user)
        for user in users
    )

    await update.message.reply_text(
        "👥 المستخدمون:\n\n"
        + text
    )


# =========================================================
# البث
# =========================================================

async def broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    if not context.args:

        await update.message.reply_text(
            "الاستخدام:\n"
            "/broadcast الرسالة"
        )

        return

    message = " ".join(
        context.args
    )

    sent = 0

    for user in users:

        try:

            await context.bot.send_message(
                chat_id=user,
                text=message
            )

            sent += 1

        except Exception:
            pass

    await update.message.reply_text(
        f"✅ تم إرسال الرسالة إلى {sent} مستخدم."
    )


# =========================================================
# إضافة نكتة
# =========================================================

async def addjoke(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    if not context.args:

        await update.message.reply_text(
            "الاستخدام:\n"
            "/addjoke النكتة"
        )

        return

    joke = " ".join(
        context.args
    )

    jokes.append(joke)

    await update.message.reply_text(
        "✅ تم إضافة النكتة."
    )


# =========================================================
# المساعدة
# =========================================================

async def helpcmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        """
🤖 أوامر البوت

👑 أوامر المالك:

/addsudo
/delsudo
/listsudo

/stats
/users
/broadcast
/addreply
/delreply
/listreply
/addjoke

🛡️ أوامر الإدارة بالعربي:

🚫 حظر
✅ فك حظر
👢 طرد
🔇 كتم
🔊 فك كتم
⬆️ ترقية
⬇️ تنزيل
📌 تثبيت
🗑 حذف

📌 طريقة الاستخدام:

رد على رسالة العضو ثم اكتب الأمر.

مثال:

حظر

أو:

كتم

أو:

ترقية

⚠️ يجب أن يكون البوت مشرفًا في المجموعة
ولديه الصلاحيات المطلوبة.
"""
    )


# =========================================================
# تشغيل البوت
# =========================================================

app = Application.builder().token(TOKEN).build()


# البداية
app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


# SUDO
app.add_handler(
    CommandHandler(
        "addsudo",
        addsudo
    )
)

app.add_handler(
    CommandHandler(
        "delsudo",
        delsudo
    )
)

app.add_handler(
    CommandHandler(
        "listsudo",
        listsudo
    )
)


# الردود
app.add_handler(
    CommandHandler(
        "addreply",
        addreply
    )
)

app.add_handler(
    CommandHandler(
        "delreply",
        delreply
    )
)

app.add_handler(
    CommandHandler(
        "listreply",
        listreply
    )
)


# الإحصائيات والبث
app.add_handler(
    CommandHandler(
        "stats",
        stats
    )
)

app.add_handler(
    CommandHandler(
        "users",
        userscmd
    )
)

app.add_handler(
    CommandHandler(
        "broadcast",
        broadcast
    )
)

app.add_handler(
    CommandHandler(
        "addjoke",
        addjoke
    )
)


# المساعدة
app.add_handler(
    CommandHandler(
        "help",
        helpcmd
    )
)


# =========================================================
# مهم:
# أوامر الإدارة العربية قبل الردود العادية
# =========================================================

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        arabic_admin
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        reply
    )
)


print("🤖 البوت يعمل الآن...")

app.run_polling()
