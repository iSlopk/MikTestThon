import asyncio
import json
import os
from telethon import events, Button
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..sql_helper.globals import addgvar, gvarstatus
from ..Config import Config

plugin_category = "البوت"

MLIST_DATA_FILE = "mlist_data.json"
MLIST_DATA = {}       # key = (main_chat_id, list_msg_id) -> set(user_ids)
MLIST_MSGS = {}       # same key -> message_id
LINKED_GROUPS = {}    # secondary_chat_id -> (main_chat_id, list_msg_id)

# -- Persistence --

def load_data():
    global MLIST_DATA, MLIST_MSGS, LINKED_GROUPS
    if os.path.exists(MLIST_DATA_FILE):
        with open(MLIST_DATA_FILE, 'r') as f:
            raw = json.load(f)
            MLIST_DATA = {eval(k): set(v) for k, v in raw.get('mlist_data', {}).items()}
            MLIST_MSGS = {eval(k): v for k, v in raw.get('mlist_msgs', {}).items()}
            LINKED_GROUPS = {int(k): tuple(v) for k, v in raw.get('linked_groups', {}).items()}

def save_data():
    with open(MLIST_DATA_FILE, 'w') as f:
        json.dump({
            'mlist_data': {str(k): list(v) for k, v in MLIST_DATA.items()},
            'mlist_msgs': {str(k): v for k, v in MLIST_MSGS.items()},
            'linked_groups': {str(k): list(v) for k, v in LINKED_GROUPS.items()}
        }, f)

load_data()

# -- Helpers --

async def get_names(client, user_ids):
    lst = []
    for uid in user_ids:
        try:
            u = await client.get_entity(uid)
            if u.username:
                lst.append(f"- @{u.username} [`{u.id}`]")
            else:
                lst.append(f"- [{u.first_name}](tg://user?id={u.id}) [`{u.id}`]")
        except:
            continue
    return lst

async def update_mlist_message(client, chat_id, msg_id, key):
    users = MLIST_DATA.get(key, set())
    names = await get_names(client, list(users))
    text = "**قائمة حضور المشرفين:**\n\n" + ("\n".join(names) if names else "👀 لا يوجد مشرف حاضر")
    buttons = [
        [Button.inline("Log In", data=f"mlogin|{chat_id}|{msg_id}"),
         Button.inline("Log Out", data=f"mlogout|{chat_id}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"mrefresh|{chat_id}|{msg_id}")]
    ]
    try:
        client_id = MLIST_MSGS.get(key)
        if client_id:
            await client.edit_message(chat_id, client_id, text, buttons=buttons, link_preview=False)
    except:
        pass
    save_data()

async def delete_after(msg, delay=5):
    await asyncio.sleep(delay)
    try: await msg.delete()
    except: pass

def get_key(event):
    reply = event.reply_to_msg_id or event.id
    return (event.chat_id, reply)

# -- Commands --

@zedub.bot_cmd(pattern="^/mlist$")
async def mlist_handler(event):
    key = get_key(event)
    MLIST_DATA.setdefault(key, set())
    chat, msg_id = key
    names = await get_names(event.client, list(MLIST_DATA[key]))
    text = "**قائمة حضور المشرفين:**\n\n" + ("\n".join(names) if names else "👀 لا يوجد مشرف حاضر")
    buttons = [
        [Button.inline("Log In", data=f"mlogin|{chat}|{msg_id}"),
         Button.inline("Log Out", data=f"mlogout|{chat}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"mrefresh|{chat}|{msg_id}")]
    ]
    message = await event.reply(text, buttons=buttons, link_preview=False)
    MLIST_MSGS[key] = message.id
    save_data()

@zedub.bot_cmd(pattern=r"^/msetlog\s+(-?\d+)$")
async def msetlog(event):
    log_chat = event.pattern_match.group(1)
    addgvar("MLIST_LOG_CHAT", str(log_chat))
    return await edit_or_reply(event, f"✅ تم تحديد روم اللوق: `{log_chat}`")

@zedub.bot_cmd(pattern=r"^/mlink\s+(-?\d+)\s*\|\s*(\d+)$")
async def link_secondary_group(event):
    sec = event.chat_id
    main_id, msg_id = map(int, event.pattern_match.group(1, 2))
    LINKED_GROUPS[sec] = (main_id, msg_id)
    save_data()
    return await event.reply("✅ تم ربط القروب الثانوي بالقائمة الرئيسية")

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogin\|(-?\d+)\|(\d+)"))
async def mlogin_cb(event):
    chat, msg_id = map(int, event.pattern_match.group(1,2))
    key = (chat, msg_id)
    MLIST_DATA.setdefault(key, set()).add(event.sender_id)
    await update_mlist_message(event.client, chat, msg_id, key)
    await event.answer("✅ تم تسجيل حضورك", alert=False)

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogout\|(-?\d+)\|(\d+)"))
async def mlogout_cb(event):
    chat, msg_id = map(int, event.pattern_match.group(1,2))
    key = (chat, msg_id)
    MLIST_DATA.setdefault(key, set()).discard(event.sender_id)
    await update_mlist_message(event.client, chat, msg_id, key)
    await event.answer("✅ تم تسجيل خروجك", alert=False)

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mrefresh\|(-?\d+)\|(\d+)"))
async def mrefresh_cb(event):
    chat, msg_id = map(int, event.pattern_match.group(1,2))
    key = (chat, msg_id)
    await update_mlist_message(event.client, chat, msg_id, key)
    await event.answer("🔄 القائمة تم تحديثها", alert=False)

@zedub.bot_cmd(pattern="^/(in|out)$")
async def alt_in_out(event):
    cmd = event.pattern_match.group(1)
    sec_chat = event.chat_id
    user = event.sender_id

    if sec_chat not in LINKED_GROUPS:
        return await edit_or_reply(event, "❗ هذا القروب غير مرتبط بقائمة رئيسية")

    main_chat, list_msg_id = LINKED_GROUPS[sec_chat]
    key = (main_chat, list_msg_id)

    if cmd == "in":
        MLIST_DATA.setdefault(key, set()).add(user)
        action = "الدخول"
    else:
        MLIST_DATA.setdefault(key, set()).discard(user)
        action = "الخروج"

    await update_mlist_message(event.client, main_chat, list_msg_id, key)

    # إرسال إشعار للوق
    log_chat = gvarstatus("MLIST_LOG_CHAT")
    if log_chat:
        ent = await event.client.get_entity(user)
        name = f"@{ent.username}" if ent.username else f"[{ent.first_name}](tg://user?id={ent.id})"
        await event.client.send_message(int(log_chat), f"✅ {name} قام بـ{action}")

    # تأكيد مؤقت
    msg = await event.reply(f"✅ تم تسجيل {action}")
    asyncio.create_task(delete_after(msg, 5))