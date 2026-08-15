from telegram.ext import MessageHandler, filters
from database import get_setting, set_setting

LOCKS = {
    "الروابط":"links", "الصور":"photos", "الفيديو":"videos",
    "الملصقات":"stickers", "المتحركه":"animations",
    "التوجيه":"forward", "التاك":"mentions"
}

async def lock_cmd(update, context):
    if update.effective_chat.type not in ("group","supergroup"):
        return
    p = update.message.text.strip().split()
    if len(p) != 2 or p[0] not in ("قفل","فتح"):
        return
    key = LOCKS.get(p[1])
    if not key:
        return
    set_setting(update.effective_chat.id, key, "on" if p[0]=="قفل" else "off")
    await update.message.reply_text(f"✅ تم {p[0]} {p[1]}")

async def guard(update, context):
    m = update.message
    if not m or update.effective_chat.type not in ("group","supergroup"):
        return
    key = None
    if m.text and any(x in m.text.lower() for x in ("http://","https://","t.me/")):
        key = "links"
    elif m.photo: key = "photos"
    elif m.video: key = "videos"
    elif m.animation: key = "animations"
    elif m.sticker: key = "stickers"
    if key and get_setting(update.effective_chat.id, key) == "on":
        try: await m.delete()
        except Exception: pass

async def m3(update, context):
    await update.message.reply_text(
        "🔒 م3 — القفل والفتح\n━━━━━━━━━━━━\n"
        "قفل/فتح الروابط • الصور • الفيديو • الملصقات\n"
        "قفل/فتح المتحركة • التوجيه • التاك"
    )

def register_lock_handlers(app):
    app.add_handler(MessageHandler(filters.Regex(r"^م3$"), m3), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lock_cmd), group=3)
    app.add_handler(MessageHandler(filters.ALL, guard), group=4)
