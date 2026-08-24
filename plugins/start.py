from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_NAME, BOT_CHANNEL
from main import app

@app.on_message(filters.private & filters.command("start"))
async def start(_, m):
    me = await app.get_me()
    channel = f"https://t.me/{BOT_CHANNEL.lstrip('@')}" if BOT_CHANNEL else "https://t.me/"
    add = f"https://t.me/{me.username}?startgroup=true"
    text = (
        f"👋 أهلاً بك عزيزي\n\n"
        f"🤖 أنا {BOT_NAME}، بوت حماية وإدارة المجموعات.\n\n"
        "🛡️ أستطيع إدارة الرتب والحظر والكتم والقفل والردود والهمسات والإحصائيات وغيرها.\n\n"
        "➕ أضفني إلى مجموعتك وارفعني مشرفاً ثم أرسل: تفعيل"
    )
    await m.reply_photo(
        "https://dummyimage.com/900x500/222/fff.png&text=Arabic+Protection+Bot",
        caption=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ أضفني لمجموعتك", url=add)],
            [InlineKeyboardButton("📋 الأوامر", callback_data="menu")],
            [InlineKeyboardButton("📢 التحديثات", url=channel)],
        ])
    )
