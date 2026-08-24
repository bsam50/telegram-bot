from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import app

COMMANDS = {
"الحماية": "تفعيل\nتعطيل\nطرد\nحظر\nفك حظر\nكتم\nفك كتم\nتقييد\nفك تقييد\nتحذير\nمسح التحذيرات",
"الرتب": "رفع مالك\nتنزيل مالك\nرفع مدير\nتنزيل مدير\nرفع أدمن\nتنزيل أدمن\nالمالكين\nالمدراء\nالأدمنية",
"القفل والفتح": "قفل الروابط / فتح الروابط\nقفل الصور / فتح الصور\nقفل الفيديو / فتح الفيديو\nقفل الملصقات / فتح الملصقات\nقفل التوجيه / فتح التوجيه\nقفل البوتات / فتح البوتات\nقفل المنشن / فتح المنشن",
"الردود والهمسات": "اضف رد\nمسح رد\nالردود\nهمسه",
"الخدمات": "الإحصائيات\nمعلوماتي\nالقوانين\nالمكتومين\nالمحظورين\nالهمسات",
"المطور": "لوحة المطور\nإذاعة بالخاص\nإذاعة بالقروبات\nنسخة المستخدمين\nنسخة المجموعات\nالسيرفر\nتحديث",
}

@app.on_callback_query(filters.regex("^menu$"))
async def menu(_, q):
    await q.message.edit(
        "📋 **قائمة أوامر البوت**\n\nاختر القسم:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡️ الحماية", callback_data="cmd:الحماية"),
             InlineKeyboardButton("👑 الرتب", callback_data="cmd:الرتب")],
            [InlineKeyboardButton("⚙️ القفل والفتح", callback_data="cmd:القفل والفتح")],
            [InlineKeyboardButton("💬 الردود والهمسات", callback_data="cmd:الردود والهمسات")],
            [InlineKeyboardButton("📊 الخدمات", callback_data="cmd:الخدمات"),
             InlineKeyboardButton("🛠️ المطور", callback_data="cmd:المطور")],
        ])
    )

@app.on_callback_query(filters.regex("^cmd:"))
async def cmd(_, q):
    key = q.data.split(":", 1)[1]
    await q.message.edit(
        f"📋 **{key}**\n\n{COMMANDS[key]}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data="menu")]])
    )
