from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8710417677:AAFUU6IXbb1wbWckf0F1Py-ua4D29qMOw0U"
OWNER_ID = 8476500086 

# الردود
replies = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته",
    "سلام عليكم": "وعليكم السلام ورحمة الله وبركاته",
    "كيفك": "الحمد لله بخير، وأنت؟ 😊",
    "كيف الحال": "الحمد لله بخير، وأنت؟ 😊",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"أهلاً وسهلاً {update.effective_user.first_name} 🌹\n"
        "نورت البوت ❤️"
    )

async def addreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام:\n/addreply السؤال | الرد")
        return

    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text("اكتب بالشكل:\n/addreply السؤال | الرد")
        return

    question, answer = text.split("|", 1)
    replies[question.strip().lower()] = answer.strip()
    await update.message.reply_text("✅ تم إضافة الرد.")

async def delreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    key = " ".join(context.args).lower()

    if key in replies:
        del replies[key]
        await update.message.reply_text("🗑 تم حذف الرد.")
    else:
        await update.message.reply_text("❌ الرد غير موجود.")

async def listreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not replies:
        await update.message.reply_text("لا توجد ردود.")
        return

    text = "\n".join(replies.keys())
    await update.message.reply_text("الردود:\n\n" + text)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if text in replies:
  users = set()

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text(f"عدد المستخدمين: {len(users)}")

app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("help", helpcmd))
async def helpcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text("""
أوامر المالك:

/addreply السؤال | الرد
/delreply السؤال
/listreply
/stats
/help
""")      await update.message.reply_text(replies[text])

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addreply", addreply))
app.add_handler(CommandHandler("delreply", delreply))
app.add_handler(CommandHandler("listreply", listreply))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

app.run_polling()
