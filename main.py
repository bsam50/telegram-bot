import random
import json
import os
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
def load_json(filename, default):
    import os
    import json

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(filename, data):
    import json

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
# الردود
replies = {
    "السلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
    "سلام عليكم": ["وعليكم السلام ورحمة الله وبركاته"],
    "كيفك": ["الحمد لله بخير وأنت😊"],
    "كيف الحال": ["الحمد لله بخير وأنت😊"],
}

replies = load_json("replies.json", replies)
users = set(load_json("users.json", []))
groups = set(load_json("groups.json", []))
reply_state = {}

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
    "😂 فيه اثنين أغبياء راحوا يصيدون سمك... إذا اصطادوا سمكة رجعوها لأنها صغيرة.",
    "🤣 فيه نملة لابسة كعب... ليه؟ عندها مناسبة.",
    "😂 فيه نملة تطالع السماء... مستنية المطر ينزل لها مسبح.",
    "🤣 فيه واحد يركض وراء سيارة الإسعاف... يقول يمكن ألحق المريض.",
    "😂 فيه واحد كل ما دخل اختبار قال: بالتوفيق لكم.",
    
]
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)
    save_json("users.json", list(users))

    if update.effective_chat.type in ["group", "supergroup"]:
        groups.add(update.effective_chat.id)
        save_json("groups.json", list(groups))

    await update.message.reply_text(
        f"أهلاً وسهلاً {update.effective_user.first_name} 🌹\n"
        "نورت البوت ❤️"
    )

async def addreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    reply_state[update.effective_user.id] = {
        "step": "question"
    }

    await update.message.reply_text(
        "✏️ أرسل الكلمة أو السؤال الذي تريد إضافة رد له."
    )
async def delreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    key = " ".join(context.args).lower()

    if key in replies:
        del replies[key]
        save_json("replies.json", replies)
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
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if user_id in reply_state:
        state = reply_state[user_id]

        if state["step"] == "question":
            state["question"] = text
            state["step"] = "answer"
            await update.message.reply_text("💬 الآن أرسل الرد.")
            return

        elif state["step"] == "answer":
            question = state["question"]

            replies[question] = [text]
            save_json("replies.json", replies)

            del reply_state[user_id]

            await update.message.reply_text("✅ تم حفظ الرد.")
            return

    if text in ["نكته", "نكتة", "ضحكني"]:
        await update.message.reply_text(random.choice(jokes))
        return

    if text in replies:
        await update.message.reply_text(random.choice(replies[text]))
        return
  

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
