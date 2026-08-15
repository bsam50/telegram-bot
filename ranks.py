from database import get_saved_rank

LEVELS = {
    "عضو": 0, "مميز": 1, "ادمن": 2, "مدير": 3,
    "منشئ": 4, "مالك": 5, "مالك اساسي": 6
}

async def get_rank(bot, chat_id, user_id, owner_id=0):
    if user_id == owner_id:
        return "مالك اساسي"
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status == "creator":
            return "مالك اساسي"
        if member.status == "administrator":
            saved = get_saved_rank(chat_id, user_id)
            return saved or "ادمن"
    except Exception:
        pass
    return get_saved_rank(chat_id, user_id) or "عضو"

async def rank_text(bot, chat_id, user_id, owner_id=0):
    return f"👑 رتبتك: {await get_rank(bot, chat_id, user_id, owner_id)}"

def can_promote(actor, target, new_rank):
    return (
        LEVELS.get(actor, 0) >= LEVELS.get(new_rank, 0)
        and LEVELS.get(actor, 0) > LEVELS.get(target, 0)
    )
