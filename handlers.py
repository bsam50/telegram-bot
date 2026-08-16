import random, re
from telegram import ChatPermissions
from telegram.ext import MessageHandler, filters
from database import *
from ranks import rank, level

LOCKS={
"الروابط":"links","الصور":"photos","الفيديو":"videos","الملصقات":"stickers",
"المتحركه":"animations","الصوت":"audio","التوجيه":"forward","التاك":"mentions",
"المعرفات":"usernames","التكرار":"repeat","الكتابة":"text","البوتات":"bots"
}

RANK_NAMES={"مميز","ادمن","مدير","منشئ","مالك","مالك اساسي"}

async def target(update):
    return update.message.reply_to_message.from_user if update.message.reply_to_message else None

async def rank_cmd(u,c,owner):
    if u.effective_chat.type not in ("group","supergroup"): return
    p=u.message.text.split()
    if len(p)!=2 or p[0] not in ("رفع","تنزيل") or p[1] not in RANK_NAMES:return
    t=await target(u)
    if not t:return await u.message.reply_text("⚠️ استخدم الأمر بالرد على العضو.")
    actor=await rank(c.bot,u.effective_chat.id,u.effective_user.id,owner)
    tr=await rank(c.bot,u.effective_chat.id,t.id,owner)
    if level(actor)<=level(tr) or level(actor)<level(p[1]):
        return await u.message.reply_text("❌ لا تملك الصلاحية.")
    if p[0]=="رفع":
        save_rank(u.effective_chat.id,t.id,p[1])
        await u.message.reply_text(f"✅ تم رفع {t.first_name} إلى {p[1]}")
    else:
        delete_rank(u.effective_chat.id,t.id)
        await u.message.reply_text("✅ تم تنزيل الرتبة.")

async def moderation(u,c,owner):
    text=u.message.text.strip()
    if text not in ("حظر","طرد","كتم","الغاء الكتم","الغاء الحظر","تحذير"):return
    if u.effective_chat.type not in ("group","supergroup"):return
    t=await target(u)
    if not t:return await u.message.reply_text("⚠️ استخدم الأمر بالرد.")
    actor=await rank(c.bot,u.effective_chat.id,u.effective_user.id,owner)
    tr=await rank(c.bot,u.effective_chat.id,t.id,owner)
    if level(actor)<=level(tr):return await u.message.reply_text("❌ لا يمكنك تنفيذ الأمر على هذه الرتبة.")
    try:
        chat=u.effective_chat.id
        if text=="حظر": await c.bot.ban_chat_member(chat,t.id)
        elif text=="طرد":
            await c.bot.ban_chat_member(chat,t.id); await c.bot.unban_chat_member(chat,t.id)
        elif text=="كتم": await c.bot.restrict_chat_member(chat,t.id,ChatPermissions(can_send_messages=False))
        elif text=="الغاء الكتم": await c.bot.restrict_chat_member(chat,t.id,ChatPermissions(can_send_messages=True))
        elif text=="الغاء الحظر": await c.bot.unban_chat_member(chat,t.id,only_if_banned=True)
        else:
            con=db(); row=con.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?",(chat,t.id)).fetchone()
            n=(row["count"] if row else 0)+1
            con.execute("INSERT INTO warnings VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET count=excluded.count",(chat,t.id,n));con.commit();con.close()
            if n>=3: await c.bot.ban_chat_member(chat,t.id)
            await u.message.reply_text(f"⚠️ تحذير {n}/3"); return
        await u.message.reply_text("✅ تم التنفيذ.")
    except Exception:
        await u.message.reply_text("❌ تأكد أن البوت مشرف بالصلاحيات المطلوبة.")

async def m1(u,c):
    await u.message.reply_text("👮 م1 — الادمنية\nرفع/تنزيل الرتب\nحظر • طرد • كتم • تقييد • فك القيود\nتحذير • مسح • كشف البوتات")

async def lock_cmd(u,c,owner):
    p=u.message.text.split()
    if len(p)!=2 or p[0] not in ("قفل","فتح"):return
    key=LOCKS.get(p[1])
    if not key:return
    r=await rank(c.bot,u.effective_chat.id,u.effective_user.id,owner)
    if level(r)<2:return await u.message.reply_text("❌ الأمر للأدمنية فقط.")
    set_setting(u.effective_chat.id,key,"on" if p[0]=="قفل" else "off")
    await u.message.reply_text(f"✅ تم {p[0]} {p[1]}.")

async def guard(u,c):
    m=u.message
    if not m or u.effective_chat.type not in ("group","supergroup"):return
    key=None
    if m.text and ("http://" in m.text or "https://" in m.text or "t.me/" in m.text):key="links"
    elif m.photo:key="photos"
    elif m.video:key="videos"
    elif m.animation:key="animations"
    elif m.sticker:key="stickers"
    elif m.voice:key="audio"
    elif m.forward_origin:key="forward"
    if key and setting(u.effective_chat.id,key)=="on":
        try:await m.delete()
        except Exception:pass

async def m2(u,c): await u.message.reply_text("⚙️ م2 — الإعدادات\nالرابط • المالكين • المنشئين • المدراء • الادمنيه • المميزين • القوانين • الترحيب • معلوماتي • المجموعة")

async def m3(u,c): await u.message.reply_text("🔒 م3 — القفل والفتح\nقفل/فتح الروابط • الصور • الفيديو • الملصقات • المتحركة • الصوت • التوجيه • التاك • المعرفات • التكرار • الكتابة • البوتات")

async def m4(u,c): await u.message.reply_text("🎮 م4 — التسلية\nرفع/تنزيل رتب التسلية • زواج • طلاق • زوجي • زوجتي • تتزوجني • اكتموه • نسبة الحب")

async def m5(u,c,owner):
    if u.effective_user.id!=owner:return
    await u.message.reply_text("👑 م5 — Dev\nمعرف المطور • الرتب العامة • الحظر العام • الردود العامة • الرد المتعدد • إضافة لعبة • الكليشة • تحديث • reload")

async def m6(u,c): await u.message.reply_text("🧰 م6 — الخدمات\nنسبة الحب • شبيهي • شبيهتي • البايو • افتاره • قوقل • قرآن • أذكار • شعر • اقتباسات • قصص • كتب")

async def identity(u,c,owner):
    t=await target(u)
    uid=t.id if t else u.effective_user.id
    r=await rank(c.bot,u.effective_chat.id,uid,owner) if u.effective_chat.type in ("group","supergroup") else "عضو"
    await u.message.reply_text(f"🆔 المعرف: {uid}\n👑 الرتبة: {r}")

async def add_reply(u,c,owner):
    if u.effective_user.id!=owner:return
    raw=u.message.text
    body=raw.split("=",1)
    if len(body)!=2:return await u.message.reply_text("الاستخدام: اضف رد كلمة = الرد")
    add_reply(u.effective_chat.id,body[0].replace("اضف رد","",1).strip().lower(),body[1].strip())
    await u.message.reply_text("✅ تم إضافة الرد.")

async def add_multi_reply(u,c,owner):
    if u.effective_user.id!=owner:return
    body=u.message.text.split("=",1)
    if len(body)!=2:return await u.message.reply_text("الاستخدام: اضف رد متعدد كلمة = رد1 | رد2 | رد3")
    trigger=body[0].replace("اضف رد متعدد","",1).strip().lower()
    add_multi(u.effective_chat.id,trigger,[x.strip() for x in body[1].split("|") if x.strip()])
    await u.message.reply_text("✅ تم إضافة الرد المتعدد.")

async def add_game_cmd(u,c,owner):
    if u.effective_user.id!=owner:return
    body=u.message.text.split("=",1)
    if len(body)!=2:return await u.message.reply_text("الاستخدام: اضف لعبة اسم = نص اللعبة")
    name=body[0].replace("اضف لعبة","",1).strip().lower()
    add_game(u.effective_chat.id,name,body[1].strip())
    await u.message.reply_text("🎮 تم إضافة اللعبة.")

async def dynamic(u,c):
    if not u.message:return
    text=u.message.text.strip().lower()
    r=get_reply(u.effective_chat.id,text)
    if r: return await u.message.reply_text(r)
    rs=get_multi(u.effective_chat.id,text)
    if rs:return await u.message.reply_text(random.choice(rs))
    g=get_game(u.effective_chat.id,text)
    if g:return await u.message.reply_text(g)
    if text in ("نسبة الحب","نسبه الحب"):
        return await u.message.reply_text(f"❤️ نسبة الحب: {random.randint(1,100)}%")
    if text in ("نكته","نكتة","ضحكني"):
        return await u.message.reply_text(random.choice(["😂 الله يعين على هالنكتة.","🤣 اليوم الضحك مجاني."]))

async def set_toggle(u,c,owner):
    p=u.message.text.split(maxsplit=1)
    if len(p)!=2:return
    action,name=p
    if action not in ("تفعيل","تعطيل"):return
    r=await rank(c.bot,u.effective_chat.id,u.effective_user.id,owner)
    if level(r)<2:return
    aliases={"الترحيب":"welcome","الردود":"replies","الحمايه":"protection","التكرار":"repeat","التحميل":"downloads"}
    if name in aliases:
        set_setting(u.effective_chat.id,aliases[name],"on" if action=="تفعيل" else "off")
        await u.message.reply_text("✅ تم تحديث الإعداد.")

async def dev_help(u,c,owner):
    if u.effective_user.id!=owner:return
    await u.message.reply_text(
        "👑 أوامر المطور:\\n"
        "معرف المطور\\nمعرف المالك\\nمعرفي\\nرتبتي\\n"
        "اضف رد كلمة = رد\\nاضف رد متعدد كلمة = رد1 | رد2\\n"
        "مسح رد كلمة\\nاضف لعبة اسم = نص\\n"
        "تفعيل/تعطيل الترحيب والردود والحماية\\n"
        "تحديث • reload"
    )

def register_all(app,owner):
    app.add_handler(MessageHandler(filters.Regex(r"^م1$"),m1),0)
    app.add_handler(MessageHandler(filters.Regex(r"^م2$"),m2),0)
    app.add_handler(MessageHandler(filters.Regex(r"^م3$"),m3),0)
    app.add_handler(MessageHandler(filters.Regex(r"^م4$"),m4),0)
    app.add_handler(MessageHandler(filters.Regex(r"^م5$"),lambda u,c:m5(u,c,owner)),0)
    app.add_handler(MessageHandler(filters.Regex(r"^م6$"),m6),0)
    app.add_handler(MessageHandler(filters.Regex(r"^(معرفي|ايدي|معرف المالك|معرف المطور)$"),lambda u,c:identity(u,c,owner)),1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,lambda u,c:rank_cmd(u,c,owner)),2)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,lambda u,c:moderation(u,c,owner)),3)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,lambda u,c:lock_cmd(u,c,owner)),4)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,lambda u,c:set_toggle(u,c,owner)),5)
    app.add_handler(MessageHandler(filters.Regex(r"^اضف رد "),lambda u,c:add_reply(u,c,owner)),6)
    app.add_handler(MessageHandler(filters.Regex(r"^اضف رد متعدد "),lambda u,c:add_multi_reply(u,c,owner)),6)
    app.add_handler(MessageHandler(filters.Regex(r"^اضف لعبة "),lambda u,c:add_game_cmd(u,c,owner)),6)
    app.add_handler(MessageHandler(filters.Regex(r"^اوامر المطور$"),lambda u,c:dev_help(u,c,owner)),6)
    app.add_handler(MessageHandler(filters.ALL,guard),7)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,dynamic),8)
