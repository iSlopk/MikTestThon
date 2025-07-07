##############################
### Tele: @ASX16 Name: Mik ###
### حقوق ميكثون، كتابة ميكثون تيم  ###
###     Source: @SLOPK     ###
##############################
import asyncio
import sqlite3
import re
from telethon import Button, events
from telethon.errors.rpcerrorlist import MessageAuthorRequiredError
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.events import CallbackQuery, NewMessage
from ..core.session import zedub
from ..Config import Config
from ..core.managers import edit_or_reply
from ..utils.points_helpers import (
    get_points, set_points, get_all_points, reset_all_points,
    get_user_id, safe_edit_or_reply as safe_edit
)

plugin_category = "بوت النقاط"
cmhd = Config.COMMAND_HAND_LER
DB_PATH = "teampoints_db.sqlite"
#DB_PATH = "points_db.sqlite"

AWAITING_NAMES = set()
TEAM_MODE = {}
TEAMS = {}

MAX_POINTS = 99
MAX_TEAM_MEMBERS = 10

def get_db():
    return sqlite3.connect(DB_PATH)

def create_table():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS points (
                chat_id INTEGER,
                user_id INTEGER,
                points INTEGER,
                PRIMARY KEY(chat_id, user_id)
            )
        """)

create_table()

async def is_user_admin(event):
    admins = await event.client.get_participants(
        event.chat_id, filter=ChannelParticipantsAdmins
    )
    return any(a.id == event.sender_id for a in admins)

def get_team_top_members(chat, team_idx):
    members = TEAMS[chat]['members'].get(team_idx, [])
    if not members:
        return []
   
    return sorted(
        [(uid, get_points(chat, uid)) for uid in members],
        key=lambda x: x[1],
        reverse=True
    )

def build_team_display(chat, client):
    async def inner():
        lines = ["🧩 | **التسجيل مفتوح الآن**\n\n🎮 | **الأفــرقــة**:", ""]
        for idx, name in enumerate(TEAMS[chat]['names']):
            members = TEAMS[chat]['members'].get(idx, [])
            if members:
                entities = await asyncio.gather(*(client.get_entity(m) for m in members))
                mentions = "\n".join(
                    f"    - @{u.username}" if u.username else f"    - [{u.first_name}](tg://user?id={u.id})"
                    for u in entities
                )
            else:
                mentions = "    - مافيه ناس بالتيم :("
            member_count = len(members)
            lines.append(f"• اسـم الـفـريـق : `{name}`\n• الأعـضـاء : `({member_count} / {MAX_TEAM_MEMBERS})`\n• تـفـاصـيـل :\n{mentions}\n")
        return "\n".join(lines)
    return inner

def build_team_buttons(chat):
    team_buttons = []
    for i, name in enumerate(TEAMS[chat]['names']):
        team_buttons.append([Button.inline(f"{name}", b"noop")])
        team_buttons.append([
            Button.inline("🔋 انضمام", f"join_team_{i}"),
            Button.inline("🪫 مغادرة", f"leave_team_{i}")
        ])
    return team_buttons

@zedub.bot_cmd(pattern=fr"^{cmhd}tmod(?:\s+(on|off))?$")
async def cmd_tmod(event):
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ الأمر للمشرفين فقط")

    arg = event.pattern_match.group(1)
    if arg == "on":
        TEAM_MODE[event.chat_id] = True
        TEAMS[event.chat_id] = {
            'count': 2,
            'names': [],
            'members': {},
            'changed': set()
        }
        buttons = [
            [Button.inline("🔧 إنشاء الفرق", b"setup_teams")]
        ]
        await event.reply("✅ تم تفعيل وضع الفرق", buttons=buttons)
        try:
            await event.delete()
        except Exception:
            pass
        return

    if arg == "off":
        TEAM_MODE[event.chat_id] = False
        return await safe_edit(event, "✅ تم الرجوع لوضع الأفراد")

    return await safe_edit(
        event,
        "❗ استخدم:\n/tmod on ← تفعيل وضع الفرق\n/tmod off ← تعطيل وضع الفرق"
    )

@zedub.tgbot.on(events.CallbackQuery)
async def callback_handler(event):
    chat = event.chat_id
    data = event.data.decode()

    if not data.startswith("join_team_") and not data.startswith("leave_team_") and not await is_user_admin(event):
        return await event.answer("❗ للمشرفين فقط", alert=True)

    if data == "setup_teams":
        kb = [
            [Button.inline(str(i), f"team_count_{i}") for i in range(2, 6)],
            [Button.inline(str(i), f"team_count_{i}") for i in range(6, 11)],
            [Button.inline("✔️ تحديد بأسماء الفرق", b"team_names")]
        ]
        return await event.edit("اختر عدد الفرق :", buttons=kb)

    if data.startswith("team_count_"):
        try:
            n = int(data.split("_")[-1])
            TEAMS[chat]['count'] = n
            return await event.edit(
                f"✅ اخترت عدد الفرق : [{n}]\nاضغط لتعيين أسماء الفرق",
                buttons=[[Button.inline("📝 تسمية الفرق", b"team_names")]]
            )
        except ValueError:
            return await event.answer("⚠️ رقم غير صالح", alert=False)

    if data == "team_names":
        AWAITING_NAMES.add(chat)
        return await event.reply(
            "📩 أرسل أسماء الفرق مثل:\n`( 🟢 MikTeam | 🔴 SaTeam )`\n\nالفواصل المدعومة:\n( `،` `,` `*` `\` `-` `|` `/` )"
        )

    if data == "confirm_names":
        if chat in TEAMS and "_preview_names" in TEAMS[chat]:
            names = TEAMS[chat].pop("_preview_names")
            TEAMS[chat]['names'] = names
            TEAMS[chat]['members'] = {i: [] for i in range(len(names))}
            AWAITING_NAMES.discard(chat)
            return await event.edit(
                "✅ تم حفظ أسماء الفرق بنجاح",
                buttons=[[Button.inline("🚀 ابدأ التسجيل", b"start_signup")]]
            )
        else:
            return await event.answer("⚠️ لا يوجد أسماء لحفظها", alert=True)

    if data == "start_signup":
        text = await build_team_display(chat, event.client)()
        buttons = build_team_buttons(chat)
        return await event.edit(text, buttons=buttons, link_preview=False)

    if data.startswith("join_team_"):
        idx = int(data.split("_")[-1])
        uid = event.sender_id
        if chat not in TEAMS:
            return await event.answer("❗ لم يتم تفعيل وضع الفرق بعد", alert=True)

        for members in TEAMS[chat]['members'].values():
            if uid in members:
                return await event.answer("❗ انت بالفعل في فريق", alert=True)

        if len(TEAMS[chat]['members'].get(idx, [])) >= MAX_TEAM_MEMBERS:
            return await event.answer("⚠️ الفريق مكتمل", alert=True)

        TEAMS[chat]['members'].setdefault(idx, []).append(uid)
        await event.answer("✅ تم الانضمام", alert=False)

        text = await build_team_display(chat, event.client)()
        buttons = build_team_buttons(chat)
        return await event.edit(text, buttons=buttons, link_preview=False)

    if data.startswith("leave_team_"):
        idx = int(data.split("_")[-1])
        uid = event.sender_id

        if chat not in TEAMS or uid not in TEAMS[chat]['members'].get(idx, []):
            return await event.answer("❗ أنت لست في هذا الفريق", alert=True)

        TEAMS[chat]['members'][idx].remove(uid)
        await event.answer("✅ غادرت الفريق", alert=True)

        text = await build_team_display(chat, event.client)()
        buttons = build_team_buttons(chat)
        return await event.edit(text, buttons=buttons, link_preview=False)
        
@zedub.tgbot.on(events.NewMessage)
async def receive_names(ev):
    if not await is_user_admin(ev):
        return
    chat = ev.chat_id
    if not ev.is_group or chat not in AWAITING_NAMES:
        return

    if TEAMS.get(chat) and not TEAMS[chat]['names']:
        text = ev.text.strip()

       
    if not (text.startswith("(") and text.endswith(")")):
        return

       
    if not re.search(r"[،,|/\-*\\]+", text):
        return


        raw_names = re.split(r"[،,*\-|/\\]+", text.strip("()"))
        cleaned = []

        for name in raw_names:
            name = name.strip()

            if not name or name in cleaned:
                continue

            if len(name) > 12:
                return await ev.reply(f"⚠️ **يابوي اسم التيم `{name}` مره طويل والحد المسموح هو** (`١٢ حرف`)")

            cleaned.append(name)

        if len(cleaned) != TEAMS[chat]['count']:
            return await ev.reply(
                f"⚠️ عدد الأسماء: ({len(cleaned)})\n لا يطابق عدد الفرق المحددة: ({TEAMS[chat]['count']}), حاول مجددًا"
            )
           
        TEAMS[chat]['_preview_names'] = cleaned
           
        preview = "**📋 المعاينة قبل الحفظ:**\n\n"
        for i, name in enumerate(cleaned, 1):
            preview += f"{i}. {name}\n"
            
        buttons = [
            [Button.inline("✅ تأكيد الأسماء", b"confirm_names")],
            [Button.inline("🔄 تعديل", b"team_names")]
        ]
        return await ev.reply(preview, buttons=buttons)

@zedub.bot_cmd(pattern=fr"^{cmhd}autoreg(?:\s+(.+))?$")
async def autoreg(event):
    if not await is_user_admin(event):
        return
    chat = event.chat_id
    if not TEAM_MODE.get(chat):
        return

    args = event.pattern_match.group(1)
    args = args.split() if args else []
    uid = await get_user_id(event, args)
    if not uid:
        return await safe_edit(event, "❗ حدد مستخدم بالرد أو منشن أو آيدي")
   
    for members in TEAMS[chat]['members'].values():
        if uid in members:
            return await safe_edit(event, "❗ المستخدم مسجل بالفعل في فريق")

    idx = uid % TEAMS[chat]['count']
    TEAMS[chat]['members'].setdefault(idx, []).append(uid)
    team_name = TEAMS[chat]['names'][idx]
    return await safe_edit(event, f"✅ انضم إلى فريق: {team_name}")

@zedub.bot_cmd(pattern=fr"^{re.escape(cmhd)}(?:tp|tdp)(?:\s+(.+))?$")
async def manage_team_points(event):
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ الأمر للمشرفين فقط")

    chat = event.chat_id
    if not TEAM_MODE.get(chat):
        return

    cmd = event.text.split()[0].lower().replace(cmhd, "/")
    args = event.pattern_match.group(1)
    args = args.split() if args else []

    uid = await get_user_id(event, args)
    if not uid:
        return await safe_edit(event, "❗ حدد مستخدم بالرد/منشن/آيدي")

    team_idx = None
    for idx, members in TEAMS[chat]['members'].items():
        if uid in members:
            team_idx = idx
            break

    if team_idx is None:
        return await safe_edit(event, "❗ المستخدم غير مسجل في أي فريق")

    number = 1
    for arg in args:
        if arg.isdigit():
            number = int(arg)
            break

    delta = number if cmd == "/tp" else -number  # يحترم القيمة المُدخلة من المستخدم

    members = TEAMS[chat]['members'][team_idx]
    for member_id in members:
        current = get_points(chat, member_id)
        new_pts = max(min(current + delta, MAX_POINTS), 0)  # يمنع تجاوز الحد

        set_points(chat, member_id, new_pts)

    total = sum(get_points(chat, member_id) for member_id in members)

    sign = "➕" if delta > 0 else "➖"
    action = "إضـافـة" if delta > 0 else "خـصـم"
    team_name = TEAMS[chat]['names'][team_idx]

    return await safe_edit(
        event,
        f"{sign} | تـم {action} :  (**{abs(delta)}**) نقاط"
        f"\n🎫 | الـفـريـق :  `{team_name}`"
        f"\n🔢 | نـقـاطـهـم : (**{total}**)"
    )
    
@zedub.bot_cmd(pattern=fr"^{cmhd}tps$")
async def team_points_summary(event):
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ الأمر للمشرفين فقط")

    chat = event.chat_id
    if not TEAM_MODE.get(chat) or not TEAMS.get(chat):
        return await safe_edit(event, "❗ لا يوجد فرق أو لم يتم التفعيل")

    text = "🔢 **نـقـاط الـفـرق:**\n"

    for idx, name in enumerate(TEAMS[chat]['names']):
        members = TEAMS[chat]['members'].get(idx, [])
        total = sum(get_points(chat, uid) for uid in members)
        member_count = len(members)

        text += f"\n• اسـم الـفـريـق : `{name}`"
        text += f"\n• الأعـضـاء : `({member_count} / {MAX_TEAM_MEMBERS})`"
        text += f"\n• الــنــقــاط : (**{total}**)"
        text += "\n\n================\n"

    await safe_edit(event, text.strip())


@zedub.bot_cmd(pattern=fr"^{cmhd}tpoints$")
async def tpoints_alias(event):
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ الأمر للمشرفين فقط")
    return await team_points_summary(event)
    

@zedub.bot_cmd(pattern=fr"^{cmhd}showt$")
async def show_teams_members(event):
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ الأمر للمشرفين فقط")

    chat = event.chat_id
    if not TEAM_MODE.get(chat) or not TEAMS.get(chat):
        return await safe_edit(event, "❗ لا يوجد فرق أو لم يتم التفعيل")

    text = "🗂️ **تفاصيل الفرق وأعضائها:**\n"

    for idx, name in enumerate(TEAMS[chat]['names']):
        members = TEAMS[chat]['members'].get(idx, [])
        member_count = len(members)

        text += f"\n• اسم التيم : `{name}`"
        text += f"\n• الأعـضـاء : `({member_count} / {MAX_TEAM_MEMBERS})`\
        \n• تـفـاصـيل :\n"

        if not members:
            text += "    - ( الفريق فاضي )\n\n"
        else:
            entities = await asyncio.gather(*(event.client.get_entity(uid) for uid in members))
            for i, u in enumerate(entities, start=1):
                if u.username:
                    text += f"    {i}- @{u.username}\n\n"
                else:
                    text += f"    {i}- [{u.first_name}](tg://user?id={u.id})\n\n"

        text += "================\n"

    await safe_edit(event, text.strip())

@zedub.bot_cmd(pattern=fr"^{cmhd}topt$")
async def show_top_in_teams(event):
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ الأمر للمشرفين فقط")
        
    chat = event.chat_id
    if not TEAM_MODE.get(chat):
        return await safe_edit(event, "❗ وضع الفرق غير مفعل")
    
    text = "🏅 | **أفضل اللاعبين إحرازاً للنقاط في كل فريق:**\n"

    for idx, name in enumerate(TEAMS[chat]['names']):
        top_members = get_team_top_members(chat, idx)

        text += f"\n• اسم الفريق : `{name}`\n"
        text += f"• أفضل الأعضاء:\n"

        if not top_members:
            text += "    - ( لا يوجد أعضاء )\n"
        else:
            for i, (uid, pts) in enumerate(top_members[:3], start=1):
                user = await event.client.get_entity(uid)
                mention = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={uid})"
                text += f"    {i}- {mention} ({pts})\n"

        text += "\n================"

    await safe_edit(event, text.strip())

@zedub.bot_cmd(pattern=fr"^{cmhd}trstp$")
async def reset_points(event):
    """إعادة جميع النقاط إلى صفر"""
    if not event.is_group:
        return await safe_edit(event, "❗️يعمل فقط في المجموعات")
    if not await is_user_admin(event):
        return await safe_edit(event, "❗️الأمر متاح للمشرفين فقط")
    ranking = get_all_points(event.chat_id)
    if ranking:
        reset_all_points(event.chat_id)
        return await safe_edit(event, "✅ تم ترسيت نقاط الأفرقة")
    else:
        return await safe_edit(event, "🍃 لا يوجد نقاط مسجلة حالياً")

# It's not the end .. (: