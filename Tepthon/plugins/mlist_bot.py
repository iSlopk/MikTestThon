# © هذا البرنامج كتبه Mik
# @ASX16 , @SLOPK , AHMD
# مرخص للجميع بالاستخدام

import asyncio, sqlite3, time
from telethon import events, Button
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..Config import Config

DB_PATH = "mlist_data.sqlite"
plugin_category = "البوت"
cmhd = Config.COMMAND_HAND_LER

# إنشاء قاعدة البيانات إذا لم تكن موجودة
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS presence (
            chat_id INTEGER,
            msg_id INTEGER,
            user_id INTEGER,
            join_time INTEGER,
            PRIMARY KEY (chat_id, msg_id, user_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            chat_id INTEGER,
            thread_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

async def get_names(client, chat_id, msg_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, join_time FROM presence WHERE chat_id=? AND msg_id=?", (chat_id, msg_id))
    rows = c.fetchall()
    conn.close()

    names = []
    for uid, ts in rows:
        try:
            ent = await client.get_entity(uid)
            name = f"@{ent.username} [`{uid}`]" if ent.username else f"[{ent.first_name}](tg://user?id={uid}) [`{uid}`]"
            mins = int((time.time() - ts) // 60)
            names.append(f"- {name} – {mins} دقيقة")
        except Exception:
            continue
    return "\n".join(names) if names else "👀 لا يوجد مشرف حاضر"

async def update_message(chat_id, msg_id):
    text = "**قائمة حضور المشرفين:**\n\n" + await get_names(zedub, chat_id, msg_id)
    btns = [
        [Button.inline("🟢 in", data=f"in|{chat_id}|{msg_id}"),
         Button.inline("🔴 out", data=f"out|{chat_id}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"up|{chat_id}|{msg_id}")]
    ]
    try:
        await zedub.edit_message(chat_id, msg_id, text, buttons=btns)
    except Exception:
        pass

@zedub.bot_cmd(pattern=fr"^{cmhd}mlist$")
async def mlist_cmd(event):
    key = (event.chat_id, event.reply_to_msg_id or event.id)
    chat_id, msg_id = key
    text = "**قائمة حضور المشرفين:**\n\n" + await get_names(event.client, chat_id, msg_id)
    btns = [
        [Button.inline("🟢 in", data=f"in|{chat_id}|{msg_id}"),
         Button.inline("🔴 out", data=f"out|{chat_id}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"up|{chat_id}|{msg_id}")]
    ]
    sent = await event.reply(text, buttons=btns)
    # لا حاجة لحفظ ID لأنه محفوظ في الرسالة نفسها

@zedub.bot_cmd(pattern=fr"^{cmhd}msetlog$")
async def setlog_cmd(event):
    chat_id = event.chat_id
    thread_id = event.reply_to_msg_id or event.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM logs WHERE chat_id=?", (chat_id,))
    c.execute("INSERT INTO logs (chat_id, thread_id) VALUES (?, ?)", (chat_id, thread_id))
    conn.commit()
    conn.close()
    await event.reply("✅ تم تعيين هذا الموضوع كروم للسجل")

@zedub.tgbot.on(events.CallbackQuery(pattern=r"(in|out|up)\|(-?\d+)\|(\d+)"))
async def cb_handler(event):
    action, chat_id, msg_id = event.pattern_match.groups()
    chat_id = int(chat_id)
    msg_id = int(msg_id)
    uid = event.sender_id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    delta = 0

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

    # تسجيل الحدث
    try:
        ent = await event.client.get_entity(uid)
        name = f"@{ent.username}" if ent.username else f"[{ent.first_name}](tg://user?id={uid})"
        log_msg = f"{name} قام {'بالدخول ✅' if action == 'in' else f'بالخروج ❌ بعد {delta} دقيقة'}"

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT thread_id FROM logs WHERE chat_id=?", (chat_id,))
        row = c.fetchone()
        if row:
            await zedub.send_message(chat_id, log_msg, reply_to=row[0])
        conn.close()
    except Exception:
        pass