import asyncio
from datetime import datetime

from telethon.errors import BadRequestError, FloodWaitError, ForbiddenError

from . import zedub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers import reply_id, time_formatter
from ..helpers.utils import _format
from ..sql_helper.bot_blacklists import check_is_black_list, get_all_bl_users
from ..sql_helper.bot_starters import del_starter_from_db, get_all_starters
from ..sql_helper.globals import addgvar, delgvar, gvarstatus
from . import BOTLOG, BOTLOG_CHATID
from .botmanagers import (
    ban_user_from_bot,
    get_user_and_reason,
    progress_str,
    unban_user_from_bot,
)

LOGS = logging.getLogger(__name__)

plugin_category = "البوت"
botusername = Config.TG_BOT_USERNAME
cmhd = Config.COMMAND_HAND_LER


@zedub.bot_cmd(pattern="^/help$")
async def bot_help(event):
    await event.reply(
        """**✪ قائمة أوامر نظام النقاط (نظام الفرق واللاعبين)**

**أوامر خاصة بالمشرفين فقط:**

**1️⃣ تسجيل النقاط:**
• /p – إضافة نقطة لمستخدم
• /tp – إضافة نقطة لفريق المستخدم

**2️⃣ خصم النقاط:**
• /dp – خصم نقطة من مستخدم
• /tdp – خصم نقطة من فريق المستخدم

**3️⃣ استعراض النقاط:**
• /ps – عرض نقاط الأفراد
• /tps – عرض نقاط الفرق 

**4️⃣ تصفير النقاط:**
• /rstp – تصفير نقاط الافراد
• /trstp – تصفير نقاط الفرق 

**5️⃣ إدارة الفرق:**
• /showt – عرض معلومات الفرق (عدد النقاط – الأعضاء)
• /tmod on – تفعيل وضع الفرق
• /tmod off – تعطيل وضع الفرق

**مـلاحـظـات :**
– جميع الأوامر تبدأ بالرموز ( `/` , `.` , `!` , `#` , `$` )
– تنفيذ الأوامر يتطلب صلاحيات إدارية في المجموعة

"""
    )


@zedub.bot_cmd(pattern="^/broadcast$", from_users=Config.OWNER_ID)
async def bot_broadcast(event):
    replied = await event.get_reply_message()
    if not replied:
        return await event.reply("**- بالـرد ع رسـالة للإذاعة**")
    start_ = datetime.now()
    br_cast = await replied.reply("**جـاري الإذاعـة ...**")
    blocked_users = []
    count = 0
    bot_users_count = len(get_all_starters())
    if bot_users_count == 0:
        return await event.reply("**- لايـوجد مستخدمين بعـد بـ البـوت الخـاص بك**")
    users = get_all_starters()
    if users is None:
        return await event.reply("**- حدثت أخطـاء أثنـاء جلب قائمـة المستخـدمين.**")
    for user in users:
        try:
            await event.client.send_message(
                int(user.user_id), "**- تم الإذاعـة لجميـع مشتركيـن البـوت .. بنجـاح 🔊✓**"
            )
            await event.client.send_message(int(user.user_id), replied)
            await asyncio.sleep(0.8)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except (BadRequestError, ValueError, ForbiddenError):
            del_starter_from_db(int(user.user_id))
        except Exception as e:
            LOGS.error(str(e))
            if BOTLOG:
                await event.client.send_message(
                    BOTLOG_CHATID, f"**خطـأ بالإذاعـة**\n`{e}`"
                )

        else:
            count += 1
            if count % 5 == 0:
                try:
                    prog_ = (
                        "**🔊 جـاري الإذاعـة لمستخدمين البـوت ...**\n\n"
                        + progress_str(
                            total=bot_users_count,
                            current=count + len(blocked_users),
                        )
                        + f"\n\n• ✔️ **تم بنجـاح** :  `{count}`\n"
                        + f"• ✖️ **خطـأ بإذاعـة** :  `{len(blocked_users)}`"
                    )
                    await br_cast.edit(prog_)
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
    end_ = datetime.now()
    b_info = f"**🔊  تمت الإذاعـة بنجـاح لـ ➜**  <b>{count} شخـص.</b>"
    if blocked_users:
        b_info += f"\n <b>- المحظـوريـن 🚫 : {len(blocked_users)} مشتـرك </b> تم حظـرهم من البـوت المسـاعد مؤخـراً .. لذلك تم استبعـادهم 🚯"
    b_info += (
        f"\n⏳  <code>- جـارِ : {time_formatter((end_ - start_).seconds)}</code>."
    )
    await br_cast.edit(b_info, parse_mode="html")


@zedub.zed_cmd(
    pattern="المشتركين$",
    command=("المشتركين", plugin_category),
    info={
        "header": "لـ جلب قائمـة بالأعضـاء المشتـركيـن في البـوت المساعد الخـاص بك",
        "الاسـتخـدام": "{tr}المشتركين",
    },
)
async def ban_starters(event):
    "لـ جلب قائمـة بالأعضـاء المشتـركيـن في البـوت المساعد الخـاص بك"
    ulist = get_all_starters()
    if len(ulist) == 0:
        return await edit_delete(event, "**- لايــوجد مشتـركين بالبـوت بعـد**")
    msg = "**- قـائمـة مشتـركيـن البـوت المسـاعـد الخـاص بـك :\n\n**"
    for user in ulist:
        msg += f"**• المستخـدم :**  {_format.mentionuser(user.first_name , user.user_id)}\n**• الأيـدي :** `{user.user_id}`\n**• المعـرف :** @{user.username}\n**• تاريـخ الاشتراك : **__{user.date}__\n\n"
    await edit_or_reply(event, msg)


@zedub.bot_cmd(pattern="^/ban\\s+([\\s\\S]*)", from_users=Config.OWNER_ID)
async def ban_botpms(event):
    user_id, reason = await get_user_and_reason(event)
    reply_to = await reply_id(event)
    if not user_id:
        return await event.client.send_message(
            event.chat_id, "**- لـم أستطـع العثـور علـى الشخـص**", reply_to=reply_to
        )
    if not reason:
        return await event.client.send_message(
            event.chat_id, "**- لحظـر الشخـص أولًا عليـك بذكـر السبب مـع الأمـر**", reply_to=reply_to
        )
    try:
        user = await event.client.get_entity(user_id)
        user_id = user.id
    except Exception as e:
        return await event.reply(f"**- خطـأ :**\n`{e}`")
    if user_id == Config.OWNER_ID:
        return await event.reply("**- لايمكننـي حظـرك سيـدي ؟!**")
    if check := check_is_black_list(user.id):
        return await event.client.send_message(
            event.chat_id,
            f"#بالفعـل_محظـور\
            \nالشخـص بالفعـل موجود في قائمـة الحظـر.\
            \n**سبب الحظـر:** `{check.reason}`\
            \n**الوقت:** `{check.date}`.",
        )
    msg = await ban_user_from_bot(user, reason, reply_to)
    await event.reply(msg)


@zedub.bot_cmd(pattern="^/unban(?:\\s|$)([\\s\\S]*)", from_users=Config.OWNER_ID)
async def ban_botpms(event):
    user_id, reason = await get_user_and_reason(event)
    reply_to = await reply_id(event)
    if not user_id:
        return await event.client.send_message(
            event.chat_id, "**- لـم أستطـع العثـور علـى الشخـص**", reply_to=reply_to
        )
    try:
        user = await event.client.get_entity(user_id)
        user_id = user.id
    except Exception as e:
        return await event.reply(f"**- خطـأ :**\n`{e}`")
    check = check_is_black_list(user.id)
    if not check:
        return await event.client.send_message(
            event.chat_id,
            f"#ليـس_محظـور\
            \n👤 {_format.mentionuser(user.first_name , user.id)} doesn't exist in my Banned Users list.",
        )
    msg = await unban_user_from_bot(user, reason, reply_to)
    await event.reply(msg)


@zedub.zed_cmd(
    pattern="المحظورين$",
    command=("المحظورين", plugin_category),
    info={
        "header": "لـ جلب قائمـة بالمستخـدمين المحظـورين من بـوتك المسـاعـد",
        "الاسـتخـدام": "{tr}المحظورين",
    },
)
async def ban_starters(event):
    "لـ جلب قائمـة بالمستخـدمين المحظـورين من بـوتك المسـاعـد"
    ulist = get_all_bl_users()
    if len(ulist) == 0:
        return await edit_delete(event, "**- لـم تقـم بحظـر أحـد بعـد**")
    msg = "**- قـائمـة محظـورين البـوت المسـاعـد الخـاص بـك :\n\n**"
    for user in ulist:
        msg += f"**• المستخـدم :**  {_format.mentionuser(user.first_name , user.chat_id)}\n**• الأيـدي :** `{user.chat_id}`\n**• المعـرف :** @{user.username}\n**• تاريـخ الاشتراك : **__{user.date}__\n**• السبب :** __{user.reason}__\n\n"
    await edit_or_reply(event, msg)


@zedub.zed_cmd(
    pattern="مكافح التكرار (تفعيل|تعطيل)$",
    command=("bot_antif", plugin_category),
    info={
        "header": "لـ تفعيل / تعطيل مكافح التكرار لمستخدمين البوت الخاص بك",
        "الوصـف": "if it was turned on then after 10 messages or 10 edits of same messages in less time then your bot auto loacks them.",
        "الاسـتخـدام": [
            "{tr}مكافح التكرار تفعيل",
            "{tr}مكافح التكرار تعطيل",
        ],
    },
)
async def ban_antiflood(event):
    "لـ تفعيل / تعطيل مكافح التكرار لمستخدمين البوت الخاص بك"
    input_str = event.pattern_match.group(1)
    if input_str == "تفعيل":
        if gvarstatus("bot_antif") is not None:
            return await edit_delete(event, "**- وضـع مكافـح التكـرار مفعـل مسبقًـا**")
        addgvar("bot_antif", True)
        await edit_delete(event, "**- تـم تفعيـل وضـع مكافـح التكـرار . . بنجـاح ✓**")
    elif input_str == "تعطيل":
        if gvarstatus("bot_antif") is None:
            return await edit_delete(event, "**- وضـع مكافـح التكـرار معطـل مسبقًـا**")
        delgvar("bot_antif")
        await edit_delete(event, "**- تـم تعطيـل وضـع مكافـح التكـرار . . بنجـاح ✓**")
