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
OWNER_ID = 8476500086

if not TOKEN:
    raise RuntimeError("ضع BOT_TOKEN في متغيرات Railway")

# =========================================================
# التخزين
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

sudo_users = set(load_json("sudo_users.json", []))

replies = {
    "السلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
    "سلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
    "كيفك": ["الحمد لله بخير وأنت😊"],
    "كيف الحال": ["الحمد لله بخير وأنت😊"],
}

replies = load_json("replies.json", replies)

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
]

# =========================================================
# الصلاحيات
# =========================================================

def is_owner(user_id):
    return user_id == OWNER_ID


def is_sudo(user_id):
    return user_id in sudo_users or is_owner(user_id)


async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return False

    if update.effective_chat.type not in ("group", "supergroup"):
        return False

    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id,
    )

    return member.status in ("administrator", "creator")


async def can_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_sudo(update.effective_user.id):
        return True

    return await is_group_admin(update, context)


async def target_from_reply(update: Update):
    if not update.message or not update.message.reply_to_message:
        return None

    return update.message.reply_to_message.from_user


# =========================================================
# البداية
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    users.add(user_id)
    save_json("users.json", list(users))

    if update.effective_chat.type in ("group", "supergroup"):
        groups.add(update.effective_chat.id)
        save_json("groups.json", list(groups))

    await update.message.reply_text(
        f"أهلاً وسهلاً {update.effective_user.first_name} 🌹\n"
        "نورت البوت ❤️"
    )


# =========================================================
# SUDO
# =========================================================

async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    target = await target_from_reply(update)

    if target:
        user_id = target.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ أرسل ID صحيح.")
            return
    else:
        await update.message.reply_text(
            "استخدم الأمر بالرد على المستخدم:\n/addsudo\n\n"
            "أو:\n/addsudo USER_ID"
        )
        return

    sudo_users.add(user_id)
    save_json("sudo_users.json", list(sudo_users))

    await update.message.reply_text(
        f"👑 تم إضافة المستخدم {user_id} إلى SUDO."
    )


async def delsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    target = await target_from_reply(update)

    if target:
        user_id = target.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ أرسل ID صحيح.")
            return
    else:
        await update.message.reply_text(
            "استخدم الأمر بالرد على المستخدم:\n/delsudo"
        )
        return

    sudo_users.discard(user_id)
    save_json("sudo_users.json", list(sudo_users))

    await update.message.reply_text(
        f"✅ تم إزالة المستخدم {user_id} من SUDO."
    )


async def listsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return

    if not sudo_users:
        await update.message.reply_text("لا يوجد SUDO.")
        return

    text = "\n".join(str(x) for x in sudo_users)

    await update.message.reply_text(
        "👑 قائمة SUDO:\n\n" + text
    )


# =========================================================
# الحظر
# =========================================================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    target = await target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "❌ رد على رسالة المستخدم واكتب /ban"
        )
        return

    if target.id == OWNER_ID:
        await update.message.reply_text("❌ لا يمكن حظر المالك.")
        return

    try:
        await context.bot.ban_chat_member(
            update.effective_chat.id,
            target.id,
        )

        await update.message.reply_text(
            f"🚫 تم حظر {target.first_name}."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ لم أستطع حظر المستخدم.\n{e}"
        )


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    target = await target_from_reply(update)

    if target:
        user_id = target.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID غير صحيح.")
            return
    else:
        await update.message.reply_text(
            "استخدم /unban بالرد على المستخدم أو مع ID."
        )
        return

    try:
        await context.bot.unban_chat_member(
            update.effective_chat.id,
            user_id,
            only_if_banned=True,
        )

        await update.message.reply_text("✅ تم فك الحظر.")

    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ:\n{e}"
        )


# =========================================================
# الطرد
# =========================================================

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    target = await target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "❌ رد على رسالة المستخدم واكتب /kick"
        )
        return

    if target.id == OWNER_ID:
        await update.message.reply_text("❌ لا يمكن طرد المالك.")
        return

    try:
        await context.bot.ban_chat_member(
            update.effective_chat.id,
            target.id,
        )

        await context.bot.unban_chat_member(
            update.effective_chat.id,
            target.id,
        )

        await update.message.reply_text(
            f"👢 تم طرد {target.first_name}."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ لم أستطع طرد المستخدم.\n{e}"
        )


