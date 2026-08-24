from pyrogram import filters
from main import app
from .storage import redis

@app.on_message(filters.group, group=200)
async def register(_, m):
    try:
        await redis.sadd("groups", m.chat.id)
        if m.from_user:
            await redis.sadd("users", m.from_user.id)
    except Exception:
        pass
