from telegram import ChatPermissions
from telegram.ext import MessageHandler, filters
from database import set_rank, remove_rank, connect
from ranks import get_rank, LEVELS, can_promote

RANK_NAMES = set(LEVELS) - {"عضو"}

async def target(update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None

async def rank_cmd(update, context, owner_id):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    parts = update.message.text.strip().split()
    if len(parts) != 2 or parts[0] not in ("رفع", "تنزيل"):
        return
    rank = parts[1]
    if rank not in RANK_NAMES:
        return
    t = await target(update)
    if not t:
        await update.message.reply_text("⚠️ استخدم الأمر بالرد على العضو.")
        return
    actor = await get_rank(context.bot, update.effective_chat.id,
                           update.effective_user.id, owner_id)
    target_rank = await get_rank(context.bot, update.effective_chat.id,
                                 t.id, owner_id)
    if not can_promote(actor, target_rank, rank):
        await update.message.reply_text("❌ لا تملك الصلاحية.")
        return
    if parts[0] == "رفع":
        set_rank(update.effective_chat.id, t.id, rank)
        await update.message.reply_text(f"✅ تم رفع {t.first_name} إلى {rank}.")
    else:
        remove_rank(update.effective_chat.id, t.id)
        await update.message.reply_text("✅ تم تنزيل رتبته.")

async def moderation(update, context, owner_id):
    text = update.message.text.strip()
    if text not in ("حظر", "طرد", "كتم", "الغاء الكتم", "الغاء الحظر", "تحذير"):
        return
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    t = await target(update)
    if not t:
        await update.message.reply_text("⚠️ استخدم الأمر بالرد.")
        return
    actor = await get_rank(context.bot, update.effective_chat.id,
                           update.effective_user.id, owner_id)
    target_rank = await get_rank(context.bot, update.effective_chat.id,
                                 t.id, owner_id)
    if LEVELS.get(actor, 0) <= LEVELS.get(target_rank, 0):
        await update.message.reply_text("❌ لا يمكنك تنفيذ الأمر على رتبة مساوية أو أعلى.")
        return
    try:
        if text == "حظر":
            await context.bot.ban_chat_member(update.effective_chat.id, t.id)
        elif text == "طرد":
            await context.bot.ban_chat_member(update.effective_chat.id, t.id)
            await context.bot.unban_chat_member(update.effective_chat.id, t.id)
        elif text == "كتم":
            await context.bot.restrict_chat_member(
                update.effective_chat.id, t.id,
                ChatPermissions(can_send_messages=False)
            )
        elif text == "الغاء الكتم":
            await context.bot.restrict_chat_member(
                update.effective_chat.id, t.id,
                ChatPermissions(can_send_messages=True)
            )
        elif text == "الغاء الحظر":
            await context.bot.unban_chat_member(
                update.effective_chat.id, t.id, only_if_banned=True
            )
        elif text == "تحذير":
            con = connect()
            row = con.execute(
                "SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
                (update.effective_chat.id, t.id)
            ).fetchone()
            n = (row["count"] if row else 0) + 1
            con.execute(
                "INSERT INTO warnings(chat_id,user_id,count) VALUES(?,?,?) "
                "ON CONFLICT(chat_id,user_id) DO UPDATE SET count=excluded.count",
                (update.effective_chat.id, t.id, n)
            )
            con.commit()
            con.close()
            if n >= 3:
                await context.bot.ban_chat_member(update.effective_chat.id, t.id)
                await update.message.reply_text("🚫 وصل إلى 3 تحذيرات وتم حظره.")
                return
            await update.message.reply_text(f"⚠️ تحذير {n}/3")
            return
        await update.message.reply_text("✅ تم التنفيذ.")
    except Exception:
        await update.message.reply_text("❌ تأكد أن البوت مشرف ولديه الصلاحيات المطلوبة.")

async def m1(update, context):
    await update.message.reply_text(
        "👮 م1 — أوامر الادمنيه\n━━━━━━━━━━━━\n"
        "رفع/تنزيل مالك، منشئ، مدير، ادمن، مميز\n"
        "حظر • طرد • كتم • الغاء الكتم • الغاء الحظر • تحذير"
    )

def register_admin_handlers(app, owner_id):
    app.add_handler(MessageHandler(filters.Regex(r"^م1$"), m1), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   lambda u,c: rank_cmd(u,c,owner_id)), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   lambda u,c: moderation(u,c,owner_id)), group=2)
