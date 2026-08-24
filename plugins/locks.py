from pyrogram import filters
from main import app
from .storage import group_enabled, redis
from .group import is_admin

LOCKS = {
"الروابط": "links", "الصور": "photos", "الفيديو": "videos",
"الملصقات": "stickers", "التوجيه": "forwards", "البوتات": "bots",
"المنشن": "mentions", "التعديل": "edits",
}

@app.on_message(filters.group & filters.text)
async def lock_commands(_, m):
    t = (m.text or "").strip()
    for action in ("قفل","فتح"):
        if t.startswith(action + " "):
            item = t.split(" ",1)[1]
            if item not in LOCKS or not await is_admin(m): return
            key = f"lock:{m.chat.id}:{LOCKS[item]}"
            if action == "قفل":
                await redis.set(key,"1")
                await m.reply(f"🔒 تم قفل {item}.")
            else:
                await redis.delete(key)
                await m.reply(f"🔓 تم فتح {item}.")
            return

@app.on_message(filters.group, group=99)
async def enforce(_, m):
    if not await group_enabled(m.chat.id): return
    checks = [
        ("links", bool(m.entities and any(e.type in ("url","text_link") for e in m.entities))),
        ("photos", bool(m.photo)),
        ("videos", bool(m.video)),
        ("stickers", bool(m.sticker)),
        ("forwards", bool(m.forward_origin)),
        ("bots", bool(m.new_chat_members and any(x.is_bot for x in m.new_chat_members))),
        ("mentions", "@" in (m.text or "")),
    ]
    for kind, found in checks:
        if found and await redis.get(f"lock:{m.chat.id}:{kind}"):
            try:
                await m.delete()
            except Exception:
                pass
            return
