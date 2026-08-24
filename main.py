from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "arabic_protection_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins={"root": "plugins"},
)

if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("ضع BOT_TOKEN في .env")
    app.run()
