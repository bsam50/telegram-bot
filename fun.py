import random
from telegram.ext import MessageHandler, filters

async def m4(update, context):
    await update.message.reply_text(
        "🎮 م4 — اوامر التسليه\n━━━━━━━━━━━━\n"
        "رتب التسليه • زواج • طلاق • زوجي • زوجتي\n"
        "تتزوجني • اكتموه"
    )

async def love(update, context):
    if update.message.text.strip() == "نسبة الحب":
        await update.message.reply_text(f"❤️ نسبة الحب: {random.randint(1,100)}%")

def register_fun_handlers(app):
    app.add_handler(MessageHandler(filters.Regex(r"^م4$"), m4), group=0)
    app.add_handler(MessageHandler(filters.Regex(r"^نسبة الحب$"), love), group=0)
