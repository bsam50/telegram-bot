from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import ChatPermissions
from main import app
from .storage import group_enabled, set_group_enabled, get_rank, set_rank, del_rank, redis

async def is_admin(m):
    try:
        member = await app.get_chat_member(m.chat.id, m.from_user.id)
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False

async def target(m):
    if m.reply_to_message and m.reply_to_message.from_user:
        return m.reply_to_message.from_user
    parts = (m.text or "").split()
    if len(parts) > 1:
        try:
            return await app.get_users(parts[1].lstrip("@"))
        except Exception:
            return None
    return None

@app.on_message(filters.group & filters.text)
async def commands(_, m):
    text = (m.text or "").strip()
    if text == "تفعيل":
        if await is_admin(m):
            await set_group_enabled(m.chat.id, True)
            await m.reply("✅ تم تفعيل المجموعة بنجاح.")
        return
    if not await group_enabled(m.chat.id):
        return
    if text == "تعطيل":
        if await is_admin(m):
            await set_group_enabled(m.chat.id, False)
            await m.reply("⛔ تم تعطيل البوت في المجموعة.")
        return
    if text in ("معلوماتي", "رتبتي"):
        await m.reply(f"👤 رتبتك: **{await get_rank(m.chat.id, m.from_user.id)}**")
        return
    if text == "القوانين":
        await m.reply("📋 قوانين المجموعة:\n• احترام الأعضاء\n• منع الروابط المزعجة\n• الالتزام بقرارات الإدارة.")
        return
    if text in ("طرد","حظر","كتم","فك حظر","فك كتم","تقييد","فك تقييد","تحذير","مسح التحذيرات"):
        if not await is_admin(m):
            return
        u = await target(m)
        if not u:
            return await m.reply("↩️ قم بالرد على العضو أو اكتب معرفه.")
        try:
            if text == "طرد":
                await app.ban_chat_member(m.chat.id, u.id)
                await app.unban_chat_member(m.chat.id, u.id)
                return await m.reply("🚪 تم طرد العضو.")
            if text == "حظر":
                await app.ban_chat_member(m.chat.id, u.id)
                return await m.reply("🚫 تم حظر العضو.")
            if text == "فك حظر":
                await app.unban_chat_member(m.chat.id, u.id)
                return await m.reply("✅ تم فك الحظر.")
            if text in ("كتم","تقييد"):
                await app.restrict_chat_member(m.chat.id, u.id, ChatPermissions())
                await redis.sadd(f"muted:{m.chat.id}", u.id)
                return await m.reply("🔇 تم كتم العضو.")
            if text in ("فك كتم","فك تقييد"):
                await app.restrict_chat_member(m.chat.id, u.id, ChatPermissions(can_send_messages=True))
                await redis.srem(f"muted:{m.chat.id}", u.id)
                return await m.reply("🔊 تم فك الكتم.")
            if text == "تحذير":
                n = await redis.incr(f"warn:{m.chat.id}:{u.id}")
                return await m.reply(f"⚠️ تم تحذير العضو. التحذيرات: {n}")
            if text == "مسح التحذيرات":
                await redis.delete(f"warn:{m.chat.id}:{u.id}")
                return await m.reply("✅ تم مسح التحذيرات.")
        except Exception as e:
            return await m.reply(f"❌ لم أستطع تنفيذ الأمر: {e}")

    if text.startswith(("رفع ","تنزيل ")):
        if not await is_admin(m):
            return
        u = await target(m)
        if not u: return await m.reply("↩️ رد على العضو.")
        rank = text.split(maxsplit=1)[1]
        rank = rank.replace("تنزيل ","")
        if text.startswith("رفع "):
            await set_rank(m.chat.id, u.id, rank)
            await m.reply(f"👑 تم رفع {u.mention} إلى {rank}.")
        else:
            await del_rank(m.chat.id, u.id)
            await m.reply(f"✅ تم تنزيل رتبة {u.mention}.")
