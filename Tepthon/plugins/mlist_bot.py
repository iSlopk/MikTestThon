# © This program was written by Mik
# @ASX16 , @SLOPK , AHMD
# I authorize everyone to use it.

import asyncio
from telethon import events, Button
from telethon.events import CallbackQuery
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..sql_helper.globals import addgvar, gvarstatus
from ..core.logger import logging

MLIST_DATA = {}
MLIST_MSGS = {}

plugin_category = "البوت"
cmhd = Config.COMMAND_HAND_LER

async def get_names(client, user_ids):
    names = []
    for uid in user_ids:
        try:
            e = await client.get_entity(uid)
            names.append(f"- [{e.first_name}](tg://user?id={uid})")
        except:
            continue
    return names

def get_key(event):
    reply_to = event.reply_to_msg_id or event.id
    return (event.chat_id, reply_to)

async def update_mlist_message(client, chat_id, reply_to, key):
    users = MLIST_DATA.get(key, set())
    names = await get_names(client, users)
    text = "**قائمة المشرفين الحاضرين:**\n\n" + ("\n".join(names) if names else "👀 لا يوجد مشرف حاضر")
    btns = [[
        Button.inline("Log In", f"mlogin|{chat_id}|{reply_to}"),
        Button.inline("Log Out", f"mlogout|{chat_id}|{reply_to}")
    ]]
    msg_id = MLIST_MSGS.get(key)
    if msg_id:
        try:
            await client.edit_message(chat_id, msg_id, text, buttons=btns)
        except:
            pass

@zedub.bot_cmd(pattern="^/msetlog$")
async def set_log_chat(event):
    chat_id = event.chat_id
    addgvar("MLIST_LOG_CHAT", str(chat_id))
    return await event.reply("✅ تم تعيين روم اللوغ لإشعارات دخول/خروج.")

@zedub.bot_cmd(pattern="^/mlist$")
async def mlist_handler(event):
    key = get_key(event)
    MLIST_DATA.setdefault(key, set())
    names = await get_names(event.client, MLIST_DATA[key])
    text = "**قائمة المشرفين الحاضرين:**\n" + ("\n".join(names) if names else "لا يوجد مشرف حاضر")
    btns = [[
        Button.inline("Log In", f"mlogin|{key[0]}|{key[1]}"),
        Button.inline("Log Out", f"mlogout|{key[0]}|{key[1]}")
    ]]
    msg = await event.reply(text, buttons=btns)
    MLIST_MSGS[key] = msg.id

@zedub.bot_cmd(pattern="^/in$")
async def mlist_in(event):
    key = get_key(event)
    uid = event.sender_id
    MLIST_DATA.setdefault(key, set()).add(uid)
    await update_mlist_message(event.client, key[0], key[1], key)
    await event.reply("✅ تم تسجيل حضورك")
    logid = gvarstatus("MLIST_LOG_CHAT")
    if logid:
        e = await event.client.get_entity(uid)
        await event.client.send_message(int(logid), f"📥 [{e.first_name}](tg://user?id={uid}) دخل `{key[0]}`")

@zedub.bot_cmd(pattern="^/out$")
async def mlist_out(event):
    key = get_key(event)
    uid = event.sender_id
    if uid in MLIST_DATA.setdefault(key, set()):
        MLIST_DATA[key].remove(uid)
        await update_mlist_message(event.client, key[0], key[1], key)
        await event.reply("❌ تم تسجيل خروجك")
        logid = gvarstatus("MLIST_LOG_CHAT")
        if logid:
            e = await event.client.get_entity(uid)
            await event.client.send_message(int(logid), f"📤 [{e.first_name}](tg://user?id={uid}) خرج `{key[0]}`")
    else:
        await event.reply("⚠️ لم تكن مسجّل دخول سابقاً")

@zedub.tgbot.on(CallbackQuery(pattern=r"mlogin\|(-?\d+)\|(\d+)"))
async def mlogin_handler(event):
    chat_id = int(event.pattern_match.group(1))
    reply_to = int(event.pattern_match.group(2))
    key = (chat_id, reply_to)
    uid = event.sender_id
    MLIST_DATA.setdefault(key, set()).add(uid)
    await update_mlist_message(event.client, chat_id, reply_to, key)
    await event.answer("✅ تم تسجيل حضورك")
    logid = gvarstatus("MLIST_LOG_CHAT")
    if logid:
        e = await event.client.get_entity(uid)
        await event.client.send_message(int(logid), f"📥 [{e.first_name}](tg://user?id={uid}) دخل `{chat_id}`")

@zedub.tgbot.on(CallbackQuery(pattern=r"mlogout\|(-?\d+)\|(\d+)"))
async def mlogout_handler(event):
    chat_id = int(event.pattern_match.group(1))
    reply_to = int(event.pattern_match.group(2))
    key = (chat_id, reply_to)
    uid = event.sender_id
    if uid in MLIST_DATA.setdefault(key, set()):
        MLIST_DATA[key].remove(uid)
        await update_mlist_message(event.client, chat_id, reply_to, key)
        await event.answer("❌ تم تسجيل خروجك")
        logid = gvarstatus("MLIST_LOG_CHAT")
        if logid:
            e = await event.client.get_entity(uid)
            await event.client.send_message(int(logid), f"📤 [{e.first_name}](tg://user?id={uid}) خرج `{chat_id}`")
    else:
        await event.answer("⚠️ لم تكن مسجّل دخول")