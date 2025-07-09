# © This program was written by Mik
# @ASX16 , @SLOPK , AHMD
# I authorize everyone to use it.
import asyncio
import sqlite3
import time
from telethon import events, Button
from . import zedub
from ..Config import Config

cmhd = Config.COMMAND_HAND_LER
plugin_category = "البوت"
DB_PATH = "mlist_data.sqlite"

# ==== قاعدة البيانات ====
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS mlist_entries (
            chat_id INTEGER, msg_id INTEGER, user_id INTEGER, join_time INTEGER,
            PRIMARY KEY (chat_id, msg_id, user_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS mlist_messages (
            chat_id INTEGER, msg_id INTEGER, message_id INTEGER,
            PRIMARY KEY (chat_id, msg_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS mlist_logs (
            chat_id INTEGER PRIMARY KEY, log_msg_id INTEGER
        )""")
        conn.commit()

init_db()

# ==== أدوات ====
def get_key(event):
    reply_to = event.reply_to_msg_id or event.id
    return (event.chat_id, reply_to)

async def get_names(client, chat_id, msg_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, join_time FROM mlist_entries WHERE chat_id=? AND msg_id=?", (chat_id, msg_id))
        entries = c.fetchall()

    out = []
    for user_id, join_time in entries:
        try:
            ent = await client.get_entity(user_id)
            delta = int((time.time() - join_time) // 60)
            name = f"@{ent.username} [`{user_id}`]" if ent.username else f"[{ent.first_name}](tg://user?id={user_id}) [`{user_id}`]"
            out.append(f"- {name} – {delta} دقيقة")
        except Exception:
            continue
    return "\n".join(out) or "👀 لا يوجد مشرف حاضر"

async def update_mlist_message(client, chat_id, msg_id):
    text = "**قائمة حضور المشرفين:**\n\n" + await get_names(client, chat_id, msg_id)
    btns = [
        [Button.inline("🟢 دخول", data=f"in|{chat_id}|{msg_id}"), Button.inline("🔴 خروج", data=f"out|{chat_id}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"up|{chat_id}|{msg_id}")]
    ]
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT message_id FROM mlist_messages WHERE chat_id=? AND msg_id=?", (chat_id, msg_id))
        row = c.fetchone()
        if row:
            try:
                await client.edit_message(chat_id, row[0], text, buttons=btns)
            except Exception:
                pass

# ==== الأوامر ====
@zedub.bot_cmd(pattern=fr"^{cmhd}mlist$")
async def mlist_cmd(e):
    key = get_key(e)
    chat_id, msg_id = key

    text = "**قائمة حضور المشرفين:**\n\n👀 لا يوجد مشرف حاضر"
    btns = [
        [Button.inline("🟢 دخول", data=f"in|{chat_id}|{msg_id}"), Button.inline("🔴 خروج", data=f"out|{chat_id}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"up|{chat_id}|{msg_id}")]
    ]
    msg = await e.reply(text, buttons=btns)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO mlist_messages VALUES (?, ?, ?)", (chat_id, msg_id, msg.id))
        conn.commit()

@zedub.bot_cmd(pattern=fr"^{cmhd}msetlog$")
async def set_log(e):
    reply_id = e.reply_to_msg_id
    if not reply_id:
        return await e.reply("❗ يجب الرد على رسالة لتعيينها كسجل")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO mlist_logs VALUES (?, ?)", (e.chat_id, reply_id))
        conn.commit()
    await e.reply("✅ تم تعيين هذا الموضوع كروم للسجل")

# ==== ردود الأزرار ====
@zedub.tgbot.on(events.CallbackQuery(pattern=r"(in|out|up)\|(-?\d+)\|(\d+)"))
async def cb_handler(e):
    cmd, chat_id, msg_id = e.pattern_match.groups()
    chat_id, msg_id = int(chat_id), int(msg_id)
    uid = e.sender_id

    if cmd == "in":
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO mlist_entries VALUES (?, ?, ?, ?)", (chat_id, msg_id, uid, int(time.time())))
            conn.commit()
        await e.answer("✅ تم تسجيل دخولك")
        await log_action(e.client, chat_id, uid, "دخول")
    elif cmd == "out":
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT join_time FROM mlist_entries WHERE chat_id=? AND msg_id=? AND user_id=?", (chat_id, msg_id, uid))
            row = c.fetchone()
            if row:
                delta = int((time.time() - row[0]) // 60)
                conn.execute("DELETE FROM mlist_entries WHERE chat_id=? AND msg_id=? AND user_id=?", (chat_id, msg_id, uid))
                conn.commit()
                await e.answer(f"❌ تم تسجيل خروجك بعد {delta} دقيقة")
                await log_action(e.client, chat_id, uid, f"خروج بعد {delta} دقيقة")
            else:
                await e.answer("⚠️ لم تكن ضمن القائمة")
    elif cmd == "up":
        await update_mlist_message(e.client, chat_id, msg_id)
        await e.answer("🔄 تم التحديث", alert=True)

    if cmd in ["in", "out"]:
        await update_mlist_message(e.client, chat_id, msg_id)

# ==== التسجيل في السجل ====
async def log_action(client, chat_id, user_id, action_text):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT log_msg_id FROM mlist_logs WHERE chat_id=?", (chat_id,))
        row = c.fetchone()
        if row:
            ent = await client.get_entity(user_id)
            name = f"@{ent.username} [`{user_id}`]" if ent.username else f"[{ent.first_name}](tg://user?id={user_id}) [`{user_id}`]"
            log_text = f"{name} قام بـ {action_text}"
            try:
                await client.send_message(chat_id, log_text, reply_to=row[0])
            except Exception:
                pass