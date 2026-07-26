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
users = set()
# الردود
replies = {
    "السلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
    "سلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
    "كيفك": ["الحمد لله بخير، وأنت؟ 😊"],
    "كيف الحال": ["الحمد لله بخير، وأنت؟ 😊"],
}
jokes = [
    "😂 نكتتي الأولى",
    "🤣 نكتتي الثانية"
]
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)

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

    question = question.strip().lower()
    answer = answer.strip()

    if question not in replies:
        replies[question] = []

    replies[question].append(answer)

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

    if text == "نكتة" or text == "ضحكني":
        if jokes:
            await update.message.reply_text(random.choice(jokes))
        else:
            await update.message.reply_text("لا توجد نكت حالياً 😂")
        return

    if text in replies:
        await update.message.reply_text(random.choice(replies[text]))
  

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text(f"عدد المستخدمين: {len(users)}")
async def userscmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not users:
        await update.message.reply_text("لا يوجد مستخدمون.")
        return

    text = "\n".join(str(user) for user in users) 
    await update.message.reply_text(f"المستخدمون:\n\n{text}")
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("الاستخدام:\n/broadcast الرسالة")
        return

    message = " ".join(context.args)

    sent = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user, text=message)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {sent} مستخدم.")
async def addjoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("الاستخدام:\n/addjoke النكتة")
        return

    joke = " ".join(context.args)
    jokes.append(joke)
    await update.message.reply_text("✅ تم إضافة النكتة.")
async def helpcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text("""
أوامر المالك:

/addreply السؤال | الرد
/delreply السؤال
/listreply
/stats
/users
/broadcast الرسالة
""")      

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addreply", addreply))
app.add_handler(CommandHandler("delreply", delreply))
app.add_handler(CommandHandler("listreply", listreply))
app.add_handler(CommandHandler("addjoke", addjoke))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("users", userscmd))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("help", helpcmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

app.run_polling()
