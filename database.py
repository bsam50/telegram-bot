import sqlite3

DB = "bot.db"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS ranks(chat_id INTEGER,user_id INTEGER,rank TEXT,
        PRIMARY KEY(chat_id,user_id));
    CREATE TABLE IF NOT EXISTS settings(chat_id INTEGER,name TEXT,value TEXT,
        PRIMARY KEY(chat_id,name));
    CREATE TABLE IF NOT EXISTS replies(chat_id INTEGER,trigger TEXT,answer TEXT,
        PRIMARY KEY(chat_id,trigger));
    CREATE TABLE IF NOT EXISTS multi_replies(chat_id INTEGER,trigger TEXT,answers TEXT,
        PRIMARY KEY(chat_id,trigger));
    CREATE TABLE IF NOT EXISTS warnings(chat_id INTEGER,user_id INTEGER,count INTEGER,
        PRIMARY KEY(chat_id,user_id));
    CREATE TABLE IF NOT EXISTS games(chat_id INTEGER,name TEXT,text TEXT,
        PRIMARY KEY(chat_id,name));
    CREATE TABLE IF NOT EXISTS global_ranks(user_id INTEGER,rank TEXT,
        PRIMARY KEY(user_id));
    CREATE TABLE IF NOT EXISTS global_bans(user_id INTEGER PRIMARY KEY);
    """)
    c.commit(); c.close()

def setting(chat_id, name, default="off"):
    c=db(); r=c.execute("SELECT value FROM settings WHERE chat_id=? AND name=?",(chat_id,name)).fetchone()
    c.close(); return r["value"] if r else default

def set_setting(chat_id,name,value):
    c=db(); c.execute("INSERT INTO settings VALUES(?,?,?) ON CONFLICT(chat_id,name) DO UPDATE SET value=excluded.value",(chat_id,name,value))
    c.commit(); c.close()

def save_rank(chat_id,user_id,rank):
    c=db(); c.execute("INSERT INTO ranks VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET rank=excluded.rank",(chat_id,user_id,rank))
    c.commit(); c.close()

def delete_rank(chat_id,user_id):
    c=db(); c.execute("DELETE FROM ranks WHERE chat_id=? AND user_id=?",(chat_id,user_id)); c.commit(); c.close()

def saved_rank(chat_id,user_id):
    c=db(); r=c.execute("SELECT rank FROM ranks WHERE chat_id=? AND user_id=?",(chat_id,user_id)).fetchone()
    c.close(); return r["rank"] if r else None

def add_reply(chat_id,trigger,answer):
    c=db(); c.execute("INSERT INTO replies VALUES(?,?,?) ON CONFLICT(chat_id,trigger) DO UPDATE SET answer=excluded.answer",(chat_id,trigger,answer)); c.commit(); c.close()

def del_reply(chat_id,trigger):
    c=db(); c.execute("DELETE FROM replies WHERE chat_id=? AND trigger=?",(chat_id,trigger)); c.commit(); c.close()

def get_reply(chat_id,trigger):
    c=db(); r=c.execute("SELECT answer FROM replies WHERE chat_id=? AND trigger=?",(chat_id,trigger)).fetchone(); c.close()
    return r["answer"] if r else None

def add_multi(chat_id,trigger,answers):
    c=db(); c.execute("INSERT INTO multi_replies VALUES(?,?,?) ON CONFLICT(chat_id,trigger) DO UPDATE SET answers=excluded.answers",(chat_id,trigger,"|||".join(answers))); c.commit(); c.close()

def get_multi(chat_id,trigger):
    c=db(); r=c.execute("SELECT answers FROM multi_replies WHERE chat_id=? AND trigger=?",(chat_id,trigger)).fetchone(); c.close()
    return r["answers"].split("|||") if r else None

def del_multi(chat_id,trigger):
    c=db(); c.execute("DELETE FROM multi_replies WHERE chat_id=? AND trigger=?",(chat_id,trigger)); c.commit(); c.close()

def add_game(chat_id,name,text):
    c=db(); c.execute("INSERT INTO games VALUES(?,?,?) ON CONFLICT(chat_id,name) DO UPDATE SET text=excluded.text",(chat_id,name,text)); c.commit(); c.close()

def get_game(chat_id,name):
    c=db(); r=c.execute("SELECT text FROM games WHERE chat_id=? AND name=?",(chat_id,name)).fetchone(); c.close()
    return r["text"] if r else None