# =========================================================
# الكتم
# =========================================================

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    target = await target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "❌ رد على رسالة المستخدم واكتب /mute"
        )
        return

    permissions = ChatPermissions(
        can_send_messages=False
    )

    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target.id,
            permissions=permissions,
        )

        await update.message.reply_text(
            f"🔇 تم كتم {target.first_name}."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ لم أستطع كتم المستخدم.\n{e}"
        )


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    target = await target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "❌ رد على رسالة المستخدم واكتب /unmute"
        )
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
            update.effective_chat.id,
            target.id,
            permissions=permissions,
        )

        await update.message.reply_text(
            f"🔊 تم فك كتم {target.first_name}."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ.\n{e}"
        )


# =========================================================
# المشرفون
# =========================================================

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    target = await target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "❌ رد على رسالة المستخدم واكتب /promote"
        )
        return

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
            can_pin_messages=True,
        )

        await update.message.reply_text(
            f"⬆️ تم ترقية {target.first_name} إلى مشرف."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ لم أستطع ترقية المستخدم.\n{e}"
        )


async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    target = await target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "❌ رد على رسالة المستخدم واكتب /demote"
        )
        return

    if target.id == OWNER_ID:
        await update.message.reply_text(
            "❌ لا يمكن تنزيل المالك."
        )
        return

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
            can_pin_messages=False,
        )

        await update.message.reply_text(
            f"⬇️ تم تنزيل {target.first_name}."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ.\n{e}"
        )


# =========================================================
# التثبيت والحذف
# =========================================================

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ رد على الرسالة التي تريد تثبيتها."
        )
        return

    try:
        await update.message.reply_to_message.pin(
            disable_notification=False
        )

        await update.message.reply_text("📌 تم تثبيت الرسالة.")

    except Exception as e:
        await update.message.reply_text(
            f"❌ لم أستطع التثبيت.\n{e}"
        )


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_manage(update, context):
        return

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


# =========================================================
# الردود
# =========================================================

async def addreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    reply_state[update.effective_user.id] = {
        "step": "question"
    }

    await update.message.reply_text(
        "✏️ أرسل الكلمة أو السؤال الذي تريد إضافة رد له."
    )


async def delreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    key = " ".join(context.args).lower()

    if key in replies:
        del replies[key]
        save_json("replies.json", replies)

        await update.message.reply_text("🗑 تم حذف الرد.")
    else:
        await update.message.reply_text("❌ الرد غير موجود.")


async def listreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not replies:
        await update.message.reply_text("لا توجد ردود.")
        return

    text = "\n".join(replies.keys())

    await update.message.reply_text(
        "الردود:\n\n" + text
    )


# =========================================================
# الرسائل والردود
# =========================================================

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if text in ["نكته", "نكتة", "ضحكني"]:
        await update.message.reply_text(
            random.choice(jokes)
        )
        return

    if text in replies:
        await update.message.reply_text(
            random.choice(replies[text])
        )


# =========================================================
# الإحصائيات والبث
# =========================================================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    await update.message.reply_text(
        f"عدد المستخدمين: {len(users)}\n"
        f"عدد المجموعات: {len(groups)}"
    )


async def userscmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not users:
        await update.message.reply_text(
            "لا يوجد مستخدمون."
        )
        return

    text = "\n".join(str(user) for user in users)

    await update.message.reply_text(
        f"المستخدمون:\n\n{text}"
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/broadcast الرسالة"
        )
        return

    message = " ".join(context.args)

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

async def addjoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/addjoke النكتة"
        )
        return

    joke = " ".join(context.args)
    jokes.append(joke)

    await update.message.reply_text(
        "✅ تم إضافة النكتة."
    )


# =========================================================
# المساعدة
# =========================================================

async def helpcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
🤖 أوامر البوت:

👑 المالك:
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

🛡️ الإدارة:
 /ban
 /unban
 /kick
 /mute
 /unmute
 /promote
 /demote
 /pin
 /delete

📌 استخدم أوامر الإدارة بالرد على رسالة العضو.
"""
    )


# =========================================================
# تشغيل البوت
# =========================================================

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(CommandHandler("addsudo", addsudo))
app.add_handler(CommandHandler("delsudo", delsudo))
app.add_handler(CommandHandler("listsudo", listsudo))

app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CommandHandler("kick", kick))

app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("unmute", unmute))

app.add_handler(CommandHandler("promote", promote))
app.add_handler(CommandHandler("demote", demote))

app.add_handler(CommandHandler("pin", pin))
app.add_handler(CommandHandler("delete", delete))

app.add_handler(CommandHandler("addreply", addreply))
app.add_handler(CommandHandler("delreply", delreply))
app.add_handler(CommandHandler("listreply", listreply))

app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("users", userscmd))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("addjoke", addjoke))
app.add_handler(CommandHandler("help", helpcmd))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        reply
    )
)

print("Bot started...")

app.run_polling()
