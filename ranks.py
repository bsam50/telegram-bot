from database import saved_rank

LEVELS={"عضو":0,"مميز":1,"ادمن":2,"مدير":3,"منشئ":4,"مالك":5,"مالك اساسي":6,"Dev":7}

async def rank(bot,chat_id,user_id,owner_id=0):
    if user_id == owner_id:
        return "Dev"
    try:
        m=await bot.get_chat_member(chat_id,user_id)
        if m.status=="creator": return "مالك اساسي"
        if m.status=="administrator":
            return saved_rank(chat_id,user_id) or "ادمن"
    except Exception:
        pass
    return saved_rank(chat_id,user_id) or "عضو"

def level(x): return LEVELS.get(x,0)
