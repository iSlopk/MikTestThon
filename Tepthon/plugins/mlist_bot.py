import asyncio, json, os, time
from telethon import events, Button
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..sql_helper.globals import addgvar, gvarstatus
from ..Config import Config

plugin_category = "البوت"
cmhd = Config.COMMAND_HAND_LER
MLIST_DATA_FILE = "mlist_data.json"
MLIST_DATA = {}  # (chat_id, msg_id) -> {user_id: join_timestamp}
MLIST_MSGS = {}  # (chat_id, msg_id) -> message_id
LOG_THREADS = {}  # (chat_id, thread_msg_id)

def load():
    global MLIST_DATA, MLIST_MSGS, LOG_THREADS
    if os.path.exists(MLIST_DATA_FILE):
        raw = json.load(open(MLIST_DATA_FILE))
        MLIST_DATA = {eval(k): v for k, v in raw.get("d", {}).items()}
        MLIST_MSGS = {eval(k): v for k, v in raw.get("m", {}).items()}
        LOG_THREADS = {eval(k): v for k, v in raw.get("l", {}).items()}

def save():
    with open(MLIST_DATA_FILE, "w") as f:
        json.dump({
            "d": MLIST_DATA,
            "m": MLIST_MSGS,
            "l": LOG_THREADS
        }, f)

load()

async def refresh_all():
    while True:
        for key in MLIST_MSGS:
            await update(key)
        await asyncio.sleep(300)

async def get_names(client, data):
    out = []
    for uid, ts in data.items():
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

async def update(key):
    chat, msg_id = key
    data = MLIST_DATA.get(key, {})
    text = "**قائمة حضور المشرفين:**\n\n" + await get_names(zedub, data)
    btns = [
        [Button.inline("🟢 in", data=f"in|{chat}|{msg_id}"),
         Button.inline("🔴 out", data=f"out|{chat}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"up|{chat}|{msg_id}")]
    ]
    try:
        await zedub.edit_message(chat, MLIST_MSGS[key], text, buttons=btns)
    except Exception:
        pass
    save()

@zedub.bot_cmd(pattern=fr"^{cmhd}mlist$")
async def cmd_mlist(e):
    key = (e.chat_id, e.reply_to_msg_id or e.id)
    MLIST_DATA.setdefault(key, {})
    msg = await e.reply("... جارٍ إنشاء القائمة")
    text = "**قائمة حضور المشرفين:**\n\n" + await get_names(zedub, {})
    msg2 = await e.reply(text, buttons=[
        [Button.inline("🟢 in", data=f"in|{key[0]}|{key[1]}"),
         Button.inline("🔴 out", data=f"out|{key[0]}|{key[1]}")],
        [Button.inline("🔄 تحديث", data=f"up|{key[0]}|{key[1]}")]
    ])
    MLIST_MSGS[key] = msg2.id
    save()
    await msg.delete()

@zedub.bot_cmd(pattern=fr"^{cmhd}msetlog$")
async def cmd_msetlog(e):
    key = (e.chat_id, e.reply_to_msg_id or e.id)
    LOG_THREADS[key] = True
    save()
    await e.reply("✅ تم تعيين هذا الموضوع كروم للسجل")

@zedub.tgbot.on(events.CallbackQuery(pattern=r"(in|out|up)\|(-?\d+)\|(\d+)"))
async def cb_handler(e):
    cmd, chat, msg_id = e.pattern_match.groups()
    chat, msg_id = int(chat), int(msg_id)
    key = (chat, msg_id)
    uid = e.sender_id
    name = ""
    delta = 0

    if cmd == "in":
        MLIST_DATA.setdefault(key, {})[uid] = time.time()
        msgtxt = "✅ تم تسجيل دخولك"
    elif cmd == "out":
        if uid in MLIST_DATA.get(key, {}):
            join_time = MLIST_DATA[key].pop(uid)
            delta = int((time.time() - join_time) // 60)
            msgtxt = f"❌ تم تسجيل خروجك بعد {delta} دقيقة"
        else:
            msgtxt = "⚠️ لم تكن ضمن القائمة"
    else:
        await update(key)
        return await e.answer("🔄 تم التحديث", alert=True)

    await update(key)
    await e.answer(msgtxt, alert=False)

    # Logging
    ent = await zedub.get_entity(uid)
    if ent.username:
        name = f"@{ent.username} [`{uid}`]"
    else:
        name = f"[{ent.first_name}](tg://user?id={uid}) [`{uid}`]"

    for thread_key in LOG_THREADS:
        if thread_key[0] == chat:
            log_msg = f"{name} قام {'بالدخول' if cmd == 'in' else f'بالخروج بعد {delta} دقيقة'}"
            await zedub.send_message(chat, log_msg, reply_to=thread_key[1])