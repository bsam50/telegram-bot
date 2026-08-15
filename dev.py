from telegram.ext import MessageHandler, filters

async def m5(update, context, owner_id):
    if update.effective_user.id != owner_id:
        return
    await update.message.reply_text(
        "👑 م5 — اوامر Dev\n━━━━━━━━━━━━\n"
        "تحديث • اعاده تشغيل • reload\n"
        "الردود العامة • الرتب العامة • الحظر العام"
    )

def register_dev_handlers(app, owner_id):
    app.add_handler(MessageHandler(
        filters.Regex(r"^م5$"),
        lambda u,c: m5(u,c,owner_id)
    ), group=0)
