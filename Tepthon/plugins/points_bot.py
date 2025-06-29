import asyncio
import sqlite3
from telethon import events, Button
from telethon.errors.rpcerrorlist import MessageAuthorRequiredError

from . import zedub
from ..Config import Config
from ..core.managers import edit_or_reply

plugin_category = "بوت النقاط"
cmhd = Config.COMMAND_HAND_LER
DB_PATH = "points_db.sqlite"

# --- متغيرات وضع الفرق ---
TEAM_MODE_STATUS = {}  # chat_id: True/False
TEAM_COUNT = {}        # chat_id: int
TEAM_NAMES = {}        # chat_id: [name, ...]
TEAMS = {}             # chat_id: {team_name: {"members": [], "points": 0}}
TEAM_MEMBERS = {}      # chat_id: {team_name: [user_id, ...]}
USER_TEAM = {}         # chat_id: {user_id: team_name}
TEAM_SWITCH = {}       # chat_id: {user_id: True/False}
TEAMS_MSG_ID = {}      # chat_id: msg_id
TEAMS_SETUP_MSG_ID = {}  # chat_id: msg_id (لبدء استقبال أسماء الفرق)

# --- قاعدة البيانات ---
def get_db():
    return sqlite3.connect(DB_PATH)

def create_table():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS points (
            chat_id INTEGER,
            user_id INTEGER,
            points INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )""")
create_table()

def get_points(chat_id, user_id):
    with get_db() as db:
        cur = db.execute(
            "SELECT points FROM points WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        return row[0] if row else 0

def set_points(chat_id, user_id, points):
    with getINSERT OR REPLACE INTO points (chat_id, user_id, points) VALUES (?, ?, ?)",
            (chat_id, user_id, points)
        )

def get_all_points(chat_id):
    with get_db() as db:
        cur = db.execute(
            "SELECT user_id, points FROM points WHERE chat_id=? AND points > 0 ORDER BY points DESC",
            (chat_id,)
        )
        return cur.fetchall()

def reset_all_points(chat_id):
    with get_db() as db:
        db.execute(
            "UPDATE points SET points=0 WHERE chat_id=?",
            (chat_id,)
        )

# --- دوال مساعدة ---
async def safe_edit_or_reply(event, text, **kwargs):
    try:
        await edit_or_reply(event, text, **kwargs)
    except MessageAuthorRequiredError:
        await event.reply(text, **kwargs)

async def get_user_id(event, args):
    if event.is_reply:
        reply = await event.get_reply_message()
        return reply.sender_id
    if args:
        if args[0].startswith("@"):
            try:
                entity = await event.client.get_entity(args[0])
                return entity.id
            except Exception:
                pass
        try:
            return int(args[0])
        except Exception:
            pass
    return None

def is_admin(event):
    # تحقق من صلاحيات المشرف مباشرة (يمكنك تطويره)
    return event.sender_id == event.chat.creator_id or getattr(event.sender, 'admin_rights', None)

# --- نظام النقاط الفردية والأفرقة ---
@zedub.bot_cmd(pattern=fr"^(?:{cmhd}p|{cmhd}delp)(?:\s+(.+))?$")
async def points_manage(event):
    """إضافة أو خصم نقاط (فردي أو فرق تلقائي)"""
    chat_id = event.chat_id
    if TEAM_MODE_STATUS.get(chat_id, False):
        return await team_manage_points(event)
    else:
        return await individual_manage_points(event)

async def individual_manage_points(event):
    """إدارة النقاط في الوضع الفردي"""
    if not event.is_group:
        return await safe_edit_or_reply(event, "❗️يعمل فقط في المجموعات.")
    perms = await event.client.get_permissions(event.chat_id, event.sender_id)
    if not perms.is_admin:
        return await safe_edit_or_reply(event, "❗️الأمر متاح للمشرفين فقط.")
    args = event.pattern_match.group(1)
    args = args.split() if args else []
    cmd = event.text.split()[0].lower().replace(cmhd, "/")
    points = 1
    if len(args) > 1:
        try:
            points = abs(int(args[1]))
        except Exception:
            pass
    elif event.is_reply and args:
        try:
            points = abs(int(args[0]))
        except Exception:
            pass
    return await handle_event(event, args, cmd, points)

async def handle_event(event, args, cmd, points):
    uid = await get_user_id(event, args)
    if uid is None:
        return await safe_edit_or_reply(event, "❗️يرجى تحديد المستخدم بالرد أو المنشن أو الإيدي.")
    try:
        user = await event.client.get_entity(uid)
        name = user.first_name + (" " + user.last_name if user.last_name else "")
    except Exception:
        name = str(uid)
    user_id = uid
    old = get_points(event.chat_id, uid)
    if cmd == "/p":
        new_points = old + points
        set_points(event.chat_id, uid, new_points)
        return await safe_edit_or_reply(
            event,
            f"➕ تم إضافة {points} نقطة.\n👤 المستخدم : [{name}](tg://user?id={user_id})\n🔢 عدد نقاطه : [{new_points}]"
        )
    else:
        new_points = max(old - points, 0)
        set_points(event.chat_id, uid, new_points)
        return await safe_edit_or_reply(
            event,
            f"➖ تم خصم {points} نقطة.\n👤 المستخدم : [{name}](tg://user?id={user_id})\n🔢 عدد نقاطه : [{new_points}]"
        )

async def team_manage_points(event):
    """إدارة النقاط للفرق"""
    chat_id = event.chat_id
    args = event.pattern_match.group(1)
    args = args.split() if args else []
    cmd = event.text.split()[0].lower().replace(cmhd, "/")
    points = 1
    if len(args) > 1:
        try:
            points = abs(int(args[1]))
        except Exception:
            pass
    elif event.is_reply and args:
        try:
            points = abs(int(args[0]))
        except Exception:
            pass
    uid = await get_user_id(event, args)
    if uid is None:
        return await safe_edit_or_reply(event, "❗️يرجى تحديد المستخدم بالرد أو المنشن أو الإيدي.")
    chat_user_team = USER_TEAM.get(chat_id, {})
    team_name = chat_user_team.get(uid)
    if not team_name:
        return await safe_edit_or_reply(event, "❗️المستخدم غير مسجل في أي فريق.")
    teams = TEAMS.get(chat_id, {})
    team = teams.get(team_name)
    if not team:
        return await safe_edit_or_reply(event, "❗️حدث خطأ مع الفريق.")
    if cmd == "/p":
        team["points"] += points
        return await safe_edit_or_reply(event, f"✅ تم إضافة {points} نقطة لفريق {team_name}. مجموعه الآن: {team['points']}")
    else:
        team["points"] = max(0, team["points"] - points)
        return await safe_edit_or_reply(event, f"✅ تم خصم {points} نقطة من فريق {team_name}. مجموعه الآن: {team['points']}")

# --- أوامر عرض النقاط ---
@zedub.bot_cmd(pattern=fr"^(?:{cmhd}ps|{cmhd}points)(?:\s+(.+))?$")
async def show_points(event):
    chat_id = event.chat_id
    if TEAM_MODE_STATUS.get(chat_id, False):
        return await show_team_points(event)
    else:
        return await show_individual_points(event)

async def show_individual_points(event):
    if not event.is_group:
        return await safe_edit_or_reply(event, "❗️يعمل فقط في المجموعات.")
    args = event.pattern_match.group(1)
    args = args.split() if args else []
    uid = await get_user_id(event, args)
    ranking = get_all_points(event.chat_id)
    if uid is None:
        if not ranking:
            return await safe_edit_or_reply(event, "🍃 لا يوجد نقاط مسجلة في الشات.")
        text = "**📊 | نشرة النقاط في المجموعة **:\n\n"
        for i, (user_id, pts) in enumerate(ranking, 1):
            try:
                user = await event.client.get_entity(user_id)
                name = user.first_name + (" " + user.last_name if user.last_name else "")
            except Exception:
                name = str(user_id)
            text += f"{i}- [{name}](tg://user?id={user_id}) [{pts}]\n"
        return await safe_edit_or_reply(event, text)
    else:
        pts = get_points(event.chat_id, uid)
        try:
            user = await event.client.get_entity(uid)
            name = user.first_name + (" " + user.last_name if user.last_name else "")
        except Exception:
            name = str(uid)
        return await safe_edit_or_reply(event, f"👤 المستخدم : [{name}](tg://user?id={uid})\n🔢 عدد النقاط : [{pts}].")

async def show_team_points(event):
    chat_id = event.chat_id
    teams = TEAMS.get(chat_id, {})
    if not teams:
        return await event.reply("❌ لا يوجد فرق معرفة.")
    text = "**📊 نقاط الفرق:**\n"
    for name, data in teams.items():
        text += f"• {name}: {data['points']} نقاط\n"
    await event.reply(text)

@zedub.bot_cmd(pattern=fr"^{cmhd}rstp$")
async def reset_points(event):
    """إعادة جميع النقاط إلى صفر"""
    chat_id = event.chat_id
    if TEAM_MODE_STATUS.get(chat_id, False):
        for name in (TEAM_NAMES.get(chat_id) or []):
            TEAMS[chat_id][name]["points"] = 0
        return await event.reply("✅ تم تصفير نقاط جميع الفرق.")
    else:
        if not event.is_group:
            return await safe_edit_or_reply(event, "❗️يعمل فقط في المجموعات.")
        perms = await event.client.get_permissions(event.chat_id, event.sender_id)
        if not perms.is_admin:
            return await safe_edit_or_reply(event, "❗️الأمر متاح للمشرفين فقط.")
        ranking = get_all_points(event.chat_id)
        if ranking:
            reset_all_points(event.chat_id)
            return await safe_edit_or_reply(event, "✅ تم ترسيت نقاط الشات.")
        else:
            return await safe_edit_or_reply(event, "🍃 لا يوجد نقاط مسجلة حالياً.")

# --- نظام الأفرقة ---

async def send_team_mode_panel(event):
    buttons = [
        [Button.inline("إعداد الأفرقة", b"create_teams")],
        [Button.inline("إغلاق وضع الفرق", b"close_team_mode")]
    ]
    await event.respond("لوحة تحكم الأفرقة:", buttons=buttons)

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tmod)$")
async def tmod_handler(event):
    chat_id = event.chat_id
    if not is_admin(event):
        return
    TEAM_MODE_STATUS[chat_id] = True
    await send_team_mode_panel(event)

@zedub.tgbot.on(events.CallbackQuery(data=b"close_team_mode"))
async def close_team_mode(event):
    chat_id = event.chat_id
    TEAM_MODE_STATUS[chat_id] = False
    TEAM_COUNT[chat_id] = 0
    TEAM_NAMES[chat_id] = []
    TEAMS[chat_id] = {}
    TEAM_MEMBERS[chat_id] = {}
    USER_TEAM[chat_id] = {}
    TEAM_SWITCH[chat_id] = {}
    TEAMS_MSG_ID[chat_id] = None
    TEAMS_SETUP_MSG_ID[chat_id] = None
    await event.edit("تم العودة لوضع الأفراد.")

@zedub.tgbot.on(events.CallbackQuery(data=b"create_teams"))
async def create_teams_panel(event):
    buttons = [
        [Button.inline("عدد الفرق", b"set_team_count")],
        [Button.inline("أسماء الفرق", b"set_team_names")],
        [Button.inline("إغلاق", b"close_team_mode")]
    ]
    await event.edit("إعدادات الأفرقة:", buttons=buttons)

@zedub.tgbot.on(events.CallbackQuery(data=b"set_team_count"))
async def choose_team_count(event):
    btns = []
    for i in range(2, 11, 2):
        btns.append([Button.inline(str(j), f"team_count_{j}".encode()) for j in range(i, min(i+2, 11))])
    await event.edit("اختر عدد الفرق:", buttons=btns + [[Button.inline("إغلاق", b"close_team_mode")]])

@zedub.tgbot.on(events.CallbackQuery(pattern=b"team_count_(\d+)"))
async def set_team_count(event):
    chat_id = event.chat_id
    count = int(event.pattern_match.group(1).decode())
    TEAM_COUNT[chat_id] = count
    await event.edit(f"عدد الفرق المختار: {count}\nالآن قم بتعيين أسماء الفرق من لوحة التحكم.")
    if TEAM_NAMES.get(chat_id) and len(TEAM_NAMES[chat_id]) == count:
        await show_start_button(event)

@zedub.tgbot.on(events.CallbackQuery(data=b"set_team_names"))
async def ask_team_names(event):
    chat_id = event.chat_id
    msg = await event.edit("أرسل أسماء الفرق هكذا (اسم1، اسم2، ...) بين قوسين () كرد على هذه الرسالة.")
    TEAMS_SETUP_MSG_ID[chat_id] = msg.id

@zedub.tgbot.on(events.NewMessage())
async def receive_team_names(event):
    chat_id = event.chat_id
    msg_id = TEAMS_SETUP_MSG_ID.get(chat_id)
    if not msg_id:
        return
    if getattr(event, "reply_to_msg_id", None) == msg_id:
        text = event.raw_text.strip()
        if text.startswith("(") and text.endswith(")"):
            names = [n.strip() for n in text[1:-1].split(',')]
            if TEAM_COUNT.get(chat_id, 0) != len(names):
                return await event.reply(f"عدد الأسماء يجب أن يكون {TEAM_COUNT.get(chat_id,0)}.")
            TEAM_NAMES[chat_id] = names
            TEAMS[chat_id] = {name: {"members": [], "points": 0} for name in names}
            TEAM_MEMBERS[chat_id] = {name: [] for name in names}
            USER_TEAM[chat_id] = {}
            TEAM_SWITCH[chat_id] = {}
            await event.reply(f"تم تعيين أسماء الفرق:\n" + "، ".join(names))
            await show_start_button(event)

async def show_start_button(event):
    buttons = [[Button.inline("بدء التسجيل", b"start_teams")], [Button.inline("إغلاق", b"close_team_mode")]]
    await event.respond("جاهز لبدء التسجيل! عند الضغط يبدأ الأعضاء باختيار فريقهم.", buttons=buttons)

@zedub.tgbot.on(events.CallbackQuery(data=b"start_teams"))
async def start_teams(event):
    chat_id = event.chat_id
    team_buttons = []
    for name in TEAM_NAMES.get(chat_id, []):
        team_buttons.append([Button.inline(name, f"join_team_{name}".encode())])
    msg = await event.respond("بدأ تسجيل الفرق! اختر فريقك:", buttons=team_buttons + [[Button.inline("إغلاق", b"close_team_mode")]])
    TEAMS_MSG_ID[chat_id] = msg.id

@zedub.tgbot.on(events.CallbackQuery(pattern=b"join_team_(.+)"))
async def join_team(event):
    chat_id = event.chat_id
    user_id = event.sender_id
    team_chosen = event.pattern_match.group(1).decode()
    USER_TEAM.setdefault(chat_id, {})
    TEAM_MEMBERS.setdefault(chat_id, {})
    TEAM_SWITCH.setdefault(chat_id, {})
    old_team = USER_TEAM[chat_id].get(user_id)
    if old_team:
        if TEAM_SWITCH[chat_id].get(user_id, False):
            return await event.answer("لا يمكنك تغيير فريقك أكثر من مرة.", alert=True)
        TEAM_MEMBERS[chat_id][old_team].remove(user_id)
        TEAM_SWITCH[chat_id][user_id] = True
    else:
        TEAM_SWITCH[chat_id][user_id] = False
    USER_TEAM[chat_id][user_id] = team_chosen
    TEAM_MEMBERS[chat_id].setdefault(team_chosen, []).append(user_id)
    await event.answer("تم تسجيلك أو نقل فريقك بنجاح!", alert=True)
    await update_teams_message(event)

async def update_teams_message(event):
    chat_id = event.chat_id
    msg_id = TEAMS_MSG_ID.get(chat_id)
    if not msg_id:
        return
    text = "توزيع الفرق الحالي:\n"
    for team, members in (TEAM_MEMBERS.get(chat_id) or {}).items():
        text += f"\n<b>{team}</b>:\n"
        for user_id in members:
            try:
                user = await event.client.get_entity(user_id)
                name = user.first_name
            except Exception:
                name = str(user_id)
            text += f"- {name} (<code>{user_id}</code>)\n"
    try:
        await event.client.edit_message(chat_id, msg_id, text, parse_mode="html")
    except Exception:
        pass

# --- أوامر الفرق ---
@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tp)$")
async def team_points(event):
    chat_id = event.chat_id
    teams = TEAMS.get(chat_id, {})
    if not teams:
        return await event.reply("❌ لا يوجد فرق معرفة.")
    text = "**📊 نقاط الفرق:**\n"
    for name, data in teams.items():
        text += f"• {name}: {data['points']} نقاط\n"
    await event.reply(text)

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tdp)$")
async def team_members_cmd(event):
    chat_id = event.chat_id
    members = TEAM_MEMBERS.get(chat_id, {})
    if not members:
        return await event.reply("❌ لا يوجد فرق معرفة.")
    text = "**📊 الفرق وأعضاؤها:**\n"
    for name, ids in members.items():
        text += f"\n• {name}:\n"
        for uid in ids:
            text += f"- [{uid}](tg://user?id={uid})\n"
    await event.reply(text)

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}trstp)$")
async def reset_teams_points(event):
    chat_id = event.chat_id
    for name in (TEAM_NAMES.get(chat_id) or []):
        TEAMS[chat_id][name]["points"] = 0
    await event.reply("✅ تم تصفير نقاط جميع الفرق.")

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tps)$")
async def teams_status(event):
    await team_members_cmd(event)

# --- نهاية ---