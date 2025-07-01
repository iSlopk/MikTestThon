import sqlite3
from telethon.errors.rpcerrorlist import MessageAuthorRequiredError
from ..core.managers import edit_or_reply

DB_PATH = "points_db.sqlite"

def get_db():
    return sqlite3.connect(DB_PATH)

def get_points(chat_id, user_id):
    with get_db() as db:
        cur = db.execute(
            "SELECT points FROM points WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        return row[0] if row else 0

def set_points(chat_id, user_id, points):
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO points (chat_id, user_id, points) VALUES (?, ?, ?)",
            (chat_id, user_id, points)
        )

def get_all_points(chat_id):
    with get_db() as db:
        cur = db.execute(
            "SELECT user_id, points FROM points WHERE chat_id=? AND points > 0 ORDER BY points DESC",
            (chat_id,)
        )
        return cur.fetchall()

def reset_all_points(chat_id):
    with get_db() as db:
        db.execute(
            "UPDATE points SET points=0 WHERE chat_id=?",
            (chat_id,)
        )

async def safe_edit_or_reply(event, text, **kwargs):
    try:
        await edit_or_reply(event, text, **kwargs)
    except MessageAuthorRequiredError:
        await event.reply(text, **kwargs)

async def get_user_id(event, args):
    if event.is_reply:
        reply = await event.get_reply_message()
        return reply.sender_id
    if args:
        if args[0].startswith("@"):
            try:
                entity = await event.client.get_entity(args[0])
                return entity.id
            except Exception:
                pass
        try:
            return int(args[0])
        except Exception:
            pass
    return None