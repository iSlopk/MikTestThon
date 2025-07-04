import sqlite3
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
DB_PATH = "points_db.sqlite"

AWAITING_NAMES = set()
TEAM_MODE = {}
TEAMS = {}

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

@zedub.bot_cmd(pattern=fr"^{cmhd}tmod(?:\s+(on|off))?$")
async def cmd_tmod(event):
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ الأمر للمشرفين فقط.")

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
        await event.reply("✅ تم تفعيل وضع الفرق.", buttons=buttons)
        await event.delete()
        return

    if arg == "off":
        TEAM_MODE[event.chat_id] = False
        return await safe_edit(event, "✅ تم الرجوع لوضع الأفراد.")

    return await safe_edit(
        event,
        "❗ استخدم:\n/tmod on ← تفعيل وضع الفرق\n/tmod off ← تعطيل وضع الفرق"
    )

@zedub.tgbot.on(events.CallbackQuery)
async def callback_handler(event):
    chat = event.chat_id
    data = event.data.decode()

    if data == "setup_teams":
        kb = [
            [Button.inline(str(i), f"team_count_{i}") for i in range(2, 6)],
            [Button.inline(str(i), f"team_count_{i}") for i in range(6, 11)],
            [Button.inline("✔️ تحديد أسماء الفرق", b"team_names")]
        ]
        return await event.edit("اختر عدد الفرق:", buttons=kb)

    if data.startswith("team_count_"):
        try:
            n = int(data.split("_")[-1])
            TEAMS[chat]['count'] = n
            return await event.edit(
                f"✅ اخترت {n} فرق.\nاضغط لتعيين أسماء الفرق.",
                buttons=[[Button.inline("📝 أسماء الفرق", b"team_names")]]
            )
        except ValueError:
            return await event.answer("⚠️ رقم غير صالح.", alert=True)

    if data == "team_names":
        AWAITING_NAMES.add(chat)
        return await event.reply(
            "📩 أرسل أسماء الفرق مثل: (فريق1 🔴، فريق2 🟢،...)"
        )

    if data == "start_signup":
        # زر لكل فريق
        team_buttons = [
            [Button.inline(f"➕ انضم لـ {name}", f"join_team_{i}")]
            for i, name in enumerate(TEAMS[chat]['names'])
        ]

        # بناء نص عرض الفرق + أعضائها
        lines = ["🔔 **التسجيل مفتوح الآن**", ""]
        for idx, name in enumerate(TEAMS[chat]['names']):
            members = TEAMS[chat]['members'].get(idx, [])
            if members:
                mentions = "، ".join(f"[{(await event.client.get_entity(uid)).first_name}](tg://user?id={uid})"
                                     for uid in members)
            else:
                mentions = "— لا أحد بعد"
            lines.append(f"**{name}**:\n{mentions}\n")

        return await event.edit("\n".join(lines), buttons=team_buttons, link_preview=False)

    if data.startswith("join_team_"):
        idx = int(data.split("_")[-1])
        uid = event.sender_id

        # تحقق من الانضمام المسبق
        for members in TEAMS[chat]['members'].values():
            if uid in members:
                return await event.answer("❗ أنت بالفعل في فريق.", alert=True)

        TEAMS[chat]['members'].setdefault(idx, []).append(uid)
        team_name = TEAMS[chat]['names'][idx]
        await event.answer(f"✅ انضممت إلى فريق {team_name}", alert=True)

        # تحديث العرض بعد الانضمام
        team_buttons = [
            [Button.inline(f"➕ انضم لـ {name}", f"join_team_{i}")]
            for i, name in enumerate(TEAMS[chat]['names'])
        ]

        lines = ["🔔 **التسجيل مفتوح الآن**", ""]
        for j, name in enumerate(TEAMS[chat]['names']):
            members = TEAMS[chat]['members'].get(j, [])
            if members:
                mentions = "، ".join(f"[{(await event.client.get_entity(m)).first_name}](tg://user?id={m})"
                                     for m in members)
            else:
                mentions = "— لا أحد بعد"
            lines.append(f"**{name}**:\n{mentions}\n")

        return await event.edit("\n".join(lines), buttons=team_buttons, link_preview=False)

@zedub.bot_cmd(events.NewMessage)
async def receive_names(ev):
    chat = ev.chat_id
    if not ev.is_group or chat not in AWAITING_NAMES:
        return

    if TEAMS.get(chat) and not TEAMS[chat]['names']:
        text = ev.text.strip()
        names = [x.strip() for x in text.strip("()").split("،")]

        if len(names) == TEAMS[chat]['count']:
            TEAMS[chat]['names'] = names
            TEAMS[chat]['members'] = {i: [] for i in range(len(names))}
            AWAITING_NAMES.discard(chat)  # ✅ أوقف الانتظار بعد النجاح
            await ev.reply("✅ تم تحديد الأسماء.", buttons=[[Button.inline("🚀 ابدأ التسجيل", b"start_signup")]])
        else:
            await ev.reply(
                f"⚠️ عدد الأسماء ({len(names)}) لا يطابق عدد الفرق المحددة ({TEAMS[chat]['count']}), حاول مجددًا."
            )

@zedub.bot_cmd(pattern=fr"^{cmhd}autoreg(?:\s+(.+))?$")
async def autoreg(event):
    chat = event.chat_id
    if not TEAM_MODE.get(chat):
        return

    args = event.pattern_match.group(1)
    args = args.split() if args else []
    uid = await get_user_id(event, args)
    if not uid:
        return await safe_edit(event, "❗ حدد مستخدم بالرد أو منشن أو آيدي.")

    for members in TEAMS[chat]['members'].values():
        if uid in members:
            return await safe_edit(event, "❗ المستخدم مسجل بالفعل في فريق.")

    idx = uid % TEAMS[chat]['count']
    TEAMS[chat]['members'].setdefault(idx, []).append(uid)
    team_name = TEAMS[chat]['names'][idx]
    return await safe_edit(event, f"✅ انضم إلى فريق: {team_name}")

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tp|{cmhd}tdp)(?:\s+(.+))?$")
async def manage_team_points(event):
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
        return await safe_edit(event, "❗ المستخدم غير مسجل في أي فريق.")

    members = TEAMS[chat]['members'][team_idx]
    delta = 1 if cmd == "/tp" else -1

    for member_id in members:
        current = get_points(chat, member_id)
        new_pts = max(current + delta, 0)
        set_points(chat, member_id, new_pts)

    sign = "➕" if delta > 0 else "➖"
    action = "إضافة" if delta > 0 else "خصم"
    team_name = TEAMS[chat]['names'][team_idx]
    return await safe_edit(
        event,
        f"{sign} تم {action} نقطة لكل أعضاء فريق **{team_name}**."
    )