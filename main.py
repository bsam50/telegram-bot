import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from database import init_db
from handlers import register_all

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في متغيرات البيئة")
if not OWNER_ID:
    raise RuntimeError("OWNER_ID غير موجود في متغيرات البيئة")

async def start(update, context):
    await update.message.reply_text(
        f"أهلاً وسهلاً {update.effective_user.first_name} 🌹\n"
        "اكتب: الاوامر"
    )

async def commands(update, context):
    await update.message.reply_text(
        "‌‌‏أهلاً بك عزيزي في قائمة الاوامر :\n"
        "━━━━━━━━━━━━\n"
        "◂ م1 : اوامر الادمنيه\n"
        "◂ م2 : اوامر الاعدادات\n"
        "◂ م3 : اوامر القفل - الفتح\n"
        "◂ م4 : اوامر التسليه\n"
        "◂ م5 : اوامر Dev\n"
        "◂ م6 : الاوامر الخدميه\n"
        "━━━━━━━━━━━━"
    )

async def my_id(update, context):
    await update.message.reply_text(f"🆔 ايديك: {update.effective_user.id}")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(r"^الاوامر$"), commands))
    app.add_handler(MessageHandler(filters.Regex(r"^(ايدي|معرفي)$"), my_id))
    register_all(app, OWNER_ID)
    app.run_polling()

if __name__ == "__main__":
    main()
