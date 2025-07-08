import asyncio
import json
import os
import re
from telethon import events, Button
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..sql_helper.globals import addgvar, gvarstatus
from ..Config import Config

plugin_category = "البوت"

MLIST_DATA_FILE = "mlist_data.json"
MLIST_DATA = {}       # (chat_id, msg_id): set(user_ids)
MLIST_MSGS = {}       # (chat_id, msg_id): msg_id
LINKED_GROUPS = {}    # group_id: (chat_id, msg_id)

# ========== التخزين ==========
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

# ========== المساعدات ==========
async def get_names(client, user_ids):
    names = []
    for uid in user_ids:
        try:
            u = await client.get_entity(uid)
            name = f"@{u.username}" if u.username else f"[{u.first_name}](tg://user?id={u.id})"
            names.append(f"- {name} [`{u.id}`]")
        except:
            continue
    return names

async def delete_after(msg, delay=5):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

async def update_mlist_message(client, chat_id, msg_id, key):
    users = MLIST_DATA.get(key, set())
    text = "**قائمة حضور المشرفين:**\n\n"
    text += "\n".join(await get_names(client, users)) if users else "👀 لا يوجد مشرف حاضر"
    buttons = [
        [Button.inline("Log In 🟢", data=f"mlogin|{chat_id}|{msg_id}"),
         Button.inline("Log Out 🔴", data=f"mlogout|{chat_id}|{msg_id}")],
        [Button.inline("🔄 تحديث", data=f"mrefresh|{chat_id}|{msg_id}")]
    ]
    try:
        await client.edit_message(chat_id, msg_id, text, buttons=buttons)
    except:
        pass
    save_data()

def extract_link_ids(link):
    match = re.search(r"t\.me/c/(-?\d+)/(\d+)", link)
    if match:
        return int("-100" + match.group(1)), int(match.group(2))
    return None, None

# ========== الأوامر ==========
@zedub.bot_cmd(pattern=r"^/mlist(?:\s+(https?://t\.me/c/\d+/\d+))?$")
async def mlist_handler(event):
    if event.pattern_match.group(1):
        chat_id, msg_id = extract_link_ids(event.pattern_match.group(1))
        if not chat_id or not msg_id:
            return await edit_or_reply(event, "❗ تأكد من رابط الرسالة داخل موضوع")
        key = (chat_id, msg_id)
        MLIST_DATA.setdefault(key, set())
        MLIST_MSGS[key] = msg_id
        await update_mlist_message(event.client, chat_id, msg_id, key)
        return await edit_or_reply(event, "✅ تم تحديث القائمة في الموضوع المحدد")
    else:
        key = (event.chat_id, event.id)
        MLIST_DATA.setdefault(key, set())
        text = "**قائمة حضور المشرفين:**\n\n"
        text += "👀 لا يوجد مشرف حاضر"
        buttons = [
            [Button.inline("Log In 🟢", data=f"mlogin|{event.chat_id}|{event.id}"),
             Button.inline("Log Out 🔴", data=f"mlogout|{event.chat_id}|{event.id}")],
            [Button.inline("🔄 تحديث", data=f"mrefresh|{event.chat_id}|{event.id}")]
        ]
        msg = await event.reply(text, buttons=buttons)
        MLIST_MSGS[key] = msg.id
        save_data()

@zedub.bot_cmd(pattern=r"^/setlog(?:\s+(https?://t\.me/c/\d+/\d+))?$")
async def msetlog(event):
    if event.pattern_match.group(1):
        chat_id, msg_id = extract_link_ids(event.pattern_match.group(1))
    else:
        chat_id = event.chat_id
        msg_id = event.reply_to_msg_id or event.id
    addgvar("MLIST_LOG_CHAT", f"{chat_id}:{msg_id}")
    return await edit_or_reply(event, "✅ تم تعيين هذا الموضوع كروم اللوق")

@zedub.bot_cmd(pattern=r"^/mlink\s+(https?://t\.me/c/\d+/\d+)$")
async def mlink(event):
    link = event.pattern_match.group(1)
    chat_id, msg_id = extract_link_ids(link)
    if not chat_id or not msg_id:
        return await edit_or_reply(event, "❗ تأكد أن الرابط صالح")
    LINKED_GROUPS[event.chat_id] = (chat_id, msg_id)
    save_data()
    return await edit_or_reply(event, "✅ تم ربط هذا القروب بالقائمة في الموضوع المحدد")

@zedub.bot_cmd(pattern=r"^/(in|out)$")
async def alt_in_out(event):
    cmd = event.pattern_match.group(1)
    user = event.sender_id
    chat_id = event.chat_id

    if chat_id not in LINKED_GROUPS:
        return await event.reply("❗ هذا القروب غير مرتبط بقائمة رئيسية", link_preview=False)

    target_chat, msg_id = LINKED_GROUPS[chat_id]
    key = (target_chat, msg_id)
    MLIST_DATA.setdefault(key, set())

    if cmd == "in":
        MLIST_DATA[key].add(user)
        status = "الدخول"
    else:
        MLIST_DATA[key].discard(user)
        status = "الخروج"

    await update_mlist_message(event.client, target_chat, msg_id, key)

    # log
    raw_log = gvarstatus("MLIST_LOG_CHAT")
    if raw_log:
        log_chat, log_msg = map(int, raw_log.split(":"))
        u = await event.client.get_entity(user)
        name = f"@{u.username}" if u.username else f"[{u.first_name}](tg://user?id={u.id})"
        await event.client.send_message(log_chat, f"📢 {name} قام بـ{status}")

    done = await event.reply(f"✅ تم تسجيل {status}")
    asyncio.create_task(delete_after(done))

# ========== الأزرار ==========
@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogin\|(-?\d+)\|(\d+)"))
async def cb_login(event):
    chat_id, msg_id = map(int, event.pattern_match.groups())
    key = (chat_id, msg_id)
    MLIST_DATA.setdefault(key, set()).add(event.sender_id)
    await update_mlist_message(event.client, chat_id, msg_id, key)
    await event.answer("✅ تم تسجيل حضورك", alert=False)

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogout\|(-?\d+)\|(\d+)"))
async def cb_logout(event):
    chat_id, msg_id = map(int, event.pattern_match.groups())
    key = (chat_id, msg_id)
    MLIST_DATA.setdefault(key, set()).discard(event.sender_id)
    await update_mlist_message(event.client, chat_id, msg_id, key)
    await event.answer("✅ تم تسجيل خروجك", alert=False)

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mrefresh\|(-?\d+)\|(\d+)"))
async def cb_refresh(event):
    chat_id, msg_id = map(int, event.pattern_match.groups())
    key = (chat_id, msg_id)
    await update_mlist_message(event.client, chat_id, msg_id, key)
    await event.answer("✅ تم التحديث", alert=False)
