# ✅ الإصدار المحسن لقائمة حضور المشرفين
# يشمل: تخزين دائم + زر تحديث + ربط المجموعات

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
MLIST_DATA = {}  # (chat_id, msg_id): [user_ids]
MLIST_MSGS = {}  # (chat_id, msg_id): message_id
LINKED_GROUPS = {}  # secondary_chat_id: (main_chat_id, msg_id)

# ----------------- Persistence -------------------
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

# ---------------- Utilities -------------------
async def get_names(client, user_ids):
    names = []
    for uid in user_ids:
        try:
            u = await client.get_entity(uid)
            if u.username:
                names.append(f"- @{u.username} [`{u.id}`]")
            else:
                names.append(f"- [{u.first_name}](tg://user?id={u.id}) [`{u.id}`]")
        except Exception:
            continue
    return names

def get_key(event):
    reply_to = event.reply_to_msg_id if getattr(event, "reply_to_msg_id", None) else event.id
    return (event.chat_id, reply_to)

async def update_mlist_message(client, chat_id, reply_to, key):
    user_ids = MLIST_DATA.get(key, set())
    names = await get_names(client, list(user_ids))
    text = "**قـائـمـة الـمـشـرفـيـن الـحـضـور:**\n\n" + ("\n".join(names) if names else "👀 ليس هناك مشرف موجود")
    btns = [
        [
            Button.inline("Log In 🟢", data=f"mlogin|{chat_id}|{reply_to}"),
            Button.inline("Log Out 🔴", data=f"mlogout|{chat_id}|{reply_to}")
        ],
        [Button.inline("🔄 تحديث", data=f"mrefresh|{chat_id}|{reply_to}")]
    ]
    try:
        msg_id = MLIST_MSGS.get(key)
        if msg_id:
            await client.edit_message(chat_id, msg_id, text, buttons=btns, link_preview=False)
    except Exception:
        pass

    save_data()

# ---------------- Commands -------------------

@zedub.bot_cmd(pattern="^/mlist$")
async def mlist_handler(event):
    key = get_key(event)
    MLIST_DATA.setdefault(key, set())
    chat_id, reply_to = key
    names = await get_names(event.client, list(MLIST_DATA[key]))
    text = "**قـائـمـة الـمـشـرفـيـن الـحـضـور:**\n\n" + ("\n".join(names) if names else "👀 ليس هناك مشرف موجود")
    btns = [
        [
            Button.inline("Log In 🟢", data=f"mlogin|{chat_id}|{reply_to}"),
            Button.inline("Log Out 🔴", data=f"mlogout|{chat_id}|{reply_to}")
        ],
        [Button.inline("🔄 تحديث", data=f"mrefresh|{chat_id}|{reply_to}")]
    ]
    msg = await event.reply(text, buttons=btns, link_preview=False)
    MLIST_MSGS[key] = msg.id
    save_data()

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogin\\|(-?\\d+)\\|(\\d+)"))
async def mlogin_handler(event):
    chat_id = int(event.pattern_match.group(1))
    reply_to = int(event.pattern_match.group(2))
    key = (chat_id, reply_to)
    user_id = event.sender_id
    MLIST_DATA.setdefault(key, set()).add(user_id)
    await update_mlist_message(event.client, chat_id, reply_to, key)
    await event.answer("✅ تم تسجيل حضورك", alert=False)

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogout\\|(-?\\d+)\\|(\\d+)"))
async def mlogout_handler(event):
    chat_id = int(event.pattern_match.group(1))
    reply_to = int(event.pattern_match.group(2))
    key = (chat_id, reply_to)
    user_id = event.sender_id
    MLIST_DATA.setdefault(key, set()).discard(user_id)
    await update_mlist_message(event.client, chat_id, reply_to, key)
    await event.answer("❌ تم تسجيل خروجك", alert=False)

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mrefresh\\|(-?\\d+)\\|(\\d+)"))
async def mrefresh_handler(event):
    chat_id = int(event.pattern_match.group(1))
    reply_to = int(event.pattern_match.group(2))
    key = (chat_id, reply_to)
    await update_mlist_message(event.client, chat_id, reply_to, key)
    await event.answer("🔄 تم تحديث القائمة", alert=False)

@zedub.bot_cmd(pattern=r"^/mlink (.+)\|(\d+)$")
async def link_secondary_group(event):
    args = event.pattern_match.group(1, 2)
    secondary = event.chat_id
    try:
        main_chat = int(args[0])
        msg_id = int(args[1])
        LINKED_GROUPS[secondary] = (main_chat, msg_id)
        save_data()
        return await event.reply("✅ تم ربط هذا القروب بالقائمة الرئيسية")
    except:
        return await event.reply("❗ استخدم التنسيق الصحيح: /mlink <معرف القروب>|<رسالة القائمة>")

@zedub.bot_cmd(pattern="^/(in|out)$")
async def alt_in_out(event):
    cmd = event.pattern_match.group(1)
    chat = event.chat_id
    user_id = event.sender_id
    if chat in LINKED_GROUPS:
        main_chat, msg_id = LINKED_GROUPS[chat]
        key = (main_chat, msg_id)
        if cmd == "in":
            MLIST_DATA.setdefault(key, set()).add(user_id)
        else:
            MLIST_DATA.setdefault(key, set()).discard(user_id)
        await update_mlist_message(event.client, main_chat, msg_id, key)
        return await event.reply("✅ تم تسجيل {}ك".format("دخول" if cmd == "in" else "خروج"))
