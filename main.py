from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = "8710417677:AAFUU6IXbb1wbWckf0F1Py-ua4D29qMOw0U"

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        text = update.message.text.lower()

        if "السلام عليكم" in text or "سلام عليكم" in text:
            await update.message.reply_text("وعليكم السلام ورحمة الله وبركاته")

app = Application.builder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

app.run_polling()
