import os,re,sqlite3,random,time
from dotenv import load_dotenv
from telegram import Update,ChatPermissions,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ContextTypes,filters

load_dotenv()
TOKEN=os.getenv("BOT_TOKEN","").strip()
OWNER_ID=int(os.getenv("OWNER_ID","0") or 0)
DEV_IDS={int(x) for x in os.getenv("DEV_IDS","").split(",") if x.strip().isdigit()}
if OWNER_ID: DEV_IDS.add(OWNER_ID)
DB="bot_data.db"

RANKS={"عضو":0,"مميز":1,"ادمن":2,"مدير":3,"منشئ":4,"مالك":5,"مالك اساسي":6}
ALIASES={"الأدمن":"ادمن","الادمن":"ادمن","المالك":"مالك","المالك الأساسي":"مالك اساسي","المالك الاساسي":"مالك اساسي"}
LOCKS=["جمثون","السب","الايرانيه","الكتابة","الاباحي","تعديل الميديا","التعديل","الفيديو","الصور","الملصقات","المتحركه","الدردشه","الروابط","التاك","البوتات","المعرفات","الكلايش","التكرار","التوجيه","الانلاين","الجهات","الدخول","الصوت","الفويس","التوجيه بالتقييد","الروابط بالتقييد","المتحركه بالتقييد","الصور بالتقييد","الفيديو بالتقييد"]
FEATURES=["ضافني","الاذكار","الثنائي","افتاري","التسليه","الكت","الترحيب","الردود","الانذار","التحذير","الايدي","الرابط","اطردني","الحظر","الرفع","التنزيل","التحويل","الحمايه","المنشن","وضع الاقتباسات","الخدميه","اليوتيوب","الايدي بالصوره","التحقق","ردود السورس","ردود MY","الاحصائيات"]

def DBconn():
    c=sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS ranks(chat,user,rank,PRIMARY KEY(chat,user));
    CREATE TABLE IF NOT EXISTS settings(chat,key,value,PRIMARY KEY(chat,key));
    CREATE TABLE IF NOT EXISTS replies(chat,key,value,PRIMARY KEY(chat,key));
    CREATE TABLE IF NOT EXISTS multi(chat,key,value,PRIMARY KEY(chat,key));
    CREATE TABLE IF NOT EXISTS special(chat,key,value,PRIMARY KEY(chat,key));
    CREATE TABLE IF NOT EXISTS global_replies(key,value,PRIMARY KEY(key));
    CREATE TABLE IF NOT EXISTS global_multi(key,value,PRIMARY KEY(key));
    CREATE TABLE IF NOT EXISTS global_special(key,value,PRIMARY KEY(key));
    CREATE TABLE IF NOT EXISTS games(key,value,PRIMARY KEY(key));
    CREATE TABLE IF NOT EXISTS warnings(chat,user,count,PRIMARY KEY(chat,user));
    CREATE TABLE IF NOT EXISTS global_bans(user PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS global_mutes(user PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS whispers(chat,sender,target,text,created);
    CREATE TABLE IF NOT EXISTS money(chat,user,coins,bank,PRIMARY KEY(chat,user));
    CREATE TABLE IF NOT EXISTS marriages(chat,user1,user2,PRIMARY KEY(chat,user1));
    CREATE TABLE IF NOT EXISTS fun(chat,user,kind,PRIMARY KEY(chat,user,kind));
    """);c.commit();return c
DBconn().close()

def one(sql,a=()):
    c=DBconn();r=c.execute(sql,a).fetchone();c.close();return r
def many(sql,a=()):
    c=DBconn();r=c.execute(sql,a).fetchall();c.close();return r
def put(sql,a=()):
    c=DBconn();c.execute(sql,a);c.commit();c.close()
def setv(chat,key,value):put("INSERT OR REPLACE INTO settings VALUES(?,?,?)",(chat,key,str(value)))
def getv(chat,key,default="0"):
    r=one("SELECT value FROM settings WHERE chat=? AND key=?",(chat,key));return r[0] if r else default
def getrank(chat,user):
    r=one("SELECT rank FROM ranks WHERE chat=? AND user=?",(chat,user));return r[0] if r else "عضو"
def isdev(user):return user in DEV_IDS
async def is_admin(u,c):
    try:
        m=await c.bot.get_chat_member(u.effective_chat.id,u.effective_user.id)
        return m.status in (ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.OWNER)
    except:return False
async def can(u,c,needed):
    if isdev(u.effective_user.id):return True
    if RANKS.get(getrank(u.effective_chat.id,u.effective_user.id),0)>=needed:return True
    return needed<=3 and await is_admin(u,c)
def target(u):return u.message.reply_to_message.from_user if u.message and u.message.reply_to_message else None
async def say(u,text,**kw):return await u.message.reply_text(text,**kw)

def menu():
    return InlineKeyboardMarkup([
    [InlineKeyboardButton("م1 الإدارة",callback_data="m1"),InlineKeyboardButton("م2 الإعدادات",callback_data="m2")],
    [InlineKeyboardButton("م3 القفل والفتح",callback_data="m3"),InlineKeyboardButton("م4 التسلية",callback_data="m4")],
    [InlineKeyboardButton("م5 المطور",callback_data="m5"),InlineKeyboardButton("م6 الخدمات",callback_data="m6")]])

MENUS={
"m1":"👑 م1 الإدارة\nرفع/تنزيل الرتب • حظر • طرد • كتم • تقييد • تحذير • معلوماتي • رتبتي • الرتب",
"m2":"⚙️ م2 الإعدادات\nالرابط • القوانين • الترحيب • الردود • الردود المتعددة • الردود المميزة • الهمسات",
"m3":"🔒 م3 القفل والفتح\nقفل/فتح المحتوى • قفل الكل • فتح الكل • تفعيل/تعطيل الميزات",
"m4":"🎮 م4 التسلية\nنسبة الحب • زواج • طلاق • بنك • راتب • إيداع • سحب • رتب التسلية",
"m5":"👨‍💻 م5 المطور\nإدارة الردود العامة والمميزة والمتعددة • الألعاب • الحظر العام • الكتم العام • الإحصائيات",
"m6":"🛠️ م6 الخدمات\nقوقل • قرآن • أذكار • اقتباسات • آيدي"
}

async def start(u,c):
    if u.effective_chat.type=="private":
        if isdev(u.effective_user.id):
            return await dev_panel(u)
        return await say(u,"👋 أهلاً بك.\nهذا البوت يعمل داخل المجموعات.")
    # group: don't dump admin commands to ordinary members
    r=getrank(u.effective_chat.id,u.effective_user.id)
    if r=="عضو" and not await is_admin(u,c):
        return await say(u,"👋 أهلاً بك.\nاكتب «رتبتي» لمعرفة رتبتك.")
    return await say(u,"👋 اختر قائمة الأوامر:",reply_markup=menu())

async def cb(u,c):
    x=u.callback_query;await x.answer()
    if x.data=="home":return await x.edit_message_text("اختر القائمة:",reply_markup=menu())
    if x.data in MENUS:
        return await x.edit_message_text(MENUS[x.data],reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع",callback_data="home")]]))

async def dev_panel(u):
    kb=InlineKeyboardMarkup([
    [InlineKeyboardButton("➕ رد عام",callback_data="dev_add_global"),InlineKeyboardButton("⭐ رد مميز",callback_data="dev_add_special")],
    [InlineKeyboardButton("💬 رد متعدد عام",callback_data="dev_add_multi"),InlineKeyboardButton("🎮 الألعاب",callback_data="dev_games")],
    [InlineKeyboardButton("📋 الردود",callback_data="dev_lists"),InlineKeyboardButton("📊 الإحصائيات",callback_data="dev_stats")]])
    return await say(u,"👨‍💻 لوحة المطور\n\nمن هنا يمكنك إدارة الردود والألعاب والميزات.",reply_markup=kb)

async def dev_callbacks(u,c):
    x=u.callback_query
    if not x.data.startswith("dev_"):return False
    await x.answer()
    if not isdev(u.effective_user.id):return True
    if x.data=="dev_add_global":
        return await x.edit_message_text("➕ لإضافة رد عام:\nأرسل رسالة ثم اعمل ردًا عليها واكتب:\nاضف رد عام الكلمة")
    if x.data=="dev_add_special":
        return await x.edit_message_text("⭐ لإضافة رد مميز:\nأرسل رسالة ثم اعمل ردًا عليها واكتب:\nاضف رد مميز الكلمة")
    if x.data=="dev_add_multi":
        return await x.edit_message_text("💬 لإضافة رد متعدد عام:\nاضف رد متعدد عام الكلمة — بالرد على الرسالة")
    if x.data=="dev_games":
        return await x.edit_message_text("🎮 إدارة الألعاب من الخاص:\nاضف لعبة اسم اللعبة | نص اللعبة\nمسح لعبة اسم اللعبة\nالالعاب")
    if x.data=="dev_lists":
        a="\n".join(x[0] for x in many("SELECT key FROM global_replies")) or "لا توجد ردود عامة"
        b="\n".join(x[0] for x in many("SELECT key FROM global_special")) or "لا توجد ردود مميزة"
        return await x.edit_message_text("📋 العامة:\n"+a+"\n\n⭐ المميزة:\n"+b)
    if x.data=="dev_stats":
        return await x.edit_message_text(f"📊 الردود العامة: {one('SELECT COUNT(*) FROM global_replies')[0]}\n⭐ المميزة: {one('SELECT COUNT(*) FROM global_special')[0]}\n💬 المتعددة: {one('SELECT COUNT(*) FROM global_multi')[0]}\n🎮 الألعاب: {one('SELECT COUNT(*) FROM games')[0]}\n💌 الهمسات: {one('SELECT COUNT(*) FROM whispers')[0]}")
    return True

async def callbacks(u,c):
    if await dev_callbacks(u,c):return
    await cb(u,c)

async def developer(u,c):
    if not isdev(u.effective_user.id):return await say(u,"❌ هذا الأمر للمطور فقط.")
    try:
        user=await c.bot.get_chat(OWNER_ID)
        username="@"+user.username if user.username else "بدون يوزر"
        text=f"👨‍💻 المطور الأساسي\n\n👤 الاسم: {user.full_name}\n🔗 اليوزر: {username}\n🆔 الآيدي: {OWNER_ID}"
        p=await c.bot.get_user_profile_photos(OWNER_ID,limit=1)
        if p.total_count:return await u.message.reply_photo(p.photos[0][-1].file_id,caption=text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لوحة المطور",callback_data="dev_home")]]))
        return await say(u,text)
    except:return await say(u,f"👨‍💻 المطور الأساسي\n🆔 الآيدي: {OWNER_ID}")

async def rank_cmd(u,c,action,r):
    if not await can(u,c,5):return await say(u,"❌ تحتاج رتبة المالك.")
    t=target(u)
    if not t:return await say(u,"↩️ استخدم الأمر بالرد على العضو.")
    if action=="رفع":put("INSERT OR REPLACE INTO ranks VALUES(?,?,?)",(u.effective_chat.id,t.id,r))
    else:put("DELETE FROM ranks WHERE chat=? AND user=?",(u.effective_chat.id,t.id))
    return await say(u,f"✅ تم {action} {r}.")

async def moderation(u,c,action):
    if not await can(u,c,3):return await say(u,"❌ ليس لديك صلاحية.")
    t=target(u)
    if not t:return await say(u,"↩️ استخدم الأمر بالرد.")
    cid=u.effective_chat.id
    try:
        if action=="حظر":await c.bot.ban_chat_member(cid,t.id)
        elif action=="طرد":await c.bot.ban_chat_member(cid,t.id);await c.bot.unban_chat_member(cid,t.id)
        elif action in ("كتم","تقييد"):await c.bot.restrict_chat_member(cid,t.id,ChatPermissions(can_send_messages=False))
        elif action in ("حظر الغاء","فك الحظر","الغاء الحظر"):await c.bot.unban_chat_member(cid,t.id)
        else:await c.bot.restrict_chat_member(cid,t.id,ChatPermissions(can_send_messages=True,can_send_other_messages=True,can_add_web_page_previews=True))
        return await say(u,"✅ تم التنفيذ.")
    except:return await say(u,"❌ تعذر التنفيذ. تأكد من صلاحيات البوت.")

async def whisper(u,c,text):
    t=target(u);body=""
    if t:body=text[5:].strip()
    else:
        m=re.match(r"^همسة\s+(@\w+)\s+(.+)$",text,re.S)
        if m:
            body=m.group(2)
            try:
                for a in await c.bot.get_chat_administrators(u.effective_chat.id):
                    if a.user.username and a.user.username.lower()==m.group(1)[1:].lower():t=a.user;break
            except:pass
    if not t or not body:return await say(u,"💌 الاستخدام: همسة @اليوزر النص أو استخدم الأمر بالرد.")
    put("INSERT INTO whispers VALUES(?,?,?,?,?)",(u.effective_chat.id,u.effective_user.id,t.id,body,int(time.time())))
    try:
        await c.bot.send_message(t.id,f"💌 همسة من {u.effective_user.full_name}:\n\n{body}")
        return await say(u,"✅ تم إرسال الهمسة.")
    except:return await say(u,"⚠️ لم يتم إرسالها. يجب أن يكون العضو قد بدأ محادثة مع البوت.")

def media(m):
    if m.photo:return "الصور"
    if m.video:return "الفيديو"
    if m.audio:return "الصوت"
    if m.voice:return "الفويس"
    if m.animation:return "المتحركه"
    if m.sticker:return "الملصقات"
    if m.contact:return "الجهات"
    if m.forward_origin:return "التوجيه"
    if m.entities and any(e.type in ("url","text_link") for e in m.entities):return "الروابط"
    if m.entities and any(e.type=="mention" for e in m.entities):return "التاك"
    return None

async def protection(u,c):
    m=u.effective_message
    if not m or u.effective_chat.type=="private" or isdev(u.effective_user.id):return
    k=media(m)
    if k and getv(u.effective_chat.id,"lock:"+k)=="1":
        try:await m.delete()
        except:pass
    if m.text and getv(u.effective_chat.id,"lock:التكرار")=="1":
        if c.chat_data.get("last")==m.text:
            try:await m.delete()
            except:pass
        c.chat_data["last"]=m.text

async def engine(u,c):
    if not u.message or not u.message.text:return
    t=u.message.text.strip();cid=u.effective_chat.id;uid=u.effective_user.id

    if u.effective_chat.type=="private":
        if not isdev(uid):return
        # Developer-only command console.
        m=re.match(r"^اضف رد عام\s+(.+)$",t)
        if m and u.message.reply_to_message and u.message.reply_to_message.text:
            put("INSERT OR REPLACE INTO global_replies VALUES(?,?)",(m.group(1),u.message.reply_to_message.text));return await say(u,"✅ تمت إضافة الرد العام.")
        m=re.match(r"^اضف رد مميز\s+(.+)$",t)
        if m and u.message.reply_to_message and u.message.reply_to_message.text:
            put("INSERT OR REPLACE INTO global_special VALUES(?,?)",(m.group(1),u.message.reply_to_message.text));return await say(u,"⭐ تمت إضافة الرد المميز.")
        m=re.match(r"^اضف رد متعدد عام\s+(.+)$",t)
        if m and u.message.reply_to_message and u.message.reply_to_message.text:
            put("INSERT OR REPLACE INTO global_multi VALUES(?,?)",(m.group(1),u.message.reply_to_message.text));return await say(u,"💬 تمت إضافة الرد المتعدد العام.")
        m=re.match(r"^مسح رد عام\s+(.+)$",t)
        if m:put("DELETE FROM global_replies WHERE key=?",(m.group(1),));return await say(u,"🗑️ تم المسح.")
        m=re.match(r"^مسح رد مميز\s+(.+)$",t)
        if m:put("DELETE FROM global_special WHERE key=?",(m.group(1),));return await say(u,"🗑️ تم المسح.")
        m=re.match(r"^اضف لعبة\s+(.+?)\s*\|\s*(.+)$",t)
        if m:put("INSERT OR REPLACE INTO games VALUES(?,?)",(m.group(1),m.group(2)));return await say(u,"🎮 تمت إضافة اللعبة.")
        m=re.match(r"^مسح لعبة\s+(.+)$",t)
        if m:put("DELETE FROM games WHERE key=?",(m.group(1),));return await say(u,"🗑️ تم مسح اللعبة.")
        if t=="الالعاب":
            return await say(u,"\n".join("🎮 "+x[0] for x in many("SELECT key FROM games")) or "لا توجد ألعاب.")
        if t in ("المطور","لوحة المطور","/start"):return await dev_panel(u)
        return await say(u,"❌ أمر المطور غير معروف.\nاكتب /start لفتح لوحة المطور.")

    # group: ordinary member gets no command menu
    if t=="رتبتي":return await say(u,f"👑 رتبتك: {getrank(cid,uid)}")
    if t=="معلوماتي":return await say(u,f"👤 {u.effective_user.full_name}\n🆔 {uid}\n🔗 @{u.effective_user.username or 'بدون'}\n👑 {getrank(cid,uid)}")
    if t=="المطور":return await developer(u,c)
    if t=="الرتب":
        if getrank(cid,uid)=="عضو" and not await is_admin(u,c):return
        rows=many("SELECT user,rank FROM ranks WHERE chat=?",(cid,))
        return await say(u,"\n".join(f"{x} — {r}" for x,r in rows) or "لا توجد رتب.")
    if t=="المالك":
        rows=many("SELECT user,rank FROM ranks WHERE chat=? AND rank IN ('مالك','مالك اساسي')",(cid,))
        return await say(u,"\n".join(f"👑 {x} — {r}" for x,r in rows) or "لا يوجد مالك مسجل.")
    if t in ("القائمة","م1"):
        if getrank(cid,uid)=="عضو" and not await is_admin(u,c):return
        return await say(u,"اختر القائمة:",reply_markup=menu())

    for r in RANKS:
        if r!="عضو":
            if t==f"رفع {r}":return await rank_cmd(u,c,"رفع",r)
            if t==f"تنزيل {r}":return await rank_cmd(u,c,"تنزيل",r)
    if t.startswith("رفع ") and t[4:] in ALIASES:return await rank_cmd(u,c,"رفع",ALIASES[t[4:]])

    if t.startswith("همسة"):return await whisper(u,c,t)

    m=re.match(r"^(قفل|فتح)\s+(.+)$",t)
    if m:
        if not await can(u,c,3):return
        k=m.group(2)
        if k=="الكل":
            for x in LOCKS:setv(cid,"lock:"+x,"1" if m.group(1)=="قفل" else "0")
        else:setv(cid,"lock:"+k,"1" if m.group(1)=="قفل" else "0")
        return await say(u,f"✅ تم {m.group(1)} {k}.")
    m=re.match(r"^(تفعيل|تعطيل)\s+(.+)$",t)
    if m:
        if not await can(u,c,2):return
        setv(cid,"feature:"+m.group(2),"1" if m.group(1)=="تفعيل" else "0")
        return await say(u,f"⚙️ تم {m.group(1)} {m.group(2)}.")

    if t=="الرابط":
        try:
            if getv(cid,"الرابط","")=="":setv(cid,"الرابط",await c.bot.create_chat_invite_link(cid).then if False else "")
        except:pass
        saved=getv(cid,"الرابط","")
        if not saved:
            try:saved=(await c.bot.create_chat_invite_link(cid)).invite_link;setv(cid,"الرابط",saved)
            except:saved="❌ تعذر إنشاء الرابط. أعطِ البوت صلاحية دعوة المستخدمين."
        return await say(u,"🔗 "+saved)
    m=re.match(r"^(ضع|تعيين)\s+(الرابط|القوانين|الترحيب)\s+(.+)$",t,re.S)
    if m:
        if not await can(u,c,3):return
        setv(cid,m.group(2),m.group(3));return await say(u,"✅ تم الحفظ.")
    if t=="القوانين":return await say(u,getv(cid,"القوانين","لا توجد قوانين."))

    m=re.match(r"^اضف رد مميز\s+(.+)$",t)
    if m:
        if not await can(u,c,2):return await say(u,"❌ تحتاج رتبة.")
        if not u.message.reply_to_message or not u.message.reply_to_message.text:return await say(u,"↩️ استخدم الأمر بالرد على الرسالة.")
        put("INSERT OR REPLACE INTO special VALUES(?,?,?)",(cid,m.group(1),u.message.reply_to_message.text));return await say(u,"⭐ تمت إضافة الرد المميز.")
    m=re.match(r"^اضف رد\s+(.+)$",t)
    if m:
        if not await can(u,c,2):return await say(u,"❌ تحتاج رتبة.")
        if not u.message.reply_to_message or not u.message.reply_to_message.text:return await say(u,"↩️ استخدم الأمر بالرد.")
        put("INSERT OR REPLACE INTO replies VALUES(?,?,?)",(cid,m.group(1),u.message.reply_to_message.text));return await say(u,"✅ تمت إضافة الرد.")
    m=re.match(r"^اضف رد متعدد\s+(.+)$",t)
    if m:
        if not await can(u,c,2):return await say(u,"❌ تحتاج رتبة.")
        if not u.message.reply_to_message or not u.message.reply_to_message.text:return await say(u,"↩️ استخدم الأمر بالرد.")
        put("INSERT OR REPLACE INTO multi VALUES(?,?,?)",(cid,m.group(1),u.message.reply_to_message.text));return await say(u,"💬 تمت إضافة الرد المتعدد.")

    if t in ("حظر","طرد","كتم","تقييد","فك الحظر","الغاء الحظر","فك الكتم","الغاء الكتم","فك التقييد"):return await moderation(u,c,t)
    if t in ("نسبة الحب","نسبه الحب"):return await say(u,f"❤️ نسبة الحب: {random.randint(0,100)}%")
    if t=="اذكار":return await say(u,"سبحان الله • الحمد لله • الله أكبر • أستغفر الله")
    if t in ("قرآن","قران"):return await say(u,"﴿إِنَّ مَعَ الْعُسْرِ يُسْرًا﴾")
    if t=="اقتباسات":return await say(u,"ابدأ بخطوة صغيرة واستمر.")

    if t in ("بنك","رصيد","رصيدي"):
        x=one("SELECT coins,bank FROM money WHERE chat=? AND user=?",(cid,uid)) or (0,0);return await say(u,f"💰 المحفظة: {x[0]}\n🏦 البنك: {x[1]}")
    if t=="راتب":
        x=one("SELECT coins,bank FROM money WHERE chat=? AND user=?",(cid,uid)) or (0,0);put("INSERT OR REPLACE INTO money VALUES(?,?,?,?)",(cid,uid,x[0]+100,x[1]));return await say(u,"💵 تم صرف 100.")
    m=re.match(r"^(ايداع|سحب)\s+(\d+)$",t)
    if m:
        n=int(m.group(2));x=one("SELECT coins,bank FROM money WHERE chat=? AND user=?",(cid,uid)) or (0,0);coins,bank=x
        if m.group(1)=="ايداع" and n<=coins:coins-=n;bank+=n
        elif m.group(1)=="سحب" and n<=bank:bank-=n;coins+=n
        else:return await say(u,"❌ الرصيد غير كافٍ.")
        put("INSERT OR REPLACE INTO money VALUES(?,?,?,?)",(cid,uid,coins,bank));return await say(u,"✅ تمت العملية.")

    # Global special reply works only for ranked users.
    if getrank(cid,uid)!="عضو" or await is_admin(u,c):
        x=one("SELECT value FROM global_special WHERE key=?",(t,))
        if x:return await say(u,x[0])
    x=one("SELECT value FROM replies WHERE chat=? AND key=?",(cid,t)) or one("SELECT value FROM global_replies WHERE key=?",(t,))
    if x:return await say(u,x[0])
    x=one("SELECT value FROM multi WHERE chat=? AND key=?",(cid,t)) or one("SELECT value FROM global_multi WHERE key=?",(t,))
    if x:return await say(u,x[0])

async def message(update,ctx):
    await protection(update,ctx)
    await engine(update,ctx)

def main():
    if not TOKEN:raise SystemExit("BOT_TOKEN غير موجود.")
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":main()
