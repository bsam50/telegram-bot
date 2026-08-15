from telegram.ext import MessageHandler, filters
from database import set_setting

async def m2(update, context):
    await update.message.reply_text(
        "⚙️ م2 — اوامر الاعدادات\n━━━━━━━━━━━━\n"
        "الرابط • المالكين • المنشئين • الادمنيه • المدراء\n"
        "المميزين • القوانين • الترحيب • معلوماتي • الاعدادات"
    )

async def setting_cmd(update, context):
    p = update.message.text.strip()
    if p in ("تفعيل الترحيب","تعطيل الترحيب"):
        set_setting(update.effective_chat.id, "welcome",
                    "on" if p.startswith("تفعيل") else "off")
        await update.message.reply_text("✅ تم تحديث الترحيب.")

def register_settings_handlers(app):
    app.add_handler(MessageHandler(filters.Regex(r"^م2$"), m2), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   setting_cmd), group=5)
