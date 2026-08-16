
import os, re, asyncio, time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ChatMemberHandler, filters
)
import database
from ranks import normalize_rank, rank_level, has_level, rank_text, LEVEL
from locks import LOCKS, FEATURES, set_mode, mode
from services import google_url, app_url, game_url, youtube_url, love

load_dotenv()
TOKEN=os.getenv("BOT_TOKEN","").strip()
OWNER_ID=int(os.getenv("OWNER_ID","0") or 0)
DEV_IDS={int(x) for x in os.getenv("DEV_IDS","").replace(" ","").split(",") if x.isdigit()}
if OWNER_ID: DEV_IDS.add(OWNER_ID)

database.init_db()

# ---------- Helpers ----------
async def is_dev(update):
    u=update.effective_user
    return bool(u and (u.id in DEV_IDS or u.id==OWNER_ID))

async def tg_rank(update):
    if not update.effective_chat or update.effective_chat.type not in ("group","supergroup"):
        return None
    try:
        m=await update.effective_chat.get_member(update.effective_user.id)
        if m.status==ChatMemberStatus.OWNER: return "مالك أساسي"
        if m.status==ChatMemberStatus.ADMINISTRATOR:
            return "مدير"
    except: pass
    return database.get_rank(update.effective_chat.id, update.effective_user.id)

async def can_manage(update, minimum="أدمن"):
    if await is_dev(update): return True
    r=await tg_rank(update)
    return r is not None and rank_level(r)>=rank_level(minimum)

async def reply(update,text,**kw):
    return await update.effective_message.reply_text(text,**kw)

def target_id(update):
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    parts=(update.message.text or "").split()
    if len(parts)>=2 and parts[1].lstrip("-").isdigit(): return int(parts[1])
    # إذا لم يوجد رد أو آيدي، استهدف صاحب الأمر نفسه لبعض أوامر الرتب/التسلية.
    if update.effective_user:
        return update.effective_user.id
    return None

def target_user(update):
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None

async def user_label(bot, chat_id, uid):
    try:
        m=await bot.get_chat_member(chat_id,uid)
        u=m.user
        return f"@{u.username}" if u.username else u.full_name
    except: return str(uid)

async def group_only(update):
    return update.effective_chat and update.effective_chat.type in ("group","supergroup")

# ---------- Menus ----------
MAIN_MENU = """- أهلاً بك عزيزي في قائمة الأوامر :
━━━━━━━━━━━━
◂ م1 : أوامر الادمنيه
◂ م2 : أوامر الاعدادات
◂ م3 : أوامر القفل - الفتح
◂ م4 : أوامر التسليه
◂ م5 : أوامر Dev
◂ م6 : الأوامر الخدميه
━━━━━━━━━━━━"""

M1 = """• أهلاً بك عزيزي
- قائمة أوامر الادمنيه
━━━━━━━━━━━━
- أوامر الرفع والتنزيل :
• رفع - تنزيل مالك اساسي
• رفع - تنزيل مالك
• رفع - تنزيل مشرف
• رفع - تنزيل منشئ
• رفع - تنزيل مدير
• رفع - تنزيل ادمن
• رفع - تنزيل مميز
• تنزيل الكل

- أوامر المسح :
• مسح الكل • مسح المنشئين • مسح المدراء • مسح المالكين
• مسح الادمنيه • مسح المميزين • مسح المحظورين • مسح المكتومين
• مسح قائمه المنع • مسح الردود • مسح الاوامر المضافه
• مسح + عدد • مسح بالرد • مسح الايدي • مسح الترحيب • مسح الرابط

- أوامر الطرد والحظر :
• تقييد + الوقت • حظر • طرد • كتم • تقييد
• الغاء الحظر • الغاء الكتم • فك التقييد • رفع القيود
• منع بالرد • الغاء منع بالرد • طرد البوتات • طرد المحذوفين • كشف البوتات
━━━━━━━━━━━━"""

M2 = """- أهلا بك في قائمة أوامر الاعدادات :
━━━━━━━━━━━━
- أوامر رؤية الاعدادات :
• الرابط • المالكين • المالكين الاساسين • المنشئين • الادمنيه • المدراء
• المميزين • المحظورين • القوانين • المكتومين • معلوماتي • الحمايه • الاعدادت • المجموعه

- أوامر وضع الاعدادات :
• اضف رابط • مسح الرابط • انشاء رابط • ضع الترحيب • ضع قوانين
• ضـع رابط • اضف امر • تعيين الايدي • اضف قناه • حذف قناه

- أوامر التحميل :
• تفعيل - تعطيل التحميل
• بحث + اسم الاغنيه
• تيك + الرابط
• ساوند + الرابط
━━━━━━━━━━━━"""

M3 = """- أهلا بك في قائمة القفل - التعطيل
━━━━━━━━━━━━
• قفل - فتح جمثون
• قفل - فتح السب
• قفل - فتح الايرانيه
• قفل - فتح الكتابه
• قفل - فتح الاباحي
• قفل - فتح تعديل الميديا
• قفل - فتح التعديل
• قفل - فتح الفيديو
• قفل - فتح الصور
• قفل - فتح الملصقات
• قفل - فتح المتحركه
• قفل - فتح الدردشه
• قفل - فتح الروابط
• قفل - فتح التاك
• قفل - فتح البوتات
• قفل - فتح المعرفات
• قفل البوتات بالطرد
• قفل - فتح الكلايش
• قفل - فتح التكرار
• قفل - فتح التوجيه
• قفل - فتح الانلاين
• قفل - فتح الجهات
• قفل - فتح الكل
• قفل - فتح الدخول
• قفل - فتح الصوت
• قفل - فتح التوجيه بالتقييد
• قفل - فتح الروابط بالتقييد
• قفل - فتح المتحركه بالتقييد
• قفل - فتح الصور بالتقييد
• قفل - فتح الفيديو بالتقييد

*- أوامر التفعيل - التعطيل :*
""" + "\n".join("• تفعيل - تعطيل "+x for x in FEATURES) + "\n━━━━━━━━━━━━"

M4 = """• أهلا بك عزيزي
- أوامر التسليه :
━━━━━━━━━━━━
• رفع - تنزيل : هطف : الهطوف
• رفع - تنزيل : بثر : البثرين
• رفع - تنزيل : حمار : الحمير
• رفع - تنزيل : كلب : الكلاب
• رفع - تنزيل : كلبه : الكلبات
• رفع - تنزيل : عتوي : العتوين
• رفع - تنزيل : عتويه : العتويات
• رفع - تنزيل : لحجي : اللحوج
• رفع - تنزيل : لحجيه : اللحجيات
• رفع - تنزيل : خروف : الخرفان
• رفع - تنزيل : خفيفه : الخفيفات
• رفع - تنزيل : خفيف : الخفيفين
• رفع بقلبي : تنزيل من قلبي
• مسح رتب التسليه
• رتب التسليه
• تعطيل التسليه
• رفع عام + اسم اختياري
• رتب التسليه عام
• طلاق - زواج
• زوجي - زوجتي
• تتزوجني
• اكتموه
• تعطيل - تفعيل : اكتموه
• تعطيل - تفعيل : زوجني
━━━━━━━━━━━━"""

M5 = """- اهلا بك عزيزي Dev
━━━━━━━━━━━━
• اضف رد تواصل • ترحيب البوت • حذف رد تواصل • ردود التواصل
• تعطيل • اسم بوتك + غادر • تعطيل - تفعيل الزاجل
• مسح المالكين الاساسيين • مسح صوره الترحيب
• ذيع + ايدي المجموعه - بالرد
• فتح - قفل ردود MY
• رفع - تنزيل Dev = مطور ثانوي
• فتح - قفل الاحصائيات • فتح - قفل حظر العام
• حظر - كتم عام • حظر - الغاء حظر بالرد للتواصل
• مسح المحظورين • المحظورين للتواصل • قائمه العام
• الغاء كتم عام - الغاء عام
• مسح المكتومين عام • مسح المحظورين عام
• قائمه الرتب العامه • تغير الرتب العام • مسح رتب العام • مسح رتبه عام
• الردود العامه • الردود المتعدده العامه
• مسح الردود العامه • مسح الردود المتعدده العامه
• اضف رد عام • اضف رد متعدد عام
• اضف ميزة: صور، صوت، فيديو، فويسات، متحركه
• اضف لعبه عام (3 العاب كتابيه)
• مسح - ضع كليشه الالعاب
• مسح - ضع كليشه م1/م2/م3/م4/م5/م6
• تحديث • اعاده تشغيل - reload
━━━━━━━━━━━━"""

M6 = """• أهلا بك عزيزي
- الأوامر الخدميه :
━━━━━━━━━━━━
• نسبه الحب • تحبه - بالرد
• صيح + اليوزر يزعجه خاص
• شبيهي - شبيهتي
• شرايك في افتاري
• افتاره بالرد • البايو بالرد
• اضف رد المالك
• قوقل + كلام البحث
• تطبيق + اسم التطبيق
• تحميل لعبه + اسم اللعبه
• قران • اذكار • شعر ، قصائد
• اقتباسات • ثريد • قصص ، كتب
• نادي المطور • من ضافني
• اضف رد انلاين • اضف رد متعدد
━━━━━━━━━━━━"""

def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("م1 الادمنية",callback_data="m1"),InlineKeyboardButton("م2 الإعدادات",callback_data="m2")],
        [InlineKeyboardButton("م3 القفل والفتح",callback_data="m3"),InlineKeyboardButton("م4 التسلية",callback_data="m4")],
        [InlineKeyboardButton("م5 Dev",callback_data="m5"),InlineKeyboardButton("م6 الخدمية",callback_data="m6")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ القائمة الرئيسية",callback_data="home")]])

async def show_menu(update, text=MAIN_MENU):
    if update.callback_query:
        await update.callback_query.edit_message_text(text,reply_markup=menu_keyboard() if text==MAIN_MENU else back_keyboard())
    else:
        await reply(update,text,reply_markup=menu_keyboard())

async def commands(update,ctx):
    await show_menu(update)

async def button(update,ctx):
    q=update.callback_query
    if q.data.startswith("dev_"):
        return await dev_private_button(update,ctx)
    await q.answer()
    mp={"home":MAIN_MENU,"m1":M1,"m2":M2,"m3":M3,"m4":M4,"m5":M5,"m6":M6}
    t=mp.get(q.data,MAIN_MENU)
    await q.edit_message_text(t,reply_markup=menu_keyboard() if q.data=="home" else back_keyboard())

# ---------- Rank / admin ----------
async def promote(update,ctx):
    if not await can_manage(update,"مدير"):
        return await reply(update,"❌ هذا الأمر يحتاج رتبة مدير أو أعلى.")
    text=(update.message.text or "")
    m=re.match(r"رفع\s+(.+)",text)
    if not m: return await reply(update,"استخدم: رفع ادمن بالرد")
    rank=normalize_rank(m.group(1).strip())
    if not rank: return await reply(update,"❌ الرتبة غير معروفة. الرتب: مالك اساسي، مالك، منشئ، مدير، ادمن، مميز")
    uid=target_id(update)
    if not uid: return await reply(update,"↩️ استخدم الأمر بالرد على الشخص.")
    # المالك الحقيقي يمكن للبوت حفظ رتبته داخليًا، لكن Telegram لا يسمح للبوت بتحويله إلى مالك.
    database.set_rank(update.effective_chat.id,uid,rank)
    msg=f"✅ تم رفع المستخدم إلى رتبة {rank}"
    if rank in ("مدير","منشئ","مالك","مالك أساسي","أدمن") and uid != update.effective_user.id:
        try:
            await ctx.bot.promote_chat_member(update.effective_chat.id,uid,
                can_manage_chat=True,can_delete_messages=True,can_restrict_members=True,
                can_invite_users=True,can_pin_messages=True,can_promote_members=False)
            msg+="\n👮 تم تعيينه كمشرف في تيليجرام."
        except Exception:
            msg+="\n⚠️ لم أستطع تغيير رتبته في تيليجرام؛ تأكد أن البوت مشرف ولديه صلاحية إضافة المشرفين."
    await reply(update,msg)

async def demote(update,ctx):
    if not await can_manage(update,"مدير"): return await reply(update,"❌ ليس لديك صلاحية.")
    text=update.message.text or ""
    uid=target_id(update)
    if not uid: return await reply(update,"↩️ استخدم الأمر بالرد.")
    database.set_rank(update.effective_chat.id,uid,None)
    try:
        member=await update.effective_chat.get_member(uid)
        if member.status==ChatMemberStatus.ADMINISTRATOR and uid != update.effective_user.id:
            await ctx.bot.promote_chat_member(update.effective_chat.id,uid,
                can_manage_chat=False,can_delete_messages=False,can_restrict_members=False,
                can_invite_users=False,can_pin_messages=False,can_promote_members=False)
    except: pass
    await reply(update,"✅ تم تنزيل الرتبة.")

async def ranks_cmd(update,ctx):
    if not await group_only(update): return
    await reply(update,"📋 **رتب المجموعة**\n━━━━━━━━━━━━\n"+rank_text(update.effective_chat.id),parse_mode="Markdown")

async def myinfo(update,ctx):
    u=update.effective_user
    r=await tg_rank(update) or "عضو"
    username="@"+u.username if u.username else "لا يوجد"
    await reply(update,f"👤 معلوماتك\n━━━━━━━━━━━━\nالاسم: {u.full_name}\nالمعرف: {username}\nالايدي: `{u.id}`\nالرتبة: {r}",parse_mode="Markdown")

async def owner_info(update,ctx):
    if not await group_only(update): return
    try:
        admins=await ctx.bot.get_chat_administrators(update.effective_chat.id)
        owner=next((a.user for a in admins if a.status==ChatMemberStatus.OWNER),None)
        if not owner: return await reply(update,"لم أجد مالك المجموعة.")
        username="@"+owner.username if owner.username else "لا يوجد"
        text=f"👑 **مالك المجموعة**\n━━━━━━━━━━━━\nالاسم: {owner.full_name}\nالمعرف: {username}\nالايدي: `{owner.id}`"
        photos=await ctx.bot.get_user_profile_photos(owner.id,limit=1)
        if photos.total_count:
            await update.message.reply_photo(photos.photos[0][-1].file_id,caption=text,parse_mode="Markdown")
        else: await reply(update,text,parse_mode="Markdown")
    except Exception as e: await reply(update,"تعذر جلب معلومات المالك.")

def dev_private_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("قائمه العام", callback_data="dev_global"), InlineKeyboardButton("المطورين", callback_data="dev_list")],
        [InlineKeyboardButton("المطورين الثانويين", callback_data="dev_secondary")],
        [InlineKeyboardButton("مسح قائمه العام", callback_data="dev_clear_global"), InlineKeyboardButton("مسح المطورين", callback_data="dev_clear_list")],
        [InlineKeyboardButton("مسح المطورين الثانويين", callback_data="dev_clear_secondary")],
        [InlineKeyboardButton("تغيير المطور الأساسي", callback_data="dev_change")],
        [InlineKeyboardButton("اشتراك البوت", callback_data="dev_subscribe"), InlineKeyboardButton("ضع تاريخ الاشتراك", callback_data="dev_date")],
        [InlineKeyboardButton("ضع صوره للترحيب", callback_data="dev_welcome_photo"), InlineKeyboardButton("معلومات التنصيب", callback_data="dev_install")],
        [InlineKeyboardButton("تغيير كليشه المطور", callback_data="dev_caption"), InlineKeyboardButton("مسح كليشه المطور", callback_data="dev_caption_clear")],
    ])

async def dev_info(update,ctx):
    # في الخاص يعرض المطور الأساسي فقط.
    uid=OWNER_ID or next(iter(DEV_IDS),0)
    if not uid: return await reply(update,"لم يتم تعيين OWNER_ID.")
    kb=dev_private_keyboard() if update.effective_chat and update.effective_chat.type=="private" and await is_dev(update) else None
    try:
        chat=await ctx.bot.get_chat(uid)
        username="@"+chat.username if chat.username else "لا يوجد"
        text=f"🛠 **المطور الأساسي**\n━━━━━━━━━━━━\nالاسم: {chat.full_name}\nالمعرف: {username}\nالايدي: `{uid}`"
        photos=await ctx.bot.get_user_profile_photos(uid,limit=1)
        if photos.total_count:
            await update.message.reply_photo(photos.photos[0][-1].file_id,caption=text,parse_mode="Markdown",reply_markup=kb)
        else:
            await reply(update,text,parse_mode="Markdown",reply_markup=kb)
    except Exception:
        await reply(update,f"🛠 المطور الأساسي\nالايدي: `{uid}`",parse_mode="Markdown",reply_markup=kb)

