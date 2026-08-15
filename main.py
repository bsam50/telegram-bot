import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from database import init_db
from ranks import rank_text
from admin import register_admin_handlers
from locks import register_lock_handlers
from settings import register_settings_handlers
from fun import register_fun_handlers
from services import register_service_handlers
from dev import register_dev_handlers

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not TOKEN or not OWNER_ID:
    raise RuntimeError("ضع BOT_TOKEN و OWNER_ID في متغيرات البيئة")

async def start(update, context):
    await update.message.reply_text(
        f"أهلاً وسهلاً {update.effective_user.first_name} 🌹\n"
        "اكتب الاوامر لعرض القائمة."
    )

async def commands(update, context):
    await update.message.reply_text(
        "أهلاً بك عزيزي في قائمة الاوامر :\n"
        "━━━━━━━━━━━━\n"
        "◂ م1 : اوامر الادمنيه\n"
        "◂ م2 : اوامر الاعدادات\n"
        "◂ م3 : اوامر القفل - الفتح\n"
        "◂ م4 : اوامر التسليه\n"
        "◂ م5 : اوامر Dev\n"
        "◂ م6 : الاوامر الخدميه\n"
        "━━━━━━━━━━━━"
    )

async def myrank(update, context):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    await update.message.reply_text(
        await rank_text(context.bot, update.effective_chat.id,
                        update.effective_user.id, OWNER_ID)
    )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(r"^الاوامر$"), commands))
    app.add_handler(MessageHandler(filters.Regex(r"^رتبتي$"), myrank))
    register_admin_handlers(app, OWNER_ID)
    register_lock_handlers(app)
    register_settings_handlers(app)
    register_fun_handlers(app)
    register_service_handlers(app)
    register_dev_handlers(app, OWNER_ID)
    app.run_polling()

if __name__ == "__main__":
    main()
