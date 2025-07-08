import asyncio, json, os, time
from telethon import events, Button
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..sql_helper.globals import addgvar, gvarstatus
from ..Config import Config

plugin_category = "البوت"
cmhd = Config.COMMAND_HAND_LER
MLIST_DATA_FILE = "mlist_data.json"
MLIST_DATA = {}  # (chat, msg_id) -> {uid: join_timestamp}
MLIST_MSGS = {}  # same key -> bot message ID
LOG_THREADS = {}  # (chat, thread_msg_id) set by /msetlog

def load():
    global MLIST_DATA, MLIST_MSGS, LOG_THREADS
    if os.path.exists(MLIST_DATA_FILE):
        raw = json.load(open(MLIST_DATA_FILE))
        MLIST_DATA = {eval(k): v for k, v in raw.get("d", {}).items()}
        MLIST_MSGS = {eval(k): v for k, v in raw.get("m", {}).items()}
        LOG_THREADS = {eval(k): v for k, v in raw.get("l", {}).items()}

def save():
    json.dump({"d": MLIST_DATA, "m": MLIST_MSGS, "l": LOG_THREADS}, open(MLIST_DATA_FILE, "w"))

load()

async def refresh_all():
    while True:
        for key, msgid in list(MLIST_MSGS.items()):
            await update(key)
        await asyncio.sleep(300)

async def get_names(client, data):
    out = []
    for uid, ts in data.items():
        ent = await client.get_entity(uid)
        name = f"@{ent.username}" if ent.username else f"[{ent.first_name}](tg://user?id={ent.id})"
        delta = int((time.time()-ts)//60)
        out.append(f"- {name} [`{uid}`] – {delta} دقيقة")
    return "\n".join(out) or "👀 لا يوجد مشرف حاضر"

async def update(key):
    chat, mid = key
    data = MLIST_DATA.get(key, {})
    text = "**قائمة حضور المشرفين:**\n\n" + (await get_names(zedub, data))
    btns = [[
        Button.inline("🟢 in", data=f"in|{chat}|{mid}"),
        Button.inline("🔴 out", data=f"out|{chat}|{mid}")
    ], [Button.inline("🔄 تحديث", data=f"up|{chat}|{mid}")]]
    await zedub.edit_message(chat, MLIST_MSGS[key], text, buttons=btns)
    save()

@zedub.bot_cmd(pattern=fr"^{cmhd}mlist$")
async def cmd_mlist(e):
    key = (e.chat_id, e.reply_to_msg_id or e.id)
    MLIST_DATA.setdefault(key, {})
    msg = await e.reply("... جارٍ إنشاء القائمة", buttons=[])
    text = "**قائمة حضور المشرفين:**\n\n" + await get_names(zedub, {})
    msg2 = await e.reply(text, buttons=[[
        Button.inline("🟢 in", data=f"in|{key[0]}|{key[1]}"),
        Button.inline("🔴 out", data=f"out|{key[0]}|{key[1]}")
    ], [Button.inline("🔄 تحديث", data=f"up|{key[0]}|{key[1]}")]])
    MLIST_MSGS[key] = msg2.id
    save()
    await msg.edit("✅ تم إنشاء القائمة")

@zedub.bot_cmd(pattern=fr"^{cmhd}msetlog$")
async def cmd_msetlog(e):
    thread = e.chat_id, e.reply_to_msg_id or e.id
    LOG_THREADS[thread] = True
    save()
    await e.reply("✅ تم تحديد هذا الموضوع كـ سجل")

@zedub.tgbot.on(events.CallbackQuery(pattern=r"(in|out|up)\|(-?\d+)\|(\d+)"))
async def cb(e):
    cmd, chat, mid = e.pattern_match.groups()
    key = (int(chat), int(mid))
    uid = e.sender_id

    if cmd == "in":
        MLIST_DATA.setdefault(key, {})[uid] = time.time()
        msgtxt = "✅ تم تسجيل دخولك"
    elif cmd == "out":
        if uid in MLIST_DATA.get(key, {}):
            join = MLIST_DATA[key].pop(uid)
            delta = int((time.time()-join)//60)
            msgtxt = f"❌ تم تسجيل خروجك بعد {delta} دقيقة"
        else:
            msgtxt = "⚠️ لم تكن ضمن القائمة"
    else:
        await update(key)
        await e.answer("🔄 تم التحديث", alert=True)
        return

    await update(key)
    await e.answer(msgtxt, alert=False)

    thread = (key[0], key[1])
    ent = await zedub.get_entity(uid)
    name = ent.username and f"@{ent.username}" or f"[{ent.first_name}](tg://user?id={uid})"
    for thr in LOG_THREADS:
        if thr[0] == key[0]:
            await zedub.send_message(key[0], f"{name} قام { 'بالدخول' if cmd=='in' else 'بالخروج'} (بعد {delta if cmd=='out' else 0} دقيقة)", reply_to=thr[1])