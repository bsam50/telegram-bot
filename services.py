from telegram.ext import MessageHandler, filters

async def m6(update, context):
    await update.message.reply_text(
        "🧰 م6 — الاوامر الخدمية\n━━━━━━━━━━━━\n"
        "نسبة الحب • شبيهي • شبيهتي • البايو • افتاره\n"
        "قوقل + بحث • قران • اذكار • شعر • قصائد\n"
        "اقتباسات • ثريد • قصص • كتب • من ضافني"
    )

def register_service_handlers(app):
    app.add_handler(MessageHandler(filters.Regex(r"^م6$"), m6), group=0)
