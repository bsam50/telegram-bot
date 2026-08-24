from pyrogram import filters
from main import app
from .storage import redis

@app.on_message(filters.group & filters.text, group=20)
async def custom_replies(_, m):
    t = (m.text or "").strip()
    if t.startswith("اضف رد "):
        parts = t.split(" ",2)
        if len(parts) == 3:
            await redis.set(f"reply:{m.chat.id}:{parts[1]}", parts[2])
            return await m.reply("✅ تم إضافة الرد.")
    if t.startswith("مسح رد "):
        await redis.delete(f"reply:{m.chat.id}:{t.split(' ',2)[2]}")
        return await m.reply("✅ تم حذف الرد.")
    if t == "الردود":
        keys = []
        async for key in redis.scan_iter(match=f"reply:{m.chat.id}:*"):
            keys.append(key.rsplit(":",1)[1])
        return await m.reply("💬 الردود:\n" + ("\n".join(keys) if keys else "لا توجد ردود."))
    value = await redis.get(f"reply:{m.chat.id}:{t}")
    if value:
        await m.reply(value)
