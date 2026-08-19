import os
import re
import json
import sqlite3
import logging
import random
import asyncio
from datetime import datetime, timedelta, timezone

from telegram import (
    Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.constants import ChatType, ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, ContextTypes, filters
)

# ============================================================
# LINA BOT - Arabic group management bot
# Python 3.12+ / python-telegram-bot 22.x
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("lina")

TOKEN = os.getenv("BOT_TOKEN", "").strip()
try:
    DEV_ID = int(os.getenv("DEV_ID", "0") or "0")
except ValueError:
    DEV_ID = 0

DB_PATH = os.getenv("DB_PATH", "lina.sqlite3")

# ---------------- Database ----------------

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db_lock = asyncio.Lock()

def q(sql, args=(), fetch=False, one=False):
    cur = db.execute(sql, args)
    rows = cur.fetchall() if fetch else None
    db.commit()
    if one:
        return rows[0] if rows else None
    return rows

def init_db():
    q("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, first_seen TEXT, last_seen TEXT
    )""")
    q("""CREATE TABLE IF NOT EXISTS groups(
        chat_id INTEGER PRIMARY KEY, title TEXT, rules TEXT DEFAULT '',
        welcome TEXT DEFAULT 'اهلاً {name} في {title} ❤️',
        welcome_on INTEGER DEFAULT 1, link TEXT DEFAULT '',
        protection INTEGER DEFAULT 0, downloads INTEGER DEFAULT 0,
        stats INTEGER DEFAULT 1, my_replies INTEGER DEFAULT 1
    )""")
    q("""CREATE TABLE IF NOT EXISTS ranks(
        chat_id INTEGER, user_id INTEGER, rank TEXT,
        PRIMARY KEY(chat_id,user_id)
    )""")
    q("""CREATE TABLE IF NOT EXISTS replies(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER,
        key TEXT, value TEXT, kind TEXT DEFAULT 'normal'
    )""")
    q("""CREATE TABLE IF NOT EXISTS channels(
        chat_id INTEGER, channel TEXT, PRIMARY KEY(chat_id,channel)
    )""")
    q("""CREATE TABLE IF NOT EXISTS locks(
        chat_id INTEGER, item TEXT, enabled INTEGER DEFAULT 0,
        PRIMARY KEY(chat_id,item)
    )""")
    q("""CREATE TABLE IF NOT EXISTS bans(
        chat_id INTEGER, user_id INTEGER, PRIMARY KEY(chat_id,user_id)
    )""")
    q("""CREATE TABLE IF NOT EXISTS mutes(
        chat_id INTEGER, user_id INTEGER, until_ts INTEGER,
        PRIMARY KEY(chat_id,user_id)
    )""")
    q("""CREATE TABLE IF NOT EXISTS global_bans(
        user_id INTEGER PRIMARY KEY
    )""")
    q("""CREATE TABLE IF NOT EXISTS global_mutes(
        user_id INTEGER PRIMARY KEY
    )""")
    q("""CREATE TABLE IF NOT EXISTS settings(
        chat_id INTEGER, key TEXT, value TEXT,
        PRIMARY KEY(chat_id,key)
    )""")
    q("""CREATE TABLE IF NOT EXISTS bot_games(
        name TEXT PRIMARY KEY, description TEXT
    )""")
    q("""CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER,
        user_id INTEGER, event TEXT, created_at TEXT
    )""")
    q("""CREATE TABLE IF NOT EXISTS custom_commands(
        chat_id INTEGER, name TEXT, response TEXT,
        PRIMARY KEY(chat_id,name)
    )""")

def now():
    return datetime.now(timezone.utc).isoformat()

def remember_user(user):
    if not user:
        return
    old = q("SELECT user_id FROM users WHERE user_id=?", (user.id,), True, True)
    if old:
        q("UPDATE users SET name=?, username=?, last_seen=? WHERE user_id=?",
          (user.full_name, user.username or "", now(), user.id))
    else:
        q("INSERT INTO users VALUES(?,?,?,?,?)",
          (user.id, user.full_name, user.username or "", now(), now()))

def ensure_group(chat):
    if not chat or chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    old = q("SELECT chat_id FROM groups WHERE chat_id=?", (chat.id,), True, True)
    if not old:
        q("INSERT INTO groups(chat_id,title) VALUES(?,?)", (chat.id, chat.title or ""))
    else:
        q("UPDATE groups SET title=? WHERE chat_id=?", (chat.title or "", chat.id))

def group_row(chat_id):
    r = q("SELECT * FROM groups WHERE chat_id=?", (chat_id,), True, True)
    if not r:
        q("INSERT INTO groups(chat_id,title) VALUES(?,?)", (chat_id, ""))
        r = q("SELECT * FROM groups WHERE chat_id=?", (chat_id,), True, True)
    return r

# ---------------- Arabic normalization ----------------

def norm(s):
    s = (s or "").strip()
    return (s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
             .replace("ى","ي").replace("ة","ه").replace("ؤ","و").replace("ئ","ي"))

def clean_key(s):
    return norm(s).strip().lower()

# ---------------- Ranks ----------------

RANKS = {
    "عضو": 0,
    "مميز": 10,
    "ادمن": 20,
    "مدير": 30,
    "منشئ": 40,
    "مالك": 50,
    "مالك اساسي": 60,
    "مطور": 100,
}
RANK_ALIASES = {
    "في اي بي": "مميز", "vip": "مميز", "مشرف": "ادمن",
    "مشرفين": "ادمن", "منشي": "منشئ", "المنشئ": "منشئ",
    "المالك": "مالك", "المالك الاساسي": "مالك اساسي",
}

def is_dev(user_id):
    return bool(DEV_ID and user_id == DEV_ID)

def rank(chat_id, user_id):
    if is_dev(user_id):
        return "مطور"
    r = q("SELECT rank FROM ranks WHERE chat_id=? AND user_id=?",
          (chat_id,user_id), True, True)
    return r["rank"] if r else "عضو"

def level(chat_id, user_id):
    return RANKS.get(rank(chat_id,user_id), 0)

def can(chat_id, user_id, needed):
    return level(chat_id,user_id) >= RANKS[needed]

async def admin_required(update, needed="ادمن"):
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await reply(update, "❌ هذا الأمر للمجموعات فقط.")
        return False
    if not can(update.effective_chat.id, update.effective_user.id, needed):
        await reply(update, f"❌ هذا الأمر يحتاج رتبة {needed} أو أعلى.")
        return False
    return True

def set_rank(chat_id, user_id, new_rank):
    q("INSERT OR REPLACE INTO ranks VALUES(?,?,?)",
      (chat_id,user_id,new_rank))

def remove_rank(chat_id, user_id):
    q("DELETE FROM ranks WHERE chat_id=? AND user_id=?", (chat_id,user_id))

# ---------------- Common helpers ----------------

async def reply(update, text, **kwargs):
    if update.message:
        return await update.message.reply_text(text, **kwargs)
    if update.callback_query:
        return await update.callback_query.message.reply_text(text, **kwargs)

async def get_target(update, context):
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    if context.args:
        raw = context.args[0].strip().lstrip("@")
        if raw.isdigit():
            try:
                m = await context.bot.get_chat_member(update.effective_chat.id, int(raw))
                return m.user
            except Exception:
                return None
        try:
            m = await context.bot.get_chat_member(update.effective_chat.id, raw)
            return m.user
        except Exception:
            return None
    return None

def target_name(u):
    return u.full_name if u else "العضو"

async def bot_is_admin(update, context):
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        return m.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def delete_message(message):
    try:
        await message.delete()
        return True
    except Exception:
        return False

# ---------------- Menus ----------------

BASE_MENU = """🤖 بوت لينا