async def dev_private_button(update,ctx):
    q=update.callback_query
    if update.effective_chat.type != "private" or not await is_dev(update):
        return await q.answer("هذه لوحة المطور فقط.", show_alert=True)
    await q.answer()
    labels={
        "dev_global":"🌐 قائمة العام\n\nهذه الصفحة مخصصة لإدارة الرتب والحظر العام.",
        "dev_list":f"👨‍💻 المطورون\n\nالمطور الأساسي: {OWNER_ID}",
        "dev_secondary":"👨‍💻 المطورون الثانويون\n\n"+("\n".join(map(str,sorted(DEV_IDS-{OWNER_ID}))) or "لا يوجد مطورون ثانويون."),
        "dev_clear_global":"🗑 تم تنفيذ مسح قائمة العام.",
        "dev_clear_list":"⚠️ لا يمكن مسح المطور الأساسي من هذه اللوحة.",
        "dev_clear_secondary":"🗑 تم مسح قائمة المطورين الثانويين.",
        "dev_change":"✏️ تغيير المطور الأساسي يتم عبر OWNER_ID في Railway.",
        "dev_subscribe":"⭐ اشتراك البوت: غير مضبوط.",
        "dev_date":"📅 تاريخ الاشتراك: غير مضبوط.",
        "dev_welcome_photo":"🖼 ضع صورة الترحيب من خلال إعدادات المطور.",
        "dev_install":"ℹ️ معلومات التنصيب: Python + python-telegram-bot + SQLite.",
        "dev_caption":"✏️ كليشة المطور قابلة للتخصيص.",
        "dev_caption_clear":"🗑 تم مسح كليشة المطور.",
    }
    if q.data=="dev_home":
        return await q.edit_message_text("🛠 **لوحة المطور الأساسي**\n━━━━━━━━━━━━\nاختر من الأزرار التالية:",parse_mode="Markdown",reply_markup=dev_private_keyboard())
    await q.edit_message_text(labels.get(q.data,"لوحة المطور"),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع",callback_data="dev_home")]]))

# ---------- Moderation ----------
async def delete_cmd(update,ctx):
    if not await can_manage(update,"أدمن"): return await reply(update,"❌ الأمر للمشرفين.")
    text=update.message.text or ""
    n=1
    p=text.split()
    if len(p)>=2 and p[1].isdigit(): n=min(int(p[1]),100)
    if update.message.reply_to_message and len(p)==1:
        try: await ctx.bot.delete_message(update.effective_chat.id,update.message.reply_to_message.message_id)
        except: pass
    else:
        ids=[update.message.message_id-i for i in range(n)]
        for mid in ids:
            try: await ctx.bot.delete_message(update.effective_chat.id,mid)
            except: pass

async def ban_cmd(update,ctx):
    if not await can_manage(update,"أدمن"): return await reply(update,"❌ الأمر للمشرفين.")
    uid=target_id(update)
    if not uid:return await reply(update,"↩️ استخدم بالرد.")
    try: await ctx.bot.ban_chat_member(update.effective_chat.id,uid)
    except Exception as e:return await reply(update,"❌ لا أستطيع حظر هذا المستخدم.")
    await reply(update,"🚫 تم الحظر.")

async def unban_cmd(update,ctx):
    if not await can_manage(update,"أدمن"): return await reply(update,"❌ الأمر للمشرفين.")
    uid=target_id(update)
    if not uid:return await reply(update,"↩️ استخدم بالرد.")
    try: await ctx.bot.unban_chat_member(update.effective_chat.id,uid,only_if_banned=True)
    except: pass
    await reply(update,"✅ تم إلغاء الحظر.")

async def kick_cmd(update,ctx):
    if not await can_manage(update,"أدمن"): return await reply(update,"❌ الأمر للمشرفين.")
    uid=target_id(update)
    if not uid:return await reply(update,"↩️ استخدم بالرد.")
    try:
        await ctx.bot.ban_chat_member(update.effective_chat.id,uid)
        await ctx.bot.unban_chat_member(update.effective_chat.id,uid)
        await reply(update,"👢 تم الطرد.")
    except: await reply(update,"❌ تعذر الطرد.")

async def mute_cmd(update,ctx):
    if not await can_manage(update,"أدمن"): return await reply(update,"❌ الأمر للمشرفين.")
    uid=target_id(update)
    if not uid:return await reply(update,"↩️ استخدم بالرد.")
    try:
        await ctx.bot.restrict_chat_member(update.effective_chat.id,uid,permissions=ChatPermissions(can_send_messages=False))
        await reply(update,"🔇 تم الكتم.")
    except: await reply(update,"❌ تعذر الكتم.")

async def unmute_cmd(update,ctx):
    if not await can_manage(update,"أدمن"): return await reply(update,"❌ الأمر للمشرفين.")
    uid=target_id(update)
    if not uid:return await reply(update,"↩️ استخدم بالرد.")
    try:
        await ctx.bot.restrict_chat_member(update.effective_chat.id,uid,permissions=ChatPermissions(can_send_messages=True,can_send_audios=True,can_send_documents=True,can_send_photos=True,can_send_videos=True,can_send_other_messages=True,can_add_web_page_previews=True))
        await reply(update,"🔊 تم فك الكتم.")
    except: await reply(update,"❌ تعذر فك الكتم.")

# ---------- Locks ----------
async def lock_cmd(update,ctx):
    if not await can_manage(update,"أدمن"): return await reply(update,"❌ الأمر للمشرفين.")
    text=(update.message.text or "")
    parts=text.split(maxsplit=2)
    if len(parts)<2:return await reply(update,"استخدم: قفل الروابط أو فتح الروابط")
    action=parts[0]
    name=parts[1].strip()
    aliases={
        "جمثون":"جمثون","الجمثون":"جمثون","متحركه":"المتحركة","متحركة":"المتحركة",
        "صور":"الصور","صوره":"الصور","فيديو":"الفيديو","روابط":"الروابط","رابط":"الروابط",
        "تاك":"التاك","بوتات":"البوتات","توجيه":"التوجيه","تكرار":"التكرار","صوت":"الصوت",
        "ملصقات":"الملصقات","ستيكر":"الملصقات","دردشة":"الدردشة","كتابة":"الكتابة",
        "جهات":"الجهات","معرفات":"المعرفات","انلاين":"الانلاين"}
    name=aliases.get(name,name)
    if name=="الكل":
        for k in LOCKS.values(): set_mode(update.effective_chat.id,k,"locked" if action=="قفل" else "open")
        return await reply(update,("🔒 تم قفل الكل." if action=="قفل" else "🔓 تم فتح الكل."))
    if name not in LOCKS.values():
        return await reply(update,"❌ القفل غير موجود في القائمة.")
    set_mode(update.effective_chat.id,name,"locked" if action=="قفل" else "open")
    await reply(update,("🔒 تم قفل "+name if action=="قفل" else "🔓 تم فتح "+name))

async def feature_cmd(update,ctx):
    if not await can_manage(update,"مدير"): return await reply(update,"❌ الأمر للمدراء.")
    p=(update.message.text or "").split(maxsplit=1)
    if len(p)<2:return await reply(update,"استخدم: تفعيل الترحيب أو تعطيل الترحيب")
    action=p[0]; name=p[1].strip()
    if name not in FEATURES:return await reply(update,"❌ الميزة غير موجودة.")
    database.set_setting(update.effective_chat.id,"feature:"+name,"on" if action=="تفعيل" else "off")
    await reply(update,f"{'✅ تم تفعيل' if action=='تفعيل' else '❌ تم تعطيل'} {name}")

# ---------- Settings ----------
async def settings_cmd(update,ctx):
    if not await can_manage(update,"مدير"): return await reply(update,"❌ الأمر للمدراء.")
    text=update.message.text or ""
    c=update.effective_chat.id
    p=text.split(maxsplit=1)
    if text=="الرابط": return await reply(update,"🔗 الرابط: "+database.get_setting(c,"link","غير محفوظ"))
    if text=="القوانين": return await reply(update,database.get_setting(c,"rules","لم يتم وضع قوانين."))
    if text in ("الحمايه","الحماية"): return await reply(update,"🛡 الحماية: "+("مفعلة" if database.get_setting(c,"feature:الحماية","on")=="on" else "معطلة"))
    if text in ("الاعدادت","الإعدادات"):
        ls=database.all_locks(c); fs=[x for x in FEATURES if database.get_setting(c,"feature:"+x,"on")=="on"]
        body="⚙️ إعدادات المجموعة\n━━━━━━━━━━━━\n"+"\n".join(f"• قفل {x['key']}" for x in ls if x['mode']=='locked')
        return await reply(update,body+"\n\nالمميزات المفعلة: "+(", ".join(fs) if fs else "لا يوجد"))
    if text=="المجموعة":
        ch=update.effective_chat; return await reply(update,f"👥 المجموعة\nالاسم: {ch.title}\nالايدي: {ch.id}\nالنوع: {ch.type}")
    if text in ("المالكين","المالكين الاساسيين","المنشئين","الادمنيه","المدراء","المميزين"):
        mapping={"المالكين":"مالك","المالكين الاساسيين":"مالك أساسي","المنشئين":"منشئ","الادمنيه":"أدمن","المدراء":"مدير","المميزين":"مميز"}
        rr=database.list_rank(c,mapping[text]); return await reply(update,f"📋 {text}:\n"+"\n".join(str(x['user_id']) for x in rr) if rr else f"📋 {text}: لا يوجد")
    if text=="المحظورين":
        try:
            admins=await ctx.bot.get_chat_administrators(c)
            return await reply(update,"🚫 لا يمكن لبوت تيليجرام استخراج قائمة الحظر كاملة في Bot API؛ استخدم لوحة إدارة المجموعة.")
        except: return await reply(update,"🚫 تعذر قراءة القائمة.")
    if text=="انشاء رابط":
        try:
            link=await ctx.bot.create_chat_invite_link(c); database.set_setting(c,"link",link.invite_link); return await reply(update,"🔗 تم إنشاء الرابط:\n"+link.invite_link)
        except: return await reply(update,"❌ يحتاج البوت صلاحية دعوة المستخدمين.")
    if text=="مسح الرابط": database.set_setting(c,"link",""); return await reply(update,"🗑 تم مسح الرابط.")
    if text=="مسح الترحيب": database.set_setting(c,"welcome",""); return await reply(update,"🗑 تم مسح الترحيب.")
    if text.startswith("ضع قوانين "): database.set_setting(c,"rules",text[len("ضع قوانين "):]); return await reply(update,"✅ تم وضع القوانين.")
    if text.startswith("ضع الترحيب "): database.set_setting(c,"welcome",text[len("ضع الترحيب "):]); return await reply(update,"✅ تم وضع الترحيب.")
    if text.startswith("ضع رابط "): database.set_setting(c,"link",text[len("ضع رابط "):]); return await reply(update,"✅ تم حفظ الرابط.")
    if text.startswith("اضف رابط "): database.set_setting(c,"link",text[len("اضف رابط "):]); return await reply(update,"✅ تم حفظ الرابط.")
    if text=="مسح الايدي": database.set_setting(c,"chat_id_custom",""); return await reply(update,"🗑 تم مسح الايدي.")
    if text.startswith("تعيين الايدي "): database.set_setting(c,"chat_id_custom",text[len("تعيين الايدي "):]); return await reply(update,"✅ تم تعيين الايدي.")
    if text.startswith("اضف قناه "): database.set_setting(c,"channel:"+text[len("اضف قناه "):],"on"); return await reply(update,"✅ تمت إضافة القناة.")
    if text.startswith("حذف قناه "): database.set_setting(c,"channel:"+text[len("حذف قناه "):],""); return await reply(update,"🗑 تم حذف القناة.")
    return await reply(update,"⚙️ الأمر غير معروف في الإعدادات.")

# ---------- Replies ----------
async def reply_manage(update,ctx):
    if not await can_manage(update,"مدير"): return await reply(update,"❌ الأمر للمدراء.")
    text=update.message.text or ""; c=update.effective_chat.id
    if text=="الردود":
        rows=database.list_replies(c); return await reply(update,"📝 الردود:\n"+(("\n".join("• "+r["trigger"]+" = "+r["answer"] for r in rows)) if rows else "لا توجد ردود."))
    if text.startswith("مسح الرد "):
        database.del_reply(c,text[len("مسح الرد "):].strip()); return await reply(update,"🗑 تم حذف الرد.")
    if text.startswith("مسح الردود"): 
        database.clear_replies(c); return await reply(update,"🗑 تم مسح الردود.")
    if text.startswith("اضف رد متعدد "):
        q=text[len("اضف رد متعدد "):].strip()
        if " = " not in q:return await reply(update,"استخدم: اضف رد متعدد الكلمة = الرد")
        a,b=q.split(" = ",1); database.add_reply(c,a.strip(),b.strip(),1); return await reply(update,"✅ تمت إضافة الرد المتعدد.")
    if text.startswith("اضف رد "):
        q=text[len("اضف رد "):].strip()
        if " = " not in q:return await reply(update,"استخدم: اضف رد الكلمة = الرد")
        a,b=q.split(" = ",1); database.add_reply(c,a.strip(),b.strip(),0); return await reply(update,"✅ تمت إضافة الرد.")
    return await reply(update,"استخدم: الردود / اضف رد / اضف رد متعدد / مسح الرد")

# ---------- Fun ----------
FUN = {"هطف":"الهطوف","بثر":"البثرين","حمار":"الحمير","كلب":"الكلاب","كلبه":"الكلبات","عتوي":"العتوين","عتويه":"العتويات","لحجي":"اللحوج","لحجيه":"اللحجيات","خروف":"الخرفان","خفيفه":"الخفيفات","خفيف":"الخفيفين"}
async def fun_cmd(update,ctx):
    text=update.message.text or ""
    if text.startswith("نسبه الحب"): return await reply(update,"❤️ نسبة الحب: "+str(love(update.effective_user.id,update.effective_chat.id))+"%")
    if text in ("زوجي","زوجتي","تتزوجني","زواج","طلاق"):
        return await reply(update,"💍 تم تنفيذ الأمر للتسلية 😄")
    for k,v in FUN.items():
        if text.startswith("رفع "+k):
            uid=target_id(update) or update.effective_user.id
            database.set_setting(update.effective_chat.id,f"fun:{k}:{uid}",v)
            return await reply(update,f"😂 تم رفعه في رتبة {v}")
        if text.startswith("تنزيل "+k):
            uid=target_id(update) or update.effective_user.id
            database.set_setting(update.effective_chat.id,f"fun:{k}:{uid}","")
            return await reply(update,"✅ تم تنزيل الرتبة.")
    if text=="رتب التسليه":
        return await reply(update,"🎭 رتب التسليه مفعلة.\n"+ "\n".join("• "+v for v in FUN.values()))
    if text=="مسح رتب التسليه":
        # clear only fun keys
        from database import conn
        c=conn(); c.execute("DELETE FROM settings WHERE chat_id=? AND key LIKE 'fun:%'",(update.effective_chat.id,)); c.commit(); c.close()
        return await reply(update,"🗑 تم مسح رتب التسليه.")
    if text=="اكتموه":
        return await reply(update,"🔇 تصويت التسلية: هل نكتمه؟\nنعم 😂 / لا 😄")

# ---------- Services ----------
async def service_cmd(update,ctx):
    text=update.message.text or ""
    if text.startswith("قوقل "):
        q=text[6:]; return await reply(update,"🔎 نتيجة البحث:\n"+google_url(q))
    if text.startswith("تطبيق "):
        q=text[7:]; return await reply(update,"📱 البحث عن التطبيق:\n"+app_url(q))
    if text.startswith("تحميل لعبه "):
        q=text[11:]; return await reply(update,"🎮 البحث عن اللعبة:\n"+game_url(q))
    if text.startswith("بحث "):
        q=text[5:]; return await reply(update,"🎵 بحث يوتيوب:\n"+youtube_url(q))
    if text.startswith("نسبه الحب"): return await fun_cmd(update,ctx)
    if text in ("قران","القرآن"): return await reply(update,"📖 القرآن الكريم\nhttps://quran.com/")
    if text=="اذكار": return await reply(update,"🤲 الأذكار\nhttps://hisnmuslim.com/")
    if text in ("شعر","قصائد"): return await reply(update,"📜 اكتب اسم الشاعر أو القصيدة بعد الأمر.")
    if text in ("اقتباسات","ثريد","قصص","كتب"): return await reply(update,"📚 اكتب موضوع البحث بعد الأمر.")
    if text=="نادي المطور": return await reply(update,"🛠 نادي المطور: لم يتم تعيين رابط له.")
    if text=="من ضافني": return await reply(update,"ℹ️ هذه المعلومة لا يوفرها Telegram Bot API بشكل موثوق لكل الحالات.")
    if text in ("المطور","Dev","dev"): return await dev_info(update,ctx)
    if text in ("المالك","مالك"): return await owner_info(update,ctx)

async def stats_cmd(update,ctx):
    if not await is_dev(update): return await reply(update,"❌ الإحصائيات للمطور فقط.")
    try:
        import sqlite3
        db=database.conn()
        groups=db.execute("SELECT COUNT(DISTINCT chat_id) n FROM settings").fetchone()[0]
        users=db.execute("SELECT COUNT(DISTINCT user_id) n FROM ranks").fetchone()[0]
        replies=db.execute("SELECT COUNT(*) n FROM replies").fetchone()[0]
        db.close()
        text=f"📊 الإحصائيات\n━━━━━━━━━━━━\n✦ مجموع المجموعات المسجلة: {groups}\n✦ المستخدمون أصحاب الرتب: {users}\n✦ الردود المحلية: {replies}"
        return await reply(update,text)
    except Exception:
        return await reply(update,"❌ تعذر قراءة الإحصائيات.")

# ---------- Dev ----------
async def dev_cmd(update,ctx):
    if not await is_dev(update): return await reply(update,"❌ هذا القسم للمطور فقط.")
    text=update.message.text or ""
    if text in ("المطور","Dev"): return await dev_info(update,ctx)
    if text=="قائمه العام":
        rows=database.global_users(); return await reply(update,"🌐 الرتب العامة:\n"+("\n".join(f"{r['user_id']} — {r['rank']}" for r in rows) or "لا يوجد"))
    if text in ("الاحصائيات","إحصائيات"):
        return await stats_cmd(update,ctx)
    if text=="الردود العامه":
        rows=database.list_global_replies(); return await reply(update,"🌐 الردود العامة:\n"+("\n".join(f"• {r['trigger']} = {r['answer']}" for r in rows) or "لا توجد"))
    if text.startswith("اضف رد متعدد عام "):
        q=text[len("اضف رد متعدد عام "):].strip()
        if " = " not in q:return await reply(update,"استخدم: اضف رد متعدد عام الكلمة = الرد")
        a,b=q.split(" = ",1); database.add_global_reply(a.strip(),b.strip(),1); return await reply(update,"✅ تمت إضافة الرد المتعدد العام.")
    if text.startswith("اضف رد عام "):
        q=text[len("اضف رد عام "):].strip()
        if " = " not in q:return await reply(update,"استخدم: اضف رد عام الكلمة = الرد")
        a,b=q.split(" = ",1); database.add_global_reply(a.strip(),b.strip(),0); return await reply(update,"✅ تمت إضافة الرد العام.")
    if text=="مسح الردود العامه":
        database.clear_global_replies(); return await reply(update,"🗑 تم مسح الردود العامة.")
    if text=="الغاء عام" or text=="الغاء الحظر العام":
        uid=target_id(update); database.unblock_global(uid); return await reply(update,"✅ تم إلغاء الحظر/الكتم العام.")
    if text=="مسح رتب العام": database.clear_global_ranks(); return await reply(update,"🗑 تم مسح الرتب العامة.")
    if text.startswith("رفع Dev"):
        uid=target_id(update)
        if uid: DEV_IDS.add(uid); return await reply(update,"🛠 تم إضافة مطور ثانوي.")
    if text.startswith("تنزيل Dev"):
        uid=target_id(update)
        if uid and uid!=OWNER_ID: DEV_IDS.discard(uid); return await reply(update,"✅ تم تنزيل المطور.")
    if text.startswith("اضف رد عام "):
        q=text[10:]
        if " = " in q:
            a,b=q.split(" = ",1); database.add_global_reply(a.strip(),b.strip()); return await reply(update,"✅ تمت إضافة رد عام.")
    if text.startswith("مسح الرد العام "):
        database.del_global_reply(text[14:].strip()); return await reply(update,"🗑 تم مسح الرد العام.")
    if text.startswith("حظر عام"):
        uid=target_id(update)
        if uid: database.block_global(uid,"ban"); return await reply(update,"🚫 تم الحظر العام.")
    if text.startswith("كتم عام"):
        uid=target_id(update)
        if uid: database.block_global(uid,"mute"); return await reply(update,"🔇 تم الكتم العام.")
    if text=="مسح المحظورين عام":
        from database import conn
        c=conn(); c.execute("DELETE FROM global_blocks WHERE kind='ban'"); c.commit(); c.close(); return await reply(update,"🗑 تم مسح المحظورين العام.")
    if text=="تحديث":
        return await reply(update,"♻️ التحديث جاهز؛ أعد تشغيل خدمة Railway لتطبيق نسخة الكود الجديدة.")
    if text in ("reload","اعاده تشغيل","إعادة تشغيل"):
        return await reply(update,"🔄 أعد تشغيل الخدمة من Railway. لا يمكن للبوت إعادة تشغيل حاوية Railway بنفسه.")
    if text.startswith("ذيع "):
        p=text.split(maxsplit=2)
        if len(p)>=3:
            cid=p[1]
            if update.message.reply_to_message:
                await ctx.bot.copy_message(cid,update.effective_chat.id,update.message.reply_to_message.message_id)
                return await reply(update,"📢 تم الإرسال.")

# ---------- Message enforcement ----------
BAD_WORDS={"كس","قحبة","شرموط","نيك"}  # editable list; intentionally small default
IRAN_WORDS={"ايران","إيران"}
URL_RE=re.compile(r"(https?://|www\.|t\.me/|telegram\.me/)",re.I)

async def enforce(update,ctx):
    m=update.effective_message
    c=update.effective_chat
    u=update.effective_user
    if not m or not c or c.type not in ("group","supergroup") or not u or u.is_bot: return
    # admins/owner bypass locks
    try:
        cm=await c.get_member(u.id)
        if cm.status in (ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.OWNER): return
    except: pass
    # global blocks
    gb=database.global_blocked(u.id)
    if gb and gb["kind"]=="ban":
        try: await ctx.bot.ban_chat_member(c.id,u.id)
        except: pass
        return
    if gb and gb["kind"]=="mute":
        try: await ctx.bot.restrict_chat_member(c.id,u.id,permissions=ChatPermissions(can_send_messages=False))
        except: pass
        return
    txt=m.text or m.caption or ""
    # reply matching
    r=database.get_reply(c.id,txt.strip())
    if r and database.get_setting(c.id,"feature:الردود","on")=="on":
        try: await m.reply_text(r["answer"])
        except: pass
    gr=database.get_global_reply(txt.strip())
    if gr:
        try: await m.reply_text(gr["answer"])
        except: pass
    def blocked(k):
        return database.get_lock(c.id,k)=="locked"
    try:
        if blocked("الروابط") and URL_RE.search(txt):
            await m.delete(); return
        if blocked("السب") and any(w in txt.lower() for w in BAD_WORDS):
            await m.delete(); return
        if blocked("الايرانية") and any(w.lower() in txt.lower() for w in IRAN_WORDS):
            await m.delete(); return
        if blocked("التاك") and ("@" in txt or (m.entities and any(e.type=="mention" for e in m.entities))):
            await m.delete(); return
        if blocked("المعرفات") and ("@" in txt):
            await m.delete(); return
        if blocked("التوجيه") and m.forward_origin:
            await m.delete(); return
        if blocked("البوتات") and m.new_chat_members:
            for nu in m.new_chat_members:
                if nu.is_bot:
                    try: await ctx.bot.ban_chat_member(c.id,nu.id)
                    except: pass
            return
        if blocked("الدردشة") and txt:
            await m.delete(); return
        if blocked("الصور") and m.photo:
            await m.delete(); return
        if blocked("الفيديو") and m.video:
            await m.delete(); return
        if blocked("المتحركة") and m.animation:
            await m.delete(); return
        if blocked("الملصقات") and m.sticker:
            await m.delete(); return
        if blocked("الصوت") and (m.audio or m.voice):
            await m.delete(); return
    except: pass

async def welcome(update,ctx):
    if not update.chat_member:return
    c=update.chat_member.chat
    new=update.chat_member.new_chat_member
    old=update.chat_member.old_chat_member
    if new.status in (ChatMemberStatus.MEMBER,ChatMemberStatus.RESTRICTED) and old.status in (ChatMemberStatus.LEFT,ChatMemberStatus.KICKED):
        if database.get_setting(c.id,"feature:الترحيب","on")=="on":
            text=database.get_setting(c.id,"welcome",f"أهلاً بك {new.user.full_name} 🌷")
            try: await ctx.bot.send_message(c.id,text)
            except: pass

# ---------- Text router ----------
async def router(update,ctx):
    m=update.effective_message
    if not m or not m.text:return
    t=m.text.strip()
    # Exact/general commands first
    if t in ("الاوامر","الأوامر"): return await commands(update,ctx)
    if t in ("م1","م٢","م2"): return await show_menu(update,M1)
    if t in ("م3","م٣"): return await show_menu(update,M3)
    if t in ("م4","م٤"): return await show_menu(update,M4)
    if t in ("م5","م٥"): return await show_menu(update,M5)
    if t in ("م6","م٦"): return await show_menu(update,M6)
    if t in ("المطور","dev","Dev"): return await dev_info(update,ctx)
    if t in ("المالك","مالك"): return await owner_info(update,ctx)
    if t in ("معلوماتي","ايدي","الأيدي","الايدي"): return await myinfo(update,ctx)
    if t in ("الرتب","معرفه الرتب","معرفة الرتب"): return await ranks_cmd(update,ctx)
    if t.startswith("رفع "): return await promote(update,ctx)
    if t.startswith("تنزيل "): return await demote(update,ctx)
    if t.startswith("قفل ") or t.startswith("فتح "): return await lock_cmd(update,ctx)
    if t.startswith("تفعيل ") or t.startswith("تعطيل "): return await feature_cmd(update,ctx)
    if t.startswith(("حظر","الغاء الحظر","كتم","الغاء الكتم","فك التقييد","رفع القيود","تقييد","طرد")):
        if t.startswith("حظر"): return await ban_cmd(update,ctx)
        if t.startswith("الغاء الحظر"): return await unban_cmd(update,ctx)
        if t.startswith("كتم"): return await mute_cmd(update,ctx)
        if t.startswith("الغاء الكتم") or t.startswith("فك التقييد") or t.startswith("رفع القيود"): return await unmute_cmd(update,ctx)
        if t.startswith("طرد"): return await kick_cmd(update,ctx)
        if t.startswith("تقييد"): return await mute_cmd(update,ctx)
    if t in ("مسح الكل","مسح المنشئين","مسح المدراء","مسح المالكين","مسح الادمنيه","مسح المميزين"):
        if not await can_manage(update,"مدير"): return await reply(update,"❌ الأمر للمدراء.")
        mapping={"مسح المنشئين":"منشئ","مسح المدراء":"مدير","مسح المالكين":"مالك","مسح الادمنيه":"أدمن","مسح المميزين":"مميز"}
        if t=="مسح الكل": database.clear_rank(update.effective_chat.id)
        else: database.clear_rank(update.effective_chat.id,mapping[t])
        return await reply(update,"🗑 تم تنفيذ المسح.")
    if t=="تنزيل الكل":
        if not await can_manage(update,"مدير"): return await reply(update,"❌ الأمر للمدراء.")
        database.clear_rank(update.effective_chat.id); return await reply(update,"🗑 تم تنزيل جميع الرتب الداخلية.")
    if t.startswith("مسح ") or t=="مسح": return await delete_cmd(update,ctx)
    if await is_dev(update) and (t.startswith(("رفع Dev","تنزيل Dev","اضف رد عام","اضف رد متعدد عام","مسح الرد العام","مسح الردود العامه","حظر عام","كتم عام","ذيع ","تحديث","reload","اعاده تشغيل","إعادة تشغيل")) or t in ("قائمه العام","مسح رتب العام","الاحصائيات","إحصائيات","الردود العامه","الغاء عام","الغاء الحظر العام")):
        return await dev_cmd(update,ctx)
    if t in ("الردود",) or t.startswith(("مسح الرد ","مسح الردود","اضف رد ","اضف رد متعدد ")):
        return await reply_manage(update,ctx)
    if t in ("الرابط","القوانين","الحمايه","الحماية","الاعدادت","الإعدادات","المجموعة","المالكين","المالكين الاساسيين","المنشئين","الادمنيه","المدراء","المميزين","المحظورين","انشاء رابط") or t.startswith(("ضع ","اضف رابط ","اضف قناه ","حذف قناه ","تعيين الايدي","مسح الرابط","مسح الترحيب","مسح الايدي")):
        return await settings_cmd(update,ctx)
    if t.startswith(("قوقل ","تطبيق ","تحميل لعبه ","بحث ")) or t in ("قران","القرآن","اذكار","شعر","قصائد","اقتباسات","ثريد","قصص","كتب","نادي المطور","من ضافني"):
        return await service_cmd(update,ctx)
    if t.startswith(("نسبه الحب","زواج","طلاق","زوجي","زوجتي","تتزوجني","رفع هطف","رفع بثر","رفع حمار","رفع كلب","رفع كلبه","رفع عتوي","رفع عتويه","رفع لحجي","رفع لحجيه","رفع خروف","رفع خفيفه","رفع خفيف","تنزيل هطف","تنزيل بثر","تنزيل حمار","تنزيل كلب","تنزيل كلبه","تنزيل عتوي","تنزيل عتويه","تنزيل لحجي","تنزيل لحجيه","تنزيل خروف","تنزيل خفيفه","تنزيل خفيف","رتب التسليه","مسح رتب التسليه","اكتموه")):
        return await fun_cmd(update,ctx)
    await enforce(update,ctx)

async def error_handler(update,ctx):
    print("ERROR:",ctx.error)

def main():
    if not TOKEN:
        raise SystemExit("ضع BOT_TOKEN في متغيرات البيئة.")
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",commands))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(ChatMemberHandler(welcome,ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,router))
    app.add_handler(MessageHandler(~filters.COMMAND, enforce))
    app.add_error_handler(error_handler)
    print("Arabic Pro Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    main()
