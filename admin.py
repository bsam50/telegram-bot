
from telegram import ChatPermissions

async def restrict_user(bot, chat_id, user_id, until_date=None):
    await bot.restrict_chat_member(
        chat_id,user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date
    )

async def unrestrict_user(bot, chat_id, user_id):
    await bot.restrict_chat_member(
        chat_id,user_id,
        permissions=ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
            can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )
