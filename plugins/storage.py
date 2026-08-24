import json
from redis.asyncio import Redis
from config import REDIS_URL

redis = Redis.from_url(REDIS_URL, decode_responses=True)

async def get_json(key, default=None):
    value = await redis.get(key)
    if value is None:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default

async def set_json(key, value):
    await redis.set(key, json.dumps(value, ensure_ascii=False))

async def group_enabled(chat_id):
    return bool(await redis.get(f"group:{chat_id}:enabled"))

async def set_group_enabled(chat_id, enabled=True):
    if enabled:
        await redis.set(f"group:{chat_id}:enabled", "1")
    else:
        await redis.delete(f"group:{chat_id}:enabled")

async def get_rank(chat_id, user_id):
    if user_id == __import__("config").OWNER_ID:
        return "المطور الأساسي"
    return await redis.get(f"rank:{chat_id}:{user_id}") or "عضو"

async def set_rank(chat_id, user_id, rank):
    await redis.set(f"rank:{chat_id}:{user_id}", rank)

async def del_rank(chat_id, user_id):
    await redis.delete(f"rank:{chat_id}:{user_id}")
