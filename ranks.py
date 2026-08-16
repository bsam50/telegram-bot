
from database import get_rank, set_rank, list_rank, clear_rank

RANKS = {
    "مالك اساسي":"مالك أساسي","مالك":"مالك","منشئ":"منشئ",
    "مدير":"مدير","ادمن":"أدمن","مميز":"مميز"
}
LEVEL = {"مميز":1,"أدمن":2,"مدير":3,"منشئ":4,"مالك":5,"مالك أساسي":6}

def normalize_rank(s):
    s=s.strip().lower().replace("أ","ا").replace("إ","ا").replace("آ","ا")
    for k,v in RANKS.items():
        if s == k.replace("أ","ا"): return v
    return None

def rank_level(r): return LEVEL.get(r,0)

def has_level(r, minimum):
    return rank_level(r) >= rank_level(minimum)

def rank_text(chat_id):
    rows=list_rank(chat_id)
    names={"مالك أساسي":"المالكين الأساسيين","مالك":"المالكين","منشئ":"المنشئين","مدير":"المدراء","أدمن":"الأدمنية","مميز":"المميزين"}
    out=[]
    for rr in ["مالك أساسي","مالك","منشئ","مدير","أدمن","مميز"]:
        ids=[str(x["user_id"]) for x in rows if x["rank"]==rr]
        out.append(f"• {names[rr]}: "+(", ".join(ids) if ids else "لا يوجد"))
    return "\n".join(out)
