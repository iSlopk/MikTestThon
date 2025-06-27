import asyncio
import sqlite3
from telethon import events
from telethon.errors.rpcerrorlist import MessageAuthorRequiredError
from . import zedub
from ..Config import Config
from ..core.managers import edit_or_reply

TEAM_MODE_STATUS = False
TEAMS = {}

plugin_category = "بوت النقاط"
cmhd = Config.COMMAND_HAND_LER
DB_PATH = "points_db.sqlite"

team_mode_enabled = False

def load_team_mode():
    global team_mode_enabled
    # حاول قراءة قيمة وضع الأفرقة من ملف أو قاعدة بيانات
    team_mode_enabled = False   # هذه القيمة مبدئية، غيّرها إذا أضفت حفظ/قراءة من ملف


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

async def safe_edit_or_reply(event, text, **kwargs):
    """دالة للرد أو التعديل بأمان (تعالج خطأ MessageAuthorRequiredError تلقائياً)."""
    try:
        await edit_or_reply(event, text, **kwargs)
    except MessageAuthorRequiredError:
        await event.reply(text, **kwargs)

async def get_user_id(event, args):
    """جلب ID المستخدم حسب الرد أو المنشن أو الإيدي."""
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

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}p|{cmhd}delp)(?:\s+(.+))?$")
async def points_manage(event):
    """إضافة أو خصم نقاط"""
    global TEAM_MODE_STATUS
    if TEAM_MODE_STATUS:
        # إذا كان وضع الفرق مُفعل، استخدم وظيفة إدارة الفرق
        return await team_manage_points(event)
    else:
        # إذا كان وضع الفرق غير مُفعل، استخدم النظام العادي
        return await individual_manage_points(event)

async def individual_manage_points(event):
    """إدارة النقاط في الوضع العادي"""
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

    # استدعاء دالة handle_event دائماً
    return await handle_event(event, args, cmd, points)

async def handle_event(event, args, cmd, points):
    """تنفيذ إضافة أو خصم النقاط"""
    # الحصول على ID المستخدم المستهدف
    uid = await get_user_id(event, args)
    if uid is None:
        return await safe_edit_or_reply(event, "❗️يرجى تحديد المستخدم بالرد أو المنشن أو الإيدي.")

    # محاولة الحصول على معلومات المستخدم
    try:
        user = await event.client.get_entity(uid)
        name = user.first_name + (" " + user.last_name if user.last_name else "")
    except Exception:
        name = str(uid)
    user_id = uid

    # الحصول على عدد النقاط الحالي
    old = get_points(event.chat_id, uid)

    # إذا كان الأمر هو /p يتم إضافة النقاط
    if cmd == "/p":
        new_points = old + points
        set_points(event.chat_id, uid, new_points)
        return await safe_edit_or_reply(
            event,
            f"➕ تم إضافة {points} نقطة.\n👤 المستخدم : [{name}](tg://user?id={user_id})\n🔢 عدد نقاطه : [{new_points}]"
        )
    # إذا كان الأمر هو /delp يتم خصم النقاط
    else:
        new_points = max(old - points, 0)  # التأكد من أن النقاط لا تصبح أقل من صفر
        set_points(event.chat_id, uid, new_points)
        return await safe_edit_or_reply(
            event,
            f"➖ تم خصم {points} نقطة.\n👤 المستخدم : [{name}](tg://user?id={user_id})\n🔢 عدد نقاطه : [{new_points}]")

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}ps|{cmhd}points)(?:\s+(.+))?$")
async def show_points(event):
    """عرض النقاط"""
    global TEAM_MODE_STATUS
    if TEAM_MODE_STATUS:
        # إذا كان وضع الفرق مُفعل، استخدم وظيفة عرض نقاط الفرق
        return await show_team_points(event)
    else:
        # إذا كان وضع الفرق غير مُفعل، استخدم النظام العادي
        return await show_individual_points(event)

async def show_individual_points(event):
    """عرض النقاط الفردية"""
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

@zedub.bot_cmd(pattern=fr"^{cmhd}rstp$")
async def reset_points(event):
    """إعادة جميع النقاط إلى صفر"""
    global TEAM_MODE_STATUS
    if TEAM_MODE_STATUS:
        # إذا كان وضع الفرق مُفعل، استخدم وظيفة إعادة تعيين نقاط الفرق
        return await reset_team_points(event)
    else:
        # إذا كان وضع الفرق غير مُفعل، استخدم النظام العادي
        return await reset_individual_points(event)

async def reset_individual_points(event):
    """إعادة جميع النقاط الفردية إلى صفر"""
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
        
        
        
@bot.on(events.NewMessage(pattern='/tmod'))
async def tmod_handler(event):
    if not is_admin(event.sender_id):
        return
    # أرسل لوحة التحكم
    await send_team_mode_panel(event)

@zedub.bot_cmd(pattern=r"^(?:[./#])?pmod$")
async def deactivate_team_mode(event):
    global TEAM_MODE_STATUS
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق مُعطل بالفعل.")
    TEAM_MODE_STATUS = False
    await event.reply("🔄 تم تعطيل وضع الفرق. عاد البوت إلى وضع الأفراد.")
    
    
@zedub.bot_cmd(pattern=r"^(?:[./#])?setteams (\d+)$")
async def set_teams(event):
    global TEAMS, TEAM_NAMES
    num_teams = int(event.pattern_match.group(1 حتى يتم استخدام /setteams لتحديد عدد الفرق من جديد.")
    
    if num_teams < 2:
        return await event.reply("❌ يجب أن يكون عدد الفرق 2 أو أكثر.")
    
    TEAMS = {f"Team {i+1}": {"members": [], "points": 0} for i in range(num_teams)}
    TEAM_NAMES = []  # قائمة لتخزين أسماء الفرق التي سيتم إدخالها
    TEAM_NAMES_LOCKED = False  # رفع القفل عن تعديل أسماء الفرق
    
    await event.reply(f"✅ تم إنشاء {num_teams} فرق. يرجى إدخال أسماء الفرق باستخدام الرد على هذه الرسالة.")

@zedub.tgbot.on(events.NewMessage(pattern=r"^(?:[./#])?teamname (.+)$"))
async def add_team_name(event):
    global TEAMS, TEAM_NAMES, TEAM_NAMES_LOCKED
    team_name = event.pattern_match.group(1)
    
    # التحقق إذا تم إدخال جميع أسماء الفرق بالفعل
    if len(TEAM_NAMES) >= len(TEAMS):
        TEAM_NAMES_LOCKED = True  # قفل تعديل أسماء الفرق بعد اكتمال الإدخال
        return await event)
    TEAMS[f"Team {team_index}"] = {"name": team_name, "members": [], "points": 0}
    
    if len(TEAM_NAMES) == len(TEAMS):
        TEAM_NAMES_LOCKED = True  # قفل تعديل أسماء الفرق بعد اكتمال الإدخال
        return await event.reply("✅ تم إدخال جميع أسماء الفرق بنجاح.")
    else:
        await event.reply(f"✅ تم إضافة اسم الفريق: {team_name}. يرجى إدخال اسم الفريق التالي.")
    
    
@zedub.bot_cmd(pattern="^/register$")
async def register_teams(event):
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    buttons = [[Button.inline(name, f"join_team|{name}")] for name in TEAMS.keys()]
    await event.reply("📝 اختر الفريق الذي تريد التسجيل فيه:", buttons=buttons)
    
    
@zedub.tgbot.on(events.CallbackQuery(pattern=r"join_team\|(.+)"))
async def join_team(event):
    team_name = event.pattern_match.group(1)
    user_id = event.sender_id
    for team in TEAMS.values():
        if user_id in team["members"]:
            return await event.reply("❌ أنت مسجل بالفعل في أحد الفرق.")
    TEAMS[team_name]["members"].append(user_id)
    await event.reply(f"✅ تم تسجيلك في فريق {team_name}.")
    
   
@zedub.bot_cmd(pattern="^/showt$")
async def show_teams(event):
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    text = "**📊 الفرق وأعضاؤها:**\n"
    for name, data in TEAMS.items():
        text += f"ㅤ• {name}:\n"
        for member in data["members"]:
            text += f"- [{member}](tg://user?id={member})\n"
    await event.reply(text)
    
    
@zedub.bot_cmd(pattern="^/pst$")
async def show_team_points(event):
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    text = "**📊 نقاط الفرق:**\n\n"
    for name, data in TEAMS.items():
        text += f"ㅤ• {name}: {data['points']} نقاط\n"
    await event.reply(text)
    
    
@zedub.bot_cmd(pattern="^/(p|delp)(?:\s+(\d+))?$")
async def manage_points(event):
    global TEAMS
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    cmd = event.pattern_match.group(1)
    points = int(event.pattern_match.group(2) or 1)
    user_id = await get_user_id(event, event.pattern_match.groups())
    if not user_id:
        return await event.reply("❌ يرجى تحديد المستخدم.")
    team_name = next((name for name, data in TEAMS.items() if user_id in data["members"]), None)
    if not team_name:
        return await event.reply("❌ المستخدم غير مسجل في أي فريق.")
    if cmd == "p":
        TEAMS[team_name]["points"] += points
        await event.reply(f"✅ تم إضافة {points} نقاط لفريق {team_name}.")
    else:
        TEAMS[team_name]["points"] = max(0, TEAMS[team_name]["points"] - points)
        await event.reply(f"❌ تم خصم {points} نقاط من فريق {team_name}.")
        
        
async def send_team_mode_panel(event):
    buttons = [
        [Button.text("إغلاق الوضع والعودة لوضع الأفراد")],
        [Button.text("إنشاء الأفرقة")]
    ]
    await event.respond("لوحة تحكم الأفرقة:", buttons=buttons)
    
    
@bot.on(events.CallbackQuery(pattern='إغلاق الوضع والعودة لوضع الأفراد'))
async def close_team_mode(event):
    global team_mode_enabled
    team_mode_enabled = False
    # (قم بحفظ القيمة إذا كنت تعتمد على ملف أو db)
    await event.edit("تم العودة لوضع الأفراد.")