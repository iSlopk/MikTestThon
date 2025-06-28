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

# ====== متغيرات إدارة الفرق ======
TEAM_MODE_STATUS = False
TEAM_COUNT = 0
TEAM_NAMES = []
TEAMS = {}
TEAM_MEMBERS = {}  # team_name: [user_ids]
USER_TEAM = {}     # user_id: team_name
TEAM_SWITCH = {}   # user_id: True/False (تغيير لمرة واحدة)
TEAMS_MSG_ID = None

# ========== قاعدة البيانات ==========
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
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO points (chat_id, user_id, points) VALUES (?, ?, ?)",
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

# ========== دوال مساعدة ==========
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

def is_admin(user_id):
    # عدل هذا حسب نظام الصلاحيات لديك
    return True

# ========== لوحة تحكم وضع الفرق ==========
async def send_team_mode_panel(event):
    buttons = [
        [Button.inline("إغلاق الوضع والعودة لوضع الأفراد", b"close_team_mode")],
        [Button.inline("إنشاء الأفرقة", b"create_teams")]
    ]
    await event.respond("لوحة تحكم الأفرقة:", buttons=buttons)

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tmod)$")
async def tmod_handler(event):
    global TEAM_MODE_STATUS
    if not is_admin(event.sender_id):
        return
    TEAM_MODE_STATUS = True
    await send_team_mode_panel(event)

@zedub.tgbot.on(events.CallbackQuery(data=b"close_team_mode"))
async def close_team_mode(event):
    global TEAM_MODE_STATUS, TEAM_COUNT, TEAM_NAMES, TEAMS, TEAM_MEMBERS, USER_TEAM, TEAM_SWITCH, TEAMS_MSG_ID
    TEAM_MODE_STATUS = False
    TEAM_COUNT = 0
    TEAM_NAMES = []
    TEAMS = {}
    TEAM_MEMBERS = {}
    USER_TEAM = {}
    TEAM_SWITCH = {}
    TEAMS_MSG_ID = None
    await event.edit("تم العودة لوضع الأفراد.")

@zedub.tgbot.on(events.CallbackQuery(data=b"create_teams"))
async def create_teams_panel(event):
    buttons = [
        [Button.inline("عدد الأفرقة", b"set_team_count")],
        [Button.inline("أسماء الأفرقة", b"set_team_names")]
    ]
    await event.edit("إعدادات الأفرقة:", buttons=buttons)

@zedub.tgbot.on(events.CallbackQuery(data=b"set_team_count"))
async def choose_team_count(event):
    btns = []
    for i in range(2, 11, 2):
        btns.append([Button.inline(str(j), f"team_count_{j}".encode()) for j in range(i, min(i+2, 11))])
    await event.edit("اختر عدد الأفرقة:", buttons=btns)

@zedub.tgbot.on(events.CallbackQuery(pattern=b"team_count_(\d+)"))
async def set_team_count(event):
    global TEAM_COUNT
    count = int(event.pattern_match.group(1).decode())
    TEAM_COUNT = count
    await event.edit(f"عدد الأفرقة المختار: {count}\nالآن قم بتعيين أسماء الأفرقة من لوحة التحكم.")
    if TEAM_NAMES and len(TEAM_NAMES) == count:
        await show_start_button(event)

@zedub.tgbot.on(events.CallbackQuery(data=b"set_team_names"))
async def ask_team_names(event):
    await event.edit("أرسل أسماء الأفرقة هكذا (اسم1، اسم2، ...) بين قوسين () كرد على هذه الرسالة.")
    global TEAMS_MSG_ID
    TEAMS_MSG_ID = event.id

@zedub.tgbot.on(events.NewMessage())
async def receive_team_names(event):
    global TEAM_NAMES, TEAMS, TEAM_MEMBERS, TEAM_COUNT
    if hasattr(event, "reply_to_msg_id") and TEAMS_MSG_ID and event.reply_to_msg_id == TEAMS_MSG_ID:
        text = event.raw_text.strip()
        if text.startswith("(") and text.endswith(")"):
            names = [n.strip() for n in text[1:-1].split(',')]
            if len(names) != TEAM_COUNT:
                return await event.reply(f"عدد الأسماء يجب أن يكون {TEAM_COUNT}.")
            TEAM_NAMES = names
            TEAMS = {name: {"members": [], "points": 0} for name in names}
            TEAM_MEMBERS = {name: [] for name in names}
            await event.reply(f"تم تعيين أسماء الفرق:\n" + "، ".join(names))
            if TEAM_COUNT:
                await show_start_button(event)

async def show_start_button(event):
    buttons = [[Button.inline("البدء", b"start_teams")]]
    await event.respond("جاهز لبدء التسجيل! عند الضغط يبدأ الأعضاء باختيار فريقهم.", buttons=buttons)

@zedub.tgbot.on(events.CallbackQuery(data=b"start_teams"))
async def start_teams(event):
    team_buttons = []
    for name in TEAM_NAMES:
        team_buttons.append([Button.inline(name, f"join_team_{name}".encode())])
    msg = await event.respond("بدأ تسجيل الفرق! اختر فريقك:", buttons=team_buttons)
    global TEAMS_MSG_ID
    TEAMS_MSG_ID = msg.id

@zedub.tgbot.on(events.CallbackQuery(pattern=b"join_team_(.+)"))
async def join_team(event):
    global TEAM_MEMBERS, USER_TEAM, TEAM_SWITCH, TEAMS
    user_id = event.sender_id
    team_chosen = event.pattern_match.group(1).decode()
    old_team = USER_TEAM.get(user_id)
    if old_team:
        # تغيير لمرة واحدة فقط
        if TEAM_SWITCH.get(user_id, False):
            return await event.answer("لا يمكنك تغيير فريقك أكثر من مرة.", alert=True)
        TEAM_MEMBERS[old_team].remove(user_id)
        TEAM_SWITCH[user_id] = True
    else:
        TEAM_SWITCH[user_id] = False
    USER_TEAM[user_id] = team_chosen
    TEAM_MEMBERS[team_chosen].append(user_id)
    await event.answer("تم تسجيلك أو نقل فريقك بنجاح!", alert=True)
    await update_teams_message(event)

async def update_teams_message(event):
    """تحديث رسالة الفرق"""
    global TEAMS_MSG_ID
    if not TEAMS_MSG_ID:
        return
    text = "توزيع الفرق الحالي:\n"
    for team, members in TEAM_MEMBERS.items():
        text += f"\n<b>{team}</b>:\n"
        for user_id in members:
            try:
                user = await event.client.get_entity(user_id)
                name = user.first_name
            except Exception:
                name = str(user_id)
            text += f"- {name} (<code>{user_id}</code>)\n"
    try:
        await event.client.edit_message(event.chat_id, TEAMS_MSG_ID, text, parse_mode="html")
    except Exception:
        pass

# ========== أوامر الفرق ==========
@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tp)$")
async def team_points(event):
    """عرض نقاط الفرق"""
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    text = "**📊 نقاط الفرق:**\n"
    for name in TEAM_NAMES:
        pts = TEAMS.get(name, {}).get("points", 0)
        text += f"• {name}: {pts} نقاط\n"
    await event.reply(text)

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tdp)$")
async def team_members_cmd(event):
    """عرض أعضاء كل فريق"""
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    text = "**📊 الفرق وأعضاؤها:**\n"
    for name in TEAM_NAMES:
        text += f"\n• {name}:\n"
        for user_id in TEAM_MEMBERS.get(name, []):
            text += f"- [{user_id}](tg://user?id={user_id})\n"
    await event.reply(text)

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}trstp)$")
async def reset_teams_points(event):
    """تصفير نقاط الفرق"""
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    for name in TEAM_NAMES:
        TEAMS[name]["points"] = 0
    await event.reply("✅ تم تصفير نقاط جميع الفرق.")

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tps)$")
async def teams_status(event):
    """عرض توزيع الفرق"""
    await team_members_cmd(event)

# ========== نهاية ==========