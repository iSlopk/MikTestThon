# © هذا السكربت كتبه Mik
# @ASX16 , @SLOPK , AHMD

import os
import sqlite3
import time
import asyncio
from telethon import events, Button
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..Config import Config

plugin_category = "البوت"
cmhd = Config.COMMAND_HAND_LER
DB_PATH = "mlist_data.sqlite"

# ✅ إنشاء قاعدة البيانات إذا لم تكن موجودة
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS presence (
                chat_id INTEGER,
                msg_id INTEGER,
                user_id INTEGER,
                join_time INTEGER,
                PRIMARY KEY (chat_id, msg_id, user_id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                chat_id INTEGER,
                msg_id INTEGER,
                message_id INTEGER,
                PRIMARY KEY (chat_id, msg_id)
            )
        ''')

init_db()


async def get_names(client, data):
    out = []
    for uid, ts in data:
        try:
            ent = await client.get_entity(uid)
            if ent.username:
                name = f"@{ent.username} [`{uid}`]"
            else:
                name = f"[{ent.first_name}](tg://user?id={uid}) [`{uid}`]"
            delta = int((time.time() - ts) // 60)
            out.append(f"- {name} – {delta} دقيقة")
        except Exception:
            continue
    return "\n".join(out) or "👀 لا يوجد مشرف حاضر"


async def update_message(chat_id, msg_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, join_time FROM presence WHERE chat_id=? AND msg_id=?", (chat_id, msg_id))
        rows = cur.fetchall()

        cur.execute("SELECT message_id FROM messages WHERE chat_id=? AND msg_id=?", (chat_id, msg_id))
        res = cur.fetchone()
        if not res:
            return
        message_id = res[0]

    text = "**قائمة حضور المشرفين:**\n\n" + await get_names(zedub, rows)
    btns = [
        [Button.inline("🟢 in", data=f"in|{chat_id}|{msg_id}"),
         Button.inline("🔴 out", data=f"out|{chat_id}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"up|{chat_id}|{msg_id}")]
    ]
    try:
        await zedub.edit_message(chat_id, message_id, text, buttons=btns)
    except Exception:
        pass


@zedub.bot_cmd(pattern=fr"^{cmhd}mlist$")
async def cmd_mlist(e):
    key = (e.chat_id, e.reply_to_msg_id or e.id)
    msg = await e.reply("... جارٍ إنشاء القائمة")
    text = "**قائمة حضور المشرفين:**\n\n👀 لا يوجد مشرف حاضر"
    btns = [
        [Button.inline("🟢 in", data=f"in|{key[0]}|{key[1]}"),
         Button.inline("🔴 out", data=f"out|{key[0]}|{key[1]}")],
        [Button.inline("🔄 تحديث", data=f"up|{key[0]}|{key[1]}")]
    ]
    msg2 = await e.reply(text, buttons=btns)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("REPLACE INTO messages (chat_id, msg_id, message_id) VALUES (?, ?, ?)",
                     (key[0], key[1], msg2.id))
    await msg.delete()


@zedub.tgbot.on(events.CallbackQuery(pattern=r"(in|out|up)\|(-?\d+)\|(\d+)"))
async def cb_handler(event):
    action, chat_id, msg_id = event.pattern_match.groups()
    chat_id = int(chat_id)
    msg_id = int(msg_id)
    uid = event.sender_id
    txt = "⚠️ حدث غير معروف"
    delta = 0

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if action == "in":
        now = int(time.time())
        c.execute("REPLACE INTO presence (chat_id, msg_id, user_id, join_time) VALUES (?, ?, ?, ?)",
                  (chat_id, msg_id, uid, now))
        conn.commit()
        txt = "✅ تم تسجيل دخولك"
    elif action == "out":
        c.execute("SELECT join_time FROM presence WHERE chat_id=? AND msg_id=? AND user_id=?",
                  (chat_id, msg_id, uid))
        row = c.fetchone()
        if row:
            delta = int((time.time() - row[0]) // 60)
            c.execute("DELETE FROM presence WHERE chat_id=? AND msg_id=? AND user_id=?",
                      (chat_id, msg_id, uid))
            conn.commit()
            txt = f"❌ تم تسجيل خروجك بعد {delta} دقيقة"
        else:
            txt = "⚠️ لم تكن ضمن القائمة"
    elif action == "up":
        await update_message(chat_id, msg_id)
        await event.answer("🔄 تم التحديث", alert=True)
        conn.close()
        return

    conn.close()
    await update_message(chat_id, msg_id)
    await event.answer(txt, alert=False)