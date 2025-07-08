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
MLIST_DATA = {}       # key = (chat_id, list_msg_id) -> set(user_ids)
MLIST_MSGS = {}       # same key -> message_id
LINKED_GROUPS = {}    # secondary_chat_id -> (main_chat_id, list_msg_id)

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
    msg_to_edit = MLIST_MSGS.get((chat_id, msg_id))
    if msg_to_edit:
        try:
            await client.edit_message(chat_id, msg_to_edit, text, buttons=buttons, link_preview=False)
        except:
            pass
    save_data()

async def delete_after(msg, delay=5):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

def parse_message_link(link: str):
    # رابط مثل https://t.me/c/ID/MSGID أو /mlist ID|MSGID
    parts = link.replace("https://t.me/", "").split("/")
    if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
        return int(parts[-2]), int(parts[-1])
    if "|" in link:
        main, msg = link.split("|", 1)
        if main.isdigit() and msg.isdigit():
            return int(main), int(msg)
    return None, None

@zedub.bot_cmd(pattern=r"^/mlist(?:\s+(.+))?$")
async def mlist_handler(event):
    arg = event.pattern_match.group(1)
    if arg:
        main_chat, list_msg_id = parse_message_link(arg.strip())
        if not main_chat or not list_msg_id:
            return await edit_or_reply(event, "❗ صيغة الرابط غير صحيحة، استخدم /mlist <رابط>")
        key = (main_chat, list_msg_id)
    else:
        # بدون رابط → ضمن نفس الموضوع
        key = (event.chat_id, event.reply_to_msg_id or event.id)

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

@zedub.bot_cmd(pattern=r"^/msetlog(?:\s+(-?\d+))?$")
async def msetlog(event):
    chat = event.chat_id
    topic = event.reply_to_msg_id or event.id
    log_chat = event.pattern_match.group(1)
    if not log_chat:
        key = (chat, topic)
        addgvar("MLIST_LOG_CHAT", json.dumps(key))
        return await edit_or_reply(event, f"✅ تم تحديد موضوع السجل هنا (chat,msg): `{key}`")
    addgvar("MLIST_LOG_CHAT", log_chat)
    return await edit_or_reply(event, f"✅ تم تحديد روم اللوق: `{log_chat}`")

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
        MLIST_DATA.setdefault(key, set()).add(user); action = "الدخول"
    else:
        MLIST_DATA.setdefault(key, set()).discard(user); action = "الخروج"

    await update_mlist_message(event.client, main_chat, list_msg_id, key)

    # إشعار سجل
    gv = gvarstatus("MLIST_LOG_CHAT")
    if gv:
        try:
            log = json.loads(gv)
            dest = log if isinstance(log, list) else (int(gv), None)
        except:
            dest = (int(gv), None)
        ent = await event.client.get_entity(user)
        name = f"@{ent.username}" if ent.username else f"[{ent.first_name}](tg://user?id={ent.id})"
        if dest[1]:
            await event.client.send_message(dest[0], f"✅ {name} قام بـ{action}", reply_to=dest[1])
        else:
            await event.client.send_message(dest[0], f"✅ {name} قام بـ{action}")

    msg = await event.reply(f"✅ تم تسجيل {action}")
    asyncio.create_task(delete_after(msg, 5))