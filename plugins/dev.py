import os, platform, psutil, json
from datetime import datetime
from pyrogram import filters
from main import app
from config import OWNER_ID, BOT_NAME, BOT_CHANNEL
from .storage import redis

def owner(m): return m.from_user and m.from_user.id == OWNER_ID

@app.on_message(filters.private & filters.text, group=100)
async def developer(_, m):
    if not owner(m): return
    t = (m.text or "").strip()
    if t == "لوحة المطور":
        return await m.reply(
            "🛠️ لوحة تحكم المطور\n\n"
            "📊 الإحصائيات\n📢 إذاعة بالخاص\n📢 إذاعة بالقروبات\n"
            "📦 نسخة المستخدمين\n📦 نسخة المجموعات\n🖥️ السيرفر\n🔄 تحديث"
        )
    if t == "الإحصائيات":
        users = await redis.scard("users")
        groups = await redis.scard("groups")
        return await m.reply(f"📊 الإحصائيات\n\n👥 المستخدمون: {users}\n👥 المجموعات: {groups}")
    if t == "السيرفر":
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return await m.reply(
            f"🖥️ معلومات السيرفر\n\n"
            f"النظام: {platform.system()} {platform.release()}\n"
            f"RAM: {vm.used//(1024**2)} / {vm.total//(1024**2)} MB ({vm.percent}%)\n"
            f"التخزين: {disk.used//(1024**3)} / {disk.total//(1024**3)} GB ({disk.percent}%)"
        )
    if t == "نسخة المستخدمين":
        users = [int(x) async for x in redis.sscan_iter("users")]
        path="/tmp/users.json"
        with open(path,"w",encoding="utf-8") as f: json.dump(users,f,ensure_ascii=False,indent=2)
        return await m.reply_document(path, caption="📦 نسخة المستخدمين")
    if t == "نسخة المجموعات":
        groups = [int(x) async for x in redis.sscan_iter("groups")]
        path="/tmp/groups.json"
        with open(path,"w",encoding="utf-8") as f: json.dump(groups,f,ensure_ascii=False,indent=2)
        return await m.reply_document(path, caption="📦 نسخة المجموعات")
