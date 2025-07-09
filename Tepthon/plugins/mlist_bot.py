# © This program was written by Mik
# @ASX16 , @SLOPK , AHMD
# I authorize everyone to use it.

import asyncio
import re
from datetime import datetime
from telethon import events, Button, functions, types
from telethon.events import CallbackQuery, InlineQuery
from . import zedub
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..sql_helper.globals import addgvar, delgvar, gvarstatus
from pySmartDL import SmartDL

MLIST_DATA = {}
MLIST_MSGS = {}
LOG_CHANNELS = {}

plugin_category = "البوت"
botusername = Config.TG_BOT_USERNAME
cmhd = Config.COMMAND_HAND_LER

def get_key(event):
    reply_to = event.reply_to_msg_id if getattr(event, "reply_to_msg_id", None) else event.id
    return (event.chat_id, reply_to)

async def get_names(client, user_ids):
    names = []
    for uid in user_ids:
        try:
            entity = await client.get_entity(uid)
            name = f"[@{entity.username}](tg://user?id={uid})" if getattr(entity, "username", None) else f"[{entity.first_name}](tg://user?id={uid})"
            names.append(f"- {name}")
        except Exception:
            continue
    return names

async def update_mlist_message(client, chat_id, reply_to, key):
    user_ids = MLIST_DATA.get(key, set())
    names = await get_names(client, list(user_ids))
    text = "**قـائـمـة الـمـشـرفـيـن الـحـضـور:**\n\n" + ("\n".join(names) if names else "👀 ليس هناك مشرف موجود")
    btns = [
        [
            Button.inline("تسجيل دخول 🟢", data=f"mlogin|{chat_id}|{reply_to}"),
            Button.inline("تسجيل خروج 🔴", data=f"mlogout|{chat_id}|{reply_to}")
        ]
    ]
    try:
        msg_id = MLIST_MSGS.get(key)
        if msg_id:
            await client.edit_message(chat_id, msg_id, text, buttons=btns, link_preview=False)
    except Exception:
        pass

@zedub.bot_cmd(pattern=fr"^{cmhd}الحضور$")
async def mlist_handler(event):
    key = get_key(event)
    if key not in MLIST_DATA:
        MLIST_DATA[key] = set()
    chat_id, reply_to = key
    names = await get_names(event.client, list(MLIST_DATA[key]))
    text = "**قـائـمـة الـمـشـرفـيـن الـحـضـور:**\n\n" + ("\n".join(names) if names else "ليس هناك مشرف موجود 👀")
    btns = [
        [
            Button.inline("تسجيل دخول 🟢", data=f"mlogin|{chat_id}|{reply_to}"),
            Button.inline("تسجيل خروج 🔴", data=f"mlogout|{chat_id}|{reply_to}")
        ]
    ]
    msg = await event.reply(text, buttons=btns, link_preview=False)
    MLIST_MSGS[key] = msg.id

@zedub.bot_cmd(pattern=fr"^{cmhd}دخول$")
async def mlist_in(event):
    key = get_key(event)
    user_id = event.sender_id
    if key not in MLIST_DATA:
        MLIST_DATA[key] = set()
    MLIST_DATA[key].add(user_id)
    await update_mlist_message(event.client, key[0], key[1], key)
    msg = await event.reply("تم تسجيل حضورك ✅")
    asyncio.create_task(delete_later(msg))

@zedub.bot_cmd(pattern=fr"^{cmhd}خروج$")
async def mlist_out(event):
    key = get_key(event)
    user_id = event.sender_id
    if key not in MLIST_DATA:
        MLIST_DATA[key] = set()
    if user_id in MLIST_DATA[key]:
        MLIST_DATA[key].remove(user_id)
        await update_mlist_message(event.client, key[0], key[1], key)
        msg = await event.reply("تم تسجيل خروجك ❌")
        asyncio.create_task(delete_later(msg))
    else:
        msg = await event.reply("أنت لست ضمن القائمة!")
        asyncio.create_task(delete_later(msg))

async def delete_later(msg):
    await asyncio.sleep(4)
    try:
        await msg.delete()
    except Exception:
        pass

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogin\|(-?\d+)\|(\d+)"))
async def mlogin_handler(event):
    chat_id = int(event.pattern_match.group(1))
    reply_to = int(event.pattern_match.group(2))
    key = (chat_id, reply_to)
    user_id = event.sender_id

    if key not in MLIST_DATA:
        MLIST_DATA[key] = set()
    MLIST_DATA[key].add(user_id)
    await update_mlist_message(event.client, chat_id, reply_to, key)
    await event.answer("تم تسجيل حضورك ✅", alert=True)

    if chat_id in LOG_CHANNELS:
        log_chat_id, topic_id = LOG_CHANNELS[chat_id]
        try:
            user = await event.client.get_entity(user_id)
            now = datetime.now().strftime("%H:%M:%S")
            name_display = f"[@{user.username}](tg://user?id={user.id})" if getattr(user, "username", None) else f"[{user.first_name}](tg://user?id={user.id})"
            msg = (
                f"👤 **المستخدم** : {name_display}\n"
                f"📣 **الــحــالــة** : [ `🟢 تسجيل دخول` ]\n"
            )
            await event.client.send_message(
                entity=log_chat_id,
                message=msg,
                reply_to=topic_id,
                parse_mode="md"
            )
        except Exception:
            pass

@zedub.tgbot.on(events.CallbackQuery(pattern=r"mlogout\|(-?\d+)\|(\d+)"))
async def mlogout_handler(event):
    chat_id = int(event.pattern_match.group(1))
    reply_to = int(event.pattern_match.group(2))
    key = (chat_id, reply_to)
    user_id = event.sender_id

    if key not in MLIST_DATA:
        MLIST_DATA[key] = set()

    if user_id in MLIST_DATA[key]:
        MLIST_DATA[key].remove(user_id)
        await update_mlist_message(event.client, chat_id, reply_to, key)
        await event.answer("تم تسجيل خروجك ❌", alert=True)

        if chat_id in LOG_CHANNELS:
            log_chat_id, topic_id = LOG_CHANNELS[chat_id]
            try:
                user = await event.client.get_entity(user_id)
                now = datetime.now().strftime("%H:%M:%S")
                name_display = f"[@{user.username}](tg://user?id={user.id})" if getattr(user, "username", None) else f"[{user.first_name}](tg://user?id={user.id})"
                msg = (
                    f"👤 **المستخدم** : {name_display}\n"
                    f"📣 **الــحــالــة** : [ `🔴 تسجيل خروج` ]\n"
                )
                await event.client.send_message(
                    entity=log_chat_id,
                    message=msg,
                    reply_to=topic_id,
                    parse_mode="md"
                )
            except Exception:
                pass
    else:
        await event.answer("أنت لست ضمن القائمة!", alert=True)

@zedub.bot_cmd(pattern="^/msetlog(?: (.+))?")
async def set_log_topic(event):
    arg = event.pattern_match.group(1)
    chat_id = event.chat_id

    if arg and "t.me" in arg:
        match = re.search(r"t\.me/c/(-?\d+)/(\d+)", arg)
        if not match:
            await event.reply("❌ الرابط غير صالح.")
            return
        log_chat_id = int("-100" + match.group(1))
        topic_id = int(match.group(2))
        LOG_CHANNELS[chat_id] = (log_chat_id, topic_id)
        await event.reply("✅ تم تعيين سجل الحضور بنجاح.")
    else:
        await event.reply("❌ يرجى إرسال رابط الموضوع.\nمثال:\n/msetlog https://t.me/c/123456789/55")