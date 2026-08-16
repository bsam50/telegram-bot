
import sqlite3, json, os
from contextlib import closing

DB = os.getenv("DB_PATH", "bot.sqlite3")

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with closing(conn()) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS ranks(
            chat_id INTEGER, user_id INTEGER, rank TEXT, PRIMARY KEY(chat_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS settings(
            chat_id INTEGER, key TEXT, value TEXT, PRIMARY KEY(chat_id,key)
        );
        CREATE TABLE IF NOT EXISTS locks(
            chat_id INTEGER, key TEXT, mode TEXT, PRIMARY KEY(chat_id,key)
        );
        CREATE TABLE IF NOT EXISTS replies(
            chat_id INTEGER, trigger TEXT, answer TEXT, multi INTEGER DEFAULT 0,
            PRIMARY KEY(chat_id,trigger,multi)
        );
        CREATE TABLE IF NOT EXISTS global_ranks(
            user_id INTEGER PRIMARY KEY, rank TEXT
        );
        CREATE TABLE IF NOT EXISTS global_blocks(
            user_id INTEGER PRIMARY KEY, kind TEXT
        );
        CREATE TABLE IF NOT EXISTS global_replies(
            trigger TEXT PRIMARY KEY, answer TEXT, multi INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS fun_ranks(
            chat_id INTEGER, user_id INTEGER, fun TEXT, label TEXT,
            PRIMARY KEY(chat_id,user_id,fun)
        );
        """)
        c.commit()

def set_rank(chat,user,rank):
    with closing(conn()) as c:
        if rank:
            c.execute("INSERT OR REPLACE INTO ranks VALUES(?,?,?)",(chat,user,rank))
        else:
            c.execute("DELETE FROM ranks WHERE chat_id=? AND user_id=?",(chat,user))
        c.commit()

def get_rank(chat,user):
    with closing(conn()) as c:
        r=c.execute("SELECT rank FROM ranks WHERE chat_id=? AND user_id=?",(chat,user)).fetchone()
        return r["rank"] if r else None

def list_rank(chat,rank=None):
    with closing(conn()) as c:
        if rank:
            return c.execute("SELECT user_id,rank FROM ranks WHERE chat_id=? AND rank=?",(chat,rank)).fetchall()
        return c.execute("SELECT user_id,rank FROM ranks WHERE chat_id=?",(chat,)).fetchall()

def clear_rank(chat,rank=None):
    with closing(conn()) as c:
        if rank:
            c.execute("DELETE FROM ranks WHERE chat_id=? AND rank=?",(chat,rank))
        else:
            c.execute("DELETE FROM ranks WHERE chat_id=?",(chat,))
        c.commit()

def set_setting(chat,key,value):
    with closing(conn()) as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES(?,?,?)",(chat,key,str(value)))
        c.commit()

def get_setting(chat,key,default=None):
    with closing(conn()) as c:
        r=c.execute("SELECT value FROM settings WHERE chat_id=? AND key=?",(chat,key)).fetchone()
        return r["value"] if r else default

def set_lock(chat,key,mode):
    with closing(conn()) as c:
        c.execute("INSERT OR REPLACE INTO locks VALUES(?,?,?)",(chat,key,mode))
        c.commit()

def get_lock(chat,key):
    with closing(conn()) as c:
        r=c.execute("SELECT mode FROM locks WHERE chat_id=? AND key=?",(chat,key)).fetchone()
        return r["mode"] if r else "open"

def all_locks(chat):
    with closing(conn()) as c:
        return c.execute("SELECT key,mode FROM locks WHERE chat_id=?",(chat,)).fetchall()

def add_reply(chat,trig,ans,multi=0):
    with closing(conn()) as c:
        c.execute("INSERT OR REPLACE INTO replies VALUES(?,?,?,?)",(chat,trig,ans,multi))
        c.commit()

def del_reply(chat,trig,multi=None):
    with closing(conn()) as c:
        if multi is None:
            c.execute("DELETE FROM replies WHERE chat_id=? AND trigger=?",(chat,trig))
        else:
            c.execute("DELETE FROM replies WHERE chat_id=? AND trigger=? AND multi=?",(chat,trig,multi))
        c.commit()

def get_reply(chat,trig):
    with closing(conn()) as c:
        return c.execute("SELECT answer,multi FROM replies WHERE chat_id=? AND trigger=? ORDER BY multi DESC",(chat,trig)).fetchone()

def list_replies(chat):
    with closing(conn()) as c:
        return c.execute("SELECT trigger,answer,multi FROM replies WHERE chat_id=? ORDER BY trigger",(chat,)).fetchall()

def clear_replies(chat):
    with closing(conn()) as c:
        c.execute("DELETE FROM replies WHERE chat_id=?",(chat,)); c.commit()

def set_global_rank(user,rank):
    with closing(conn()) as c:
        if rank: c.execute("INSERT OR REPLACE INTO global_ranks VALUES(?,?)",(user,rank))
        else: c.execute("DELETE FROM global_ranks WHERE user_id=?",(user,))
        c.commit()

def get_global_rank(user):
    with closing(conn()) as c:
        r=c.execute("SELECT rank FROM global_ranks WHERE user_id=?",(user,)).fetchone()
        return r["rank"] if r else None

def global_users(rank=None):
    with closing(conn()) as c:
        if rank: return c.execute("SELECT user_id,rank FROM global_ranks WHERE rank=?",(rank,)).fetchall()
        return c.execute("SELECT user_id,rank FROM global_ranks").fetchall()

def clear_global_ranks():
    with closing(conn()) as c:
        c.execute("DELETE FROM global_ranks"); c.commit()

def block_global(user,kind):
    with closing(conn()) as c:
        c.execute("INSERT OR REPLACE INTO global_blocks VALUES(?,?)",(user,kind)); c.commit()

def unblock_global(user):
    with closing(conn()) as c:
        c.execute("DELETE FROM global_blocks WHERE user_id=?",(user,)); c.commit()

def global_blocked(user):
    with closing(conn()) as c:
        return c.execute("SELECT kind FROM global_blocks WHERE user_id=?",(user,)).fetchone()

def add_global_reply(trig,ans,multi=0):
    with closing(conn()) as c:
        c.execute("INSERT OR REPLACE INTO global_replies VALUES(?,?,?)",(trig,ans,multi)); c.commit()

def del_global_reply(trig):
    with closing(conn()) as c:
        c.execute("DELETE FROM global_replies WHERE trigger=?",(trig,)); c.commit()

def get_global_reply(trig):
    with closing(conn()) as c:
        return c.execute("SELECT answer,multi FROM global_replies WHERE trigger=?",(trig,)).fetchone()

def list_global_replies():
    with closing(conn()) as c:
        return c.execute("SELECT trigger,answer,multi FROM global_replies ORDER BY trigger").fetchall()

def clear_global_replies():
    with closing(conn()) as c:
        c.execute("DELETE FROM global_replies"); c.commit()
