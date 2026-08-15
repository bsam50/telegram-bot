import sqlite3

DB = "bot.db"

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = connect()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS ranks(
        chat_id INTEGER, user_id INTEGER, rank TEXT,
        PRIMARY KEY(chat_id,user_id)
    );
    CREATE TABLE IF NOT EXISTS settings(
        chat_id INTEGER, name TEXT, value TEXT,
        PRIMARY KEY(chat_id,name)
    );
    CREATE TABLE IF NOT EXISTS warnings(
        chat_id INTEGER, user_id INTEGER, count INTEGER,
        PRIMARY KEY(chat_id,user_id)
    );
    CREATE TABLE IF NOT EXISTS replies(
        chat_id INTEGER, trigger TEXT, answer TEXT,
        PRIMARY KEY(chat_id,trigger)
    );
    """)
    con.commit()
    con.close()

def get_setting(chat_id, name, default="off"):
    con = connect()
    row = con.execute(
        "SELECT value FROM settings WHERE chat_id=? AND name=?",
        (chat_id, name)
    ).fetchone()
    con.close()
    return row["value"] if row else default

def set_setting(chat_id, name, value):
    con = connect()
    con.execute(
        "INSERT INTO settings(chat_id,name,value) VALUES(?,?,?) "
        "ON CONFLICT(chat_id,name) DO UPDATE SET value=excluded.value",
        (chat_id, name, value)
    )
    con.commit()
    con.close()

def set_rank(chat_id, user_id, rank):
    con = connect()
    con.execute(
        "INSERT INTO ranks(chat_id,user_id,rank) VALUES(?,?,?) "
        "ON CONFLICT(chat_id,user_id) DO UPDATE SET rank=excluded.rank",
        (chat_id, user_id, rank)
    )
    con.commit()
    con.close()

def remove_rank(chat_id, user_id):
    con = connect()
    con.execute(
        "DELETE FROM ranks WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )
    con.commit()
    con.close()

def get_saved_rank(chat_id, user_id):
    con = connect()
    row = con.execute(
        "SELECT rank FROM ranks WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    ).fetchone()
    con.close()
    return row["rank"] if row else None
