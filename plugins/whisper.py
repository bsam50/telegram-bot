from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import app
from .storage import redis

@app.on_message(filters.group & filters.reply & filters.regex(r"^همسه$"), group=50)
async def make_whisper(_, m):
    u = m.reply_to_message.from_user
    key = f"hms:{m.chat.id}:{m.from_user.id}"
    await redis.set(key, str(u.id), ex=600)
    me = await app.get_me()
    url = f"https://t.me/{me.username}?start=whisper_{m.chat.id}_{m.from_user.id}_{u.id}"
    await m.reply("🔐 اضغط الزر لإرسال همستك.", reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("✉️ إرسال الهمسة", url=url)]]
    ))

@app.on_message(filters.private & filters.command("start"))
async def whisper_start(_, m):
    if not m.command or len(m.command) < 2 or not m.command[1].startswith("whisper_"):
        return
    try:
        _, chat, sender, receiver = m.command[1].split("_")
        chat, sender, receiver = map(int,(chat,sender,receiver))
    except Exception:
        return await m.reply("❌ رابط الهمسة غير صالح.")
    if m.from_user.id != sender:
        return await m.reply("❌ أنت لست مرسل الهمسة.")
    await redis.set(f"waiting_hms:{m.from_user.id}", f"{chat}:{receiver}", ex=300)
    user = await app.get_users(receiver)
    await m.reply(f"✉️ أرسل همستك الآن إلى {user.mention}.")

@app.on_message(filters.private & filters.text, group=30)
async def whisper_send(_, m):
    key = f"waiting_hms:{m.from_user.id}"
    data = await redis.get(key)
    if not data or (m.text or "").startswith("/start"):
        return
    chat, receiver = map(int,data.split(":"))
    await redis.delete(key)
    await redis.set(f"whisper_data:{chat}:{receiver}", m.text, ex=3600)
    await m.reply("✅ تم إرسال الهمسة بنجاح.")
    await app.send_message(chat, "🔐 تم استلام همسة سرية. اضغط الزر بالأسفل لرؤيتها.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👁️ عرض الهمسة", callback_data=f"viewh:{receiver}:{chat}")]]))

@app.on_callback_query(filters.regex(r"^viewh:"))
async def view_whisper(_, q):
    _, receiver, chat = q.data.split(":")
    if q.from_user.id != int(receiver) or q.message.chat.id != int(chat):
        return await q.answer("هذه الهمسة ليست لك.", show_alert=True)
    value = await redis.get(f"whisper_data:{chat}:{receiver}")
    if not value:
        return await q.answer("الهمسة منتهية.", show_alert=True)
    await q.answer(value, show_alert=True)