الأوامر المتاحة حسب رتبتك:
• رتبتي
• معلوماتي
• القوانين
• الرابط
• اهمس
• نسبة الحب / تحبه
• هطف / بثر / حمار / زواج / طلاق
"""

ADMIN_MENU = BASE_MENU + """
🛡️ الإدارة:
• رفع مميز / تنزيل مميز
• رفع ادمن / تنزيل ادمن
• رفع مدير / تنزيل مدير
• رفع منشئ / تنزيل منشئ
• رفع مالك / تنزيل مالك
• حظر / فك حظر / طرد
• كتم / فك كتم
• مسح

💬 الردود:
• اضف رد الكلمة الرد
• اضف رد عام الكلمة الرد
• اضف رد مميز الكلمة الرد
• اضف رد متعدد الكلمة الرد
• حذف رد الكلمة
• الردود

🔒 الحماية:
• قفل الروابط / فتح الروابط
• قفل الصور / فتح الصور
• قفل الفيديو / فتح الفيديو
• قفل الصوت / فتح الصوت
• قفل الملصقات / فتح الملصقات
• قفل المتحركة / فتح المتحركة
• قفل المنشن / فتح المنشن
• قفل التوجيه / فتح التوجيه
• قفل البوتات / فتح البوتات
• قفل التعديل / فتح التعديل
• قفل الكتابة / فتح الكتابة
• قفل الكل / فتح الكل
"""

OWNER_MENU = ADMIN_MENU + """
⚙️ الإعدادات:
• ضع قوانين النص
• ضع ترحيب النص
• تفعيل الترحيب / تعطيل الترحيب
• ضع رابط الرابط
• حذف الرابط
• ايدي المجموعة
• معلومات المجموعة
• الحماية / تعطيل الحماية
• الاعدادات
• اضف قناة @channel
• حذف قناة @channel
"""

DEV_MENU = OWNER_MENU + """
👨‍💻 المطور:
• لوحة المطور
• احصائيات
• حظر عام / فك حظر عام
• كتم عام / فك كتم عام
• حظر مطور
• مسح المطورين
• تفعيل الردود / تعطيل الردود
• تفعيل الاحصائيات / تعطيل الاحصائيات
• تفعيل الحماية / تعطيل الحماية
"""

def menu_for(chat_id, user_id):
    l = level(chat_id,user_id)
    if l >= RANKS["مطور"]:
        return DEV_MENU
    if l >= RANKS["مالك"]:
        return OWNER_MENU
    if l >= RANKS["ادمن"]:
        return ADMIN_MENU
    return BASE_MENU

# ---------------- Start / commands ----------------

async def start(update, context):
    remember_user(update.effective_user)
    if update.effective_chat.type == ChatType.PRIVATE:
        if is_dev(update.effective_user.id):
            text = ("👨‍💻 مرحبًا بك في لوحة مطور بوت لينا.\n\n"
                    "يمكنك إدارة الردود والألعاب والإحصائيات من الخاص.\n"
                    "اكتب: لوحة المطور")
        else:
            text = ("مرحبًا بك ❤️\n\n"
                    "أنا بوت لينا 🤖\n"
                    "بوت إدارة وحماية وترفيه للمجموعات.\n\n"
                    "أضفني إلى مجموعتك وارفعني مشرفًا.")
        await update.message.reply_text(text)
    else:
        await update.message.reply_text(
            f"أهلًا {update.effective_user.first_name} ❤️\n"
            "اكتب «اوامر» لرؤية الأوامر المتاحة لرتبتك."
        )

async def commands(update, context):
    remember_user(update.effective_user)
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await reply(update, "اكتب «اوامر» داخل المجموعة.")
        return
    await reply(update, menu_for(update.effective_chat.id, update.effective_user.id))

async def my_rank(update, context):
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await reply(update, "❌ للمجموعات.")
        return
    await reply(update, f"🎖️ رتبتك: {rank(update.effective_chat.id, update.effective_user.id)}")

async def my_info(update, context):
    u = update.effective_user
    r = rank(update.effective_chat.id,u.id) if update.effective_chat.type in (ChatType.GROUP,ChatType.SUPERGROUP) else "عضو"
    await reply(update, f"👤 الاسم: {u.full_name}\n🆔 الآيدي: {u.id}\n🔹 اليوزر: @{u.username or 'لا يوجد'}\n🎖️ الرتبة: {r}")

async def group_info(update, context):
    if not await admin_required(update,"ادمن"): return
    c = update.effective_chat
    try:
        count = await context.bot.get_chat_member_count(c.id)
    except Exception:
        count = "غير متاح"
    g = group_row(c.id)
    await reply(update, f"🏠 {c.title}\n🆔 {c.id}\n👥 الأعضاء: {count}\n🛡️ الحماية: {'مفعلة' if g['protection'] else 'معطلة'}")

# ---------------- Rank commands ----------------

async def rank_cmd(update, context, wanted, promote):
    if not await admin_required(update, "مدير"): return
    t = await get_target(update, context)
    if not t:
        await reply(update, "❌ قم بالرد على العضو.")
        return
    actor_level = level(update.effective_chat.id, update.effective_user.id)
    if actor_level <= RANKS[wanted]:
        await reply(update, "❌ لا يمكنك إعطاء رتبة أعلى من رتبتك أو مساوية لها.")
        return
    if t.id == update.effective_user.id or is_dev(t.id):
        await reply(update, "❌ لا يمكن تعديل هذه الرتبة.")
        return
    if promote:
        set_rank(update.effective_chat.id,t.id,wanted)
        await reply(update, f"✅ تم رفع {target_name(t)} إلى {wanted}.")
    else:
        if rank(update.effective_chat.id,t.id) == wanted:
            remove_rank(update.effective_chat.id,t.id)
        await reply(update, f"✅ تم تنزيل {target_name(t)} من {wanted}.")

# ---------------- Moderation ----------------

async def ban(update, context):
    if not await admin_required(update,"ادمن"): return
    t = await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على العضو."); return
    if level(update.effective_chat.id,update.effective_user.id) <= level(update.effective_chat.id,t.id):
        await reply(update,"❌ لا يمكنك حظر رتبة مساوية أو أعلى."); return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id,t.id)
        q("INSERT OR REPLACE INTO bans VALUES(?,?)",(update.effective_chat.id,t.id))
        await reply(update,f"🚫 تم حظر {target_name(t)}.")
    except Exception as e:
        log.warning(e)
        await reply(update,"❌ فشل الحظر. تأكد أن البوت مشرف ولديه صلاحية الحظر.")

async def unban(update, context):
    if not await admin_required(update,"ادمن"): return
    t = await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على العضو."); return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id,t.id,only_if_banned=True)
        q("DELETE FROM bans WHERE chat_id=? AND user_id=?",(update.effective_chat.id,t.id))
        await reply(update,"✅ تم فك الحظر.")
    except Exception:
        await reply(update,"❌ تعذر فك الحظر.")

async def kick(update, context):
    if not await admin_required(update,"ادمن"): return
    t = await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على العضو."); return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id,t.id)
        await context.bot.unban_chat_member(update.effective_chat.id,t.id)
        await reply(update,f"👢 تم طرد {target_name(t)}.")
    except Exception:
        await reply(update,"❌ فشل الطرد.")

def mute_permissions():
    return ChatPermissions(can_send_messages=False)

def full_permissions():
    return ChatPermissions(
        can_send_messages=True, can_send_audios=True, can_send_documents=True,
        can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
        can_send_voice_notes=True, can_send_polls=True,
        can_send_other_messages=True, can_add_web_page_previews=True
    )

async def mute(update, context):
    if not await admin_required(update,"ادمن"): return
    t = await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على العضو."); return
    minutes = 0
    for a in context.args:
        if a.isdigit(): minutes=int(a); break
    until = datetime.now(timezone.utc)+timedelta(minutes=minutes) if minutes else None
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,t.id,permissions=mute_permissions(),
            until_date=until
        )
        ts = int(until.timestamp()) if until else 0
        q("INSERT OR REPLACE INTO mutes VALUES(?,?,?)",(update.effective_chat.id,t.id,ts))
        await reply(update,f"🔇 تم كتم {target_name(t)}" + (f" لمدة {minutes} دقيقة." if minutes else "."))
    except Exception:
        await reply(update,"❌ فشل الكتم.")

async def unmute(update, context):
    if not await admin_required(update,"ادمن"): return
    t = await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على العضو."); return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id,t.id,permissions=full_permissions())
        q("DELETE FROM mutes WHERE chat_id=? AND user_id=?",(update.effective_chat.id,t.id))
        await reply(update,"🔊 تم فك الكتم.")
    except Exception:
        await reply(update,"❌ فشل فك الكتم.")

async def clear(update, context):
    if not await admin_required(update,"ادمن"): return
    if not update.message.reply_to_message:
        await reply(update,"❌ رد على أول رسالة تريد مسحها ثم اكتب مسح.")
        return
    start = update.message.reply_to_message.message_id
    end = update.message.message_id
    count=0
    for mid in range(start,end+1):
        try:
            await context.bot.delete_message(update.effective_chat.id,mid)
            count += 1
        except Exception:
            pass
    await reply(update,f"🧹 تم مسح {count} رسالة.")

# ---------------- Replies ----------------

async def add_reply(update, context, kind="normal"):
    if not await admin_required(update,"ادمن"): return
    parts = update.message.text.split(maxsplit=3)
    if len(parts)<4:
        await reply(update,"❌ الصيغة: اضف رد [الكلمة] [الرد]")
        return
    key=clean_key(parts[2]); value=parts[3]
    q("DELETE FROM replies WHERE chat_id=? AND key=? AND kind=?",
      (update.effective_chat.id,key,kind))
    q("INSERT INTO replies(chat_id,key,value,kind) VALUES(?,?,?,?)",
      (update.effective_chat.id,key,value,kind))
    await reply(update,f"✅ تم حفظ الرد «{parts[2]}».")

async def delete_reply(update, context):
    if not await admin_required(update,"ادمن"): return
    parts=update.message.text.split(maxsplit=2)
    if len(parts)<3:
        await reply(update,"❌ الصيغة: حذف رد الكلمة"); return
    key=clean_key(parts[2])
    cur=q("DELETE FROM replies WHERE chat_id=? AND key=?",(update.effective_chat.id,key))
    await reply(update,"✅ تم حذف الرد." if cur is not None else "❌ لم يتم العثور على الرد.")

async def list_replies(update, context):
    if not await admin_required(update,"ادمن"): return
    rows=q("SELECT key,kind FROM replies WHERE chat_id=? ORDER BY key",
           (update.effective_chat.id,),True)
    if not rows:
        await reply(update,"💬 لا توجد ردود.")
        return
    names={"normal":"عادي","special":"مميز","multi":"متعدد","global":"عام"}
    await reply(update,"💬 الردود:\n"+"\n".join(
        f"• {r['key']} — {names.get(r['kind'],r['kind'])}" for r in rows
    ))

# ---------------- Settings ----------------

async def show_rules(update, context):
    if update.effective_chat.type not in (ChatType.GROUP,ChatType.SUPERGROUP):
        await reply(update,"❌ للمجموعات."); return
    g=group_row(update.effective_chat.id)
    await reply(update,"📜 القوانين:\n\n"+(g["rules"] or "لم يتم وضع قوانين."))

async def set_rules_cmd(update, context):
    if not await admin_required(update,"مالك"): return
    p=update.message.text.split(maxsplit=2)
    if len(p)<3: await reply(update,"❌ الصيغة: ضع قوانين النص"); return
    q("UPDATE groups SET rules=? WHERE chat_id=?",(p[2],update.effective_chat.id))
    await reply(update,"✅ تم حفظ القوانين.")

async def set_welcome_cmd(update, context):
    if not await admin_required(update,"مالك"): return
    p=update.message.text.split(maxsplit=2)
    if len(p)<3: await reply(update,"❌ الصيغة: ضع ترحيب النص"); return
    q("UPDATE groups SET welcome=? WHERE chat_id=?",(p[2],update.effective_chat.id))
    await reply(update,"✅ تم حفظ الترحيب.\nاستخدم {name} و {title} داخل النص.")

async def welcome_toggle(update, context, enabled):
    if not await admin_required(update,"مالك"): return
    q("UPDATE groups SET welcome_on=? WHERE chat_id=?",(1 if enabled else 0,update.effective_chat.id))
    await reply(update,"✅ تم تفعيل الترحيب." if enabled else "❌ تم تعطيل الترحيب.")

async def show_link(update, context):
    if update.effective_chat.type not in (ChatType.GROUP,ChatType.SUPERGROUP):
        await reply(update,"❌ للمجموعات."); return
    g=group_row(update.effective_chat.id)
    if g["link"]:
        await reply(update,"🔗 "+g["link"]); return
    try:
        l=await context.bot.create_chat_invite_link(update.effective_chat.id)
        q("UPDATE groups SET link=? WHERE chat_id=?",(l.invite_link,update.effective_chat.id))
        await reply(update,"🔗 "+l.invite_link)
    except Exception:
        await reply(update,"❌ لا أستطيع إنشاء رابط. اجعلني مشرفًا.")

async def set_link(update, context):
    if not await admin_required(update,"مالك"): return
    p=update.message.text.split(maxsplit=2)
    if len(p)<3: await reply(update,"❌ الصيغة: ضع رابط الرابط"); return
    q("UPDATE groups SET link=? WHERE chat_id=?",(p[2],update.effective_chat.id))
    await reply(update,"✅ تم حفظ الرابط.")

async def delete_link(update, context):
    if not await admin_required(update,"مالك"): return
    q("UPDATE groups SET link='' WHERE chat_id=?",(update.effective_chat.id,))
    await reply(update,"✅ تم حذف الرابط.")

async def settings_cmd(update, context):
    if not await admin_required(update,"ادمن"): return
    g=group_row(update.effective_chat.id)
    locks=q("SELECT item FROM locks WHERE chat_id=? AND enabled=1",(update.effective_chat.id,),True)
    await reply(update,
        f"⚙️ إعدادات المجموعة\n"
        f"الحماية: {'مفعلة' if g['protection'] else 'معطلة'}\n"
        f"الترحيب: {'مفعل' if g['welcome_on'] else 'معطل'}\n"
        f"الردود: {'مفعلة' if g['my_replies'] else 'معطلة'}\n"
        f"الأقفال: {', '.join(x['item'] for x in locks) or 'لا يوجد'}"
    )

# ---------------- Lock system ----------------

LOCK_ITEMS={
    "الروابط":"links","الصور":"photos","الفيديو":"video",
    "الصوت":"audio","الملصقات":"stickers","المتحركة":"animations",
    "المنشن":"mentions","التوجيه":"forward","البوتات":"bots",
    "التعديل":"edit","الكتابة":"text","الجهات":"contacts",
    "الوسائط":"media","التاغات":"mentions","الانلاين":"inline",
    "التكرار":"repeat","الفشار":"profanity","الملفات":"documents",
    "المكالمات":"calls","الدخول":"join",
}
LOCK_LABELS={"links":"الروابط","photos":"الصور","video":"الفيديو","audio":"الصوت",
"stickers":"الملصقات","animations":"المتحركة","mentions":"المنشن","forward":"التوجيه",
"bots":"البوتات","edit":"التعديل","text":"الكتابة","contacts":"الجهات",
"media":"الوسائط","documents":"الملفات","join":"الدخول","calls":"المكالمات",
"inline":"الانلاين","repeat":"التكرار","profanity":"الكلام المسيء"}

async def set_lock(update, context, enabled):
    if not await admin_required(update,"ادمن"): return
    parts=norm(update.message.text).split(maxsplit=1)
    if len(parts)<2:
        await reply(update,"❌ مثال: قفل الروابط"); return
    item=parts[1]
    if item=="الكل":
        for k in LOCK_LABELS:
            q("INSERT OR REPLACE INTO locks VALUES(?,?,?)",(update.effective_chat.id,k,1 if enabled else 0))
        await reply(update,"🔒 تم قفل كل الأنواع." if enabled else "🔓 تم فتح كل الأنواع.")
        return
    key=LOCK_ITEMS.get(item)
    if not key:
        await reply(update,"❌ نوع القفل غير معروف."); return
    q("INSERT OR REPLACE INTO locks VALUES(?,?,?)",(update.effective_chat.id,key,1 if enabled else 0))
    await reply(update,("🔒 تم قفل "+item+"." if enabled else "🔓 تم فتح "+item+"."))

def locked(chat_id,item):
    r=q("SELECT enabled FROM locks WHERE chat_id=? AND item=?",(chat_id,item),True,True)
    return bool(r and r["enabled"])

# ---------------- Channels ----------------

async def add_channel(update, context):
    if not await admin_required(update,"مالك"): return
    p=update.message.text.split(maxsplit=2)
    if len(p)<3: await reply(update,"❌ الصيغة: اضف قناة @channel"); return
    ch=p[2]
    q("INSERT OR IGNORE INTO channels VALUES(?,?)",(update.effective_chat.id,ch))
    await reply(update,"✅ تمت إضافة القناة.")

async def del_channel(update, context):
    if not await admin_required(update,"مالك"): return
    p=update.message.text.split(maxsplit=2)
    if len(p)<3: await reply(update,"❌ الصيغة: حذف قناة @channel"); return
    q("DELETE FROM channels WHERE chat_id=? AND channel=?",(update.effective_chat.id,p[2]))
    await reply(update,"✅ تم حذف القناة.")

# ---------------- Whisper ----------------

async def whisper(update, context):
    if update.effective_chat.type not in (ChatType.GROUP,ChatType.SUPERGROUP):
        await reply(update,"❌ الهمسات داخل المجموعة فقط."); return
    t=await get_target(update,context)
    if not t:
        await reply(update,"❌ قم بالرد على العضو ثم اكتب اهمس."); return
    context.user_data["whisper"]={"group":update.effective_chat.id,"target":t.id}
    try:
        await context.bot.send_message(
            update.effective_user.id,
            "💌 أرسل الآن نص الهمسة.\n"
            "سيتم إرسالها إلى المجموعة باسم «همسة» دون إظهار صاحبها."
        )
        await reply(update,"💌 تم فتح الهمسة في الخاص. أرسل الرسالة هناك.")
    except Exception:
        await reply(update,"❌ افتح خاص البوت واضغط Start أولًا.")

# ---------------- Entertainment / games ----------------

FUN_NAMES=["هطف","بثر","حمار","مزعج","كيوت","محبوب","زعيم","ذكي","نحس"]
FUN_PHRASES=["نسبتك", "احتمال", "النتيجة"]

async def fun_percent(update, context, label):
    t=await get_target(update,context)
    if not t: t=update.effective_user
    value=random.randint(0,100)
    await reply(update,f"🎮 {label}\n👤 {t.full_name}\n📊 النتيجة: {value}%")

async def dice_game(update, context):
    a=random.randint(1,6); b=random.randint(1,6)
    await reply(update,f"🎲 النرد\nأنت: {a}\nالبوت: {b}\n"+("🏆 فزت!" if a>b else "🤝 تعادل!" if a==b else "🤖 فاز البوت!"))

async def love(update, context):
    await fun_percent(update,context,"نسبة الحب ❤️")

async def who_loves(update, context):
    t=await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على شخص."); return
    await reply(update,f"❤️ {update.effective_user.first_name} يحب {t.first_name} بنسبة {random.randint(0,100)}%.")

# ---------------- Developer ----------------

async def dev_panel(update, context):
    if not is_dev(update.effective_user.id):
        await reply(update,"❌ هذا الأمر للمطور الأساسي فقط."); return
    kb=[
        [InlineKeyboardButton("📊 الإحصائيات",callback_data="dev_stats"),
         InlineKeyboardButton("💬 الردود العامة",callback_data="dev_replies")],
        [InlineKeyboardButton("🎮 الألعاب",callback_data="dev_games"),
         InlineKeyboardButton("👥 المستخدمون",callback_data="dev_users")],
    ]
    await reply(update,"👨‍💻 لوحة مطور لينا\n\nمن هنا يمكنك إدارة الخدمات العامة.",reply_markup=InlineKeyboardMarkup(kb))

async def stats(update, context):
    if not is_dev(update.effective_user.id):
        await reply(update,"❌ للمطور فقط."); return
    users=q("SELECT COUNT(*) c FROM users",fetch=True,one=True)["c"]
    groups=q("SELECT COUNT(*) c FROM groups",fetch=True,one=True)["c"]
    reps=q("SELECT COUNT(*) c FROM replies",fetch=True,one=True)["c"]
    await reply(update,f"📊 إحصائيات لينا\n\n👤 المستخدمون: {users}\n👥 المجموعات: {groups}\n💬 الردود: {reps}")

async def global_ban(update, context, enable=True):
    if not is_dev(update.effective_user.id):
        await reply(update,"❌ للمطور فقط."); return
    t=await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على العضو."); return
    if enable:
        q("INSERT OR IGNORE INTO global_bans VALUES(?)",(t.id,))
        await reply(update,"🌍 تم الحظر العام.")
    else:
        q("DELETE FROM global_bans WHERE user_id=?",(t.id,))
        await reply(update,"🌍 تم فك الحظر العام.")

async def global_mute(update, context, enable=True):
    if not is_dev(update.effective_user.id):
        await reply(update,"❌ للمطور فقط."); return
    t=await get_target(update,context)
    if not t: await reply(update,"❌ قم بالرد على العضو."); return
    if enable:
        q("INSERT OR IGNORE INTO global_mutes VALUES(?)",(t.id,))
        await reply(update,"🌍 تم الكتم العام.")
    else:
        q("DELETE FROM global_mutes WHERE user_id=?",(t.id,))
        await reply(update,"🌍 تم فك الكتم العام.")

async def dev_clear_ranks(update, context):
    if not is_dev(update.effective_user.id):
        await reply(update,"❌ للمطور فقط."); return
    q("DELETE FROM ranks WHERE rank='مطور'")
    await reply(update,"✅ تم مسح المطورين الثانويين.")

async def dev_toggle(update, context, field, enabled):
    if not is_dev(update.effective_user.id):
        await reply(update,"❌ للمطور فقط."); return
    # Applies to the current group when command is used in a group.
    if update.effective_chat.type not in (ChatType.GROUP,ChatType.SUPERGROUP):
        await reply(update,"❌ استخدم هذا الأمر داخل المجموعة."); return
    if field not in ("my_replies","stats","protection"):
        await reply(update,"❌ إعداد غير معروف."); return
    q(f"UPDATE groups SET {field}=? WHERE chat_id=?",(1 if enabled else 0,update.effective_chat.id))
    await reply(update,"✅ تم التفعيل." if enabled else "❌ تم التعطيل.")

# ---------------- Custom commands ----------------

async def add_command(update, context):
    if not await admin_required(update,"مالك"): return
    p=update.message.text.split(maxsplit=3)
    if len(p)<4:
        await reply(update,"❌ الصيغة: اضف امر اسم الامر الرد"); return
    q("INSERT OR REPLACE INTO custom_commands VALUES(?,?,?)",
      (update.effective_chat.id,clean_key(p[2]),p[3]))
    await reply(update,"✅ تمت إضافة الأمر.")

async def delete_command(update, context):
    if not await admin_required(update,"مالك"): return
    p=update.message.text.split(maxsplit=2)
    if len(p)<3: await reply(update,"❌ الصيغة: حذف امر اسم الامر"); return
    q("DELETE FROM custom_commands WHERE chat_id=? AND name=?",
      (update.effective_chat.id,clean_key(p[2])))
    await reply(update,"✅ تم حذف الأمر.")

# ---------------- New members / protection ----------------

async def new_member(update, context):
    if not update.chat_member: return
    old=update.chat_member.old_chat_member
    new=update.chat_member.new_chat_member
    if new.status not in (ChatMemberStatus.MEMBER,ChatMemberStatus.RESTRICTED): return
    if old.status in (ChatMemberStatus.MEMBER,ChatMemberStatus.RESTRICTED): return
    uid=new.user.id
    if q("SELECT user_id FROM global_bans WHERE user_id=?",(uid,),True,True):
        try: await context.bot.ban_chat_member(update.effective_chat.id,uid)
        except Exception: pass
        return
    g=group_row(update.effective_chat.id)
    if g["welcome_on"]:
        try:
            text=g["welcome"].format(name=new.user.full_name,title=update.effective_chat.title or "")
            await context.bot.send_message(update.effective_chat.id,text)
        except Exception: pass

# ---------------- Message enforcement ----------------

def message_has_url(m):
    if not m: return False
    text=m.text or m.caption or ""
    return bool(re.search(r"(https?://|www\.|t\.me/|telegram\.me/)",text,re.I))

async def enforce(update, context):
    m=update.message
    if not m or update.effective_chat.type not in (ChatType.GROUP,ChatType.SUPERGROUP):
        return
    remember_user(update.effective_user)
    cid=update.effective_chat.id
    uid=update.effective_user.id

    if q("SELECT user_id FROM global_bans WHERE user_id=?",(uid,),True,True):
        if level(cid,uid)<RANKS["ادمن"]:
            await delete_message(m)
        return

    if q("SELECT user_id FROM global_mutes WHERE user_id=?",(uid,),True,True):
        if level(cid,uid)<RANKS["ادمن"]:
            await delete_message(m)
        return

    if level(cid,uid)>=RANKS["ادمن"]:
        return

    bad=False
    if message_has_url(m) and locked(cid,"links"): bad=True
    if m.photo and locked(cid,"photos"): bad=True
    if m.video and locked(cid,"video"): bad=True
    if (m.audio or m.voice) and locked(cid,"audio"): bad=True
    if m.sticker and locked(cid,"stickers"): bad=True
    if m.animation and locked(cid,"animations"): bad=True
    if m.contact and locked(cid,"contacts"): bad=True
    if m.forward_origin and locked(cid,"forward"): bad=True
    text=m.text or ""
    if "@" in text and locked(cid,"mentions"): bad=True
    if m.document and locked(cid,"documents"): bad=True
    if bad:
        await delete_message(m)

# ---------------- Text router ----------------

async def text_router(update, context):
    m=update.message
    if not m or not m.text: return
    remember_user(update.effective_user)
    ensure_group(update.effective_chat)

    text=norm(m.text)
    low=text.lower()

    # Private whisper continuation
    if update.effective_chat.type == ChatType.PRIVATE:
        state=context.user_data.get("whisper")
        if state and not low.startswith(("start","اوامر","لوحه المطور","لوحة المطور")):
            try:
                await context.bot.send_message(
                    state["group"],
                    f"💌 همسة إلى <a href='tg://user?id={state['target']}'>{update.effective_user.first_name}</a>:\n{text}",
                    parse_mode="HTML"
                )
                await m.reply_text("✅ تم إرسال الهمسة إلى المجموعة.")
            except Exception:
                await m.reply_text("❌ تعذر إرسال الهمسة.")
            context.user_data.pop("whisper",None)
            return
        if low in ("لوحة المطور","لوحه المطور"):
            await dev_panel(update,context); return
        if low=="احصائيات":
            await stats(update,context); return
        return

    # Menus
    if low in ("اوامر","الاوامر","قائمة الاوامر","قائمه الاوامر"):
        await commands(update,context); return

    # Exact commands
    exact={
        "رتبتي":my_rank, "معلوماتي":my_info,
        "معلومات المجموعة":group_info,"معلومات المجموعه":group_info,
        "القوانين":show_rules,"الرابط":show_link,
        "حظر":ban,"فك حظر":unban,"طرد":kick,
        "كتم":mute,"فك كتم":unmute,"مسح":clear,
        "الردود":list_replies,"اهمس":whisper,
        "نسبة الحب":love,"تحبه":who_loves,
        "هطف":lambda u,c:fun_percent(u,c,"هطف"),
        "بثر":lambda u,c:fun_percent(u,c,"بثر"),
        "حمار":lambda u,c:fun_percent(u,c,"حمار"),
        "زواج":lambda u,c:fun_percent(u,c,"زواج"),
        "طلاق":lambda u,c:fun_percent(u,c,"طلاق"),
        "نرد":dice_game,
        "لوحة المطور":dev_panel,"لوحه المطور":dev_panel,
        "احصائيات":stats,
        "حظر عام":lambda u,c:global_ban(u,c,True),
        "فك حظر عام":lambda u,c:global_ban(u,c,False),
        "كتم عام":lambda u,c:global_mute(u,c,True),
        "فك كتم عام":lambda u,c:global_mute(u,c,False),
        "مسح المطورين":dev_clear_ranks,
        "الاعدادات":settings_cmd,"الإعدادات":settings_cmd,
        "اضف قناة":add_channel,"حذف قناة":del_channel,
        "قفل":lambda u,c:set_lock(u,c,True),
        "فتح":lambda u,c:set_lock(u,c,False),
    }

    # rank commands
    rank_map={
        "رفع مميز":("مميز",True),"تنزيل مميز":("مميز",False),
        "رفع ادمن":("ادمن",True),"تنزيل ادمن":("ادمن",False),
        "رفع مدير":("مدير",True),"تنزيل مدير":("مدير",False),
        "رفع منشئ":("منشئ",True),"تنزيل منشئ":("منشئ",False),
        "رفع مالك":("مالك",True),"تنزيل مالك":("مالك",False),
        "رفع مالك اساسي":("مالك اساسي",True),"تنزيل مالك اساسي":("مالك اساسي",False),
    }
    if low in rank_map:
        await rank_cmd(update,context,*rank_map[low]); return

    # Settings prefix commands
    if low.startswith("اضف رد عام "):
        await add_reply(update,context,"global"); return
    if low.startswith("اضف رد مميز "):
        await add_reply(update,context,"special"); return
    if low.startswith("اضف رد متعدد "):
        await add_reply(update,context,"multi"); return
    if low.startswith("اضف رد "):
        await add_reply(update,context,"normal"); return
    if low.startswith("حذف رد "):
        await delete_reply(update,context); return
    if low.startswith("ضع قوانين "):
        await set_rules_cmd(update,context); return
    if low.startswith("ضع ترحيب "):
        await set_welcome_cmd(update,context); return
    if low=="تفعيل الترحيب":
        await welcome_toggle(update,context,True); return
    if low=="تعطيل الترحيب":
        await welcome_toggle(update,context,False); return
    if low.startswith("ضع رابط "):
        await set_link(update,context); return
    if low=="حذف الرابط":
        await delete_link(update,context); return
    if low.startswith("اضف قناة "):
        await add_channel(update,context); return
    if low.startswith("حذف قناة "):
        await del_channel(update,context); return
    if low.startswith("اضف امر "):
        await add_command(update,context); return
    if low.startswith("حذف امر "):
        await delete_command(update,context); return

    if low.startswith("قفل "):
        await set_lock(update,context,True); return
    if low.startswith("فتح "):
        await set_lock(update,context,False); return

    if low=="تفعيل الردود":
        await dev_toggle(update,context,"my_replies",True); return
    if low=="تعطيل الردود":
        await dev_toggle(update,context,"my_replies",False); return
    if low=="تفعيل الاحصائيات":
        await dev_toggle(update,context,"stats",True); return
    if low=="تعطيل الاحصائيات":
        await dev_toggle(update,context,"stats",False); return
    if low=="تفعيل الحماية":
        await dev_toggle(update,context,"protection",True); return
    if low=="تعطيل الحماية":
        await dev_toggle(update,context,"protection",False); return

    # Custom command
    if update.effective_chat.type in (ChatType.GROUP,ChatType.SUPERGROUP):
        cc=q("SELECT response FROM custom_commands WHERE chat_id=? AND name=?",
             (update.effective_chat.id,clean_key(text)),True,True)
        if cc:
            await m.reply_text(cc["response"]); return

        g=group_row(update.effective_chat.id)
        if g["my_replies"]:
            rr=q("""SELECT value,kind FROM replies
                    WHERE chat_id=? AND key=? ORDER BY CASE kind
                    WHEN 'special' THEN 0 WHEN 'normal' THEN 1 WHEN 'multi' THEN 2 WHEN 'global' THEN 3 END
                    LIMIT 1""",
                 (update.effective_chat.id,clean_key(text)),True,True)
            if rr:
                if rr["kind"]!="special" or level(update.effective_chat.id,update.effective_user.id)>=RANKS["مميز"]:
                    await m.reply_text(rr["value"])

# ---------------- Callback buttons ----------------

async def callbacks(update, context):
    qy=update.callback_query
    await qy.answer()
    if qy.data=="dev_stats":
        await stats(update,context)
    elif qy.data=="dev_replies":
        rows=q("SELECT COUNT(*) c FROM replies",fetch=True,one=True)["c"]
        await qy.message.reply_text(f"💬 عدد الردود: {rows}\n\nأضف الرد العام من أي مجموعة بصيغة:\nاضف رد عام الكلمة الرد")
    elif qy.data=="dev_games":
        await qy.message.reply_text("🎮 الألعاب: نرد، نسبة الحب، تحبه، هطف، بثر، حمار، زواج، طلاق.")
    elif qy.data=="dev_users":
        rows=q("SELECT COUNT(*) c FROM users",fetch=True,one=True)["c"]
        await qy.message.reply_text(f"👥 المستخدمون المحفوظون: {rows}")

# ---------------- Error handler ----------------

async def errors(update, context):
    log.exception("Unhandled exception", exc_info=context.error)

# ---------------- Main ----------------

def main():
    init_db()
    if not TOKEN:
        raise RuntimeError("ضع BOT_TOKEN في متغيرات البيئة.")
    app=Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("commands",commands))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(ChatMemberHandler(new_member,ChatMemberHandler.CHAT_MEMBER))

    # Enforcement before command/text routing.
    app.add_handler(
        MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, enforce),
        group=0
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_router),
        group=1
    )

    app.add_error_handler(errors)
    log.info("Lina Bot is running.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__=="__main__":
    main()

