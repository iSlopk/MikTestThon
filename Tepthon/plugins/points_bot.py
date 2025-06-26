import asyncio
import sqlite3
from telethon import events
from telethon.tl.custom import Button
from telethon.errors.rpcerrorlist import MessageAuthorRequiredError
from . import zedub
from ..Config import Config
from ..core.managers import edit_or_reply

TEAM_MODE_STATUS = False
TEAMS = {}

plugin_category = "بوت النقاط"
cmhd = Config.COMMAND_HAND_LER
DB_PATH = "points_db.sqlite"

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


@zedub.bot_cmd(pattern=fr"^(?:{cmhd}p|{cmhd}delp|{cmhd}rstp|{cmhd}ps)(?:\s+(.+))?$")
async def individual_commands(event):
    """الأوامر الفردية"""
    global TEAM_MODE_STATUS
    if TEAM_MODE_STATUS:  # تحقق من وضع الفرق
        return await safe_edit_or_reply(event, "❌ هذا الأمر متاح فقط في وضع الأفراد.")
    
    # توجيه الأوامر إلى الوظائف المناسبة
    cmd = event.text.split()[0].lower().replace(cmhd, "/")
    if cmd == "/p" or cmd == "/delp":
        return await individual_manage_points(event)
    elif cmd == "/ps":
        return await show_individual_points(event)
    elif cmd == "/rstp":
        return await reset_individual_points(event)

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tp|{cmhd}tdelp|{cmhd}trstp|{cmhd}tps)(?:\s+(.+))?$")
async def team_commands(event):
    """الأوامر الخاصة بالفرق"""
    global TEAM_MODE_STATUS
    if not TEAM_MODE_STATUS:  # تحقق 
    await safe_edit_or_reply(event, "❌ هذا الأمر متاح فقط في وضع الفرق.")
    
    # توجيه الأوامر إلى الوظائف المناسبة
    cmd = event.text.split()[0].lower().replace(cmhd, "/")
    if cmd == "/tp" or cmd == "/tdelp":
        return await team_manage_points(event)
    elif cmd == "/tps":
        return await show_team_points(event)
    elif cmd == "/trstp":
        return await reset_team_points(event)


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

async def reset_team_points(event):
    """إعادة تعيين نقاط جميع الفرق إلى صفر"""
    global TEAM_MODE_STATUS, TEAMS
    
    # التحقق من وضع الفرق
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    
    # التحقق من وجود الفرق
    if not TEAMS:
        return await event.reply("❌ لا توجد فرق لإعادة تعيين نقاطها.")
    
    # إعادة تعيين النقاط لجميع الفرق
    for team in TEAMS.values():
        team["points"] = 0
    
    await event.reply("✅ تم إعادة تعيين نقاط جميع الفرق إلى صفر.")
    
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
        
        
        
@zedub.bot_cmd(pattern="^/tmod$")
async def activate_team_mode(event):
    global TEAM_MODE_STATUS, TEAMS
    if TEAM_MODE_STATUS:
        return await event.reply("✅ وضع الفرق مُفعل بالفعل.")
    TEAM_MODE_STATUS = True
    TEAMS = {}
    await event.reply("🚀 وضع الفرق مُفعل. يرجى إدخال عدد الفرق باستخدام الرد على هذه الرسالة.")

@zedub.bot_cmd(pattern="^/pmod$")
async def deactivate_team_mode(event):
    global TEAM_MODE_STATUS
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق مُعطل بالفعل.")
    TEAM_MODE_STATUS = False
    await event.reply("🔄 تم تعطيل وضع الفرق. عاد البوت إلى وضع الأفراد.")
    
    
@zedub.bot_cmd(pattern="^/setteams (\d+)$")
async def set_teams(event):
    global TEAMS
    num_teams = int(event.pattern_match.group(1))
    if num_teams < 2 or num_teams > 10:
        return await event.reply("❌ يجب أن يكون عدد الفرق بين 2 و 10.")
    TEAMS = {f"Team {i+1}": {"members": [], "points": 0} for i in range(num_teams)}
    await event.reply(f"✅ تم إنشاء {num_teams} فرق. يرجى إدخال أسماء الفرق باستخدام الرد على هذه الرسالة.")
    
    
from telethon.tl.custom import Button  # تأكد من استيراد Button في أعلى الملف

@zedub.bot_cmd(pattern="^/register$")
async def register_teams(event):
    """وظيفة تسجيل الفرق"""
    global TEAM_MODE_STATUS, TEAMS

    # تحقق من وضع الفرق
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل. يرجى تفعيل الوضع باستخدام الأمر /tmod.")

    # تحقق من وجود الفرق
    if not TEAMS:
        return await event.reply("❌ لا توجد فرق مسجلة. يرجى إنشاء الفرق باستخدام الأمر /setteams <عدد الفرق>.")

    # إنشاء الأزرار للفرق
    try:
        buttons = [[Button.inline(name, f"join_team|{name}")] for name in TEAMS.keys()]
        await event.reply("📝 اختر الفريق الذي تريد التسجيل فيه:", buttons=buttons)
    except Exception as e:
        # التعامل مع الأخطاء المحتملة
        await event.reply(f"❌ حدث خطأ أثناء إنشاء الأزرار: {str(e)}")
    
    
@zedub.tgbot.on(events.CallbackQuery(pattern=r"join_team\|(.+)"))
async def join_team(event):
    global TEAMS
    
    # استخراج اسم الفريق وفك ترميزه إذا كان مرمزًا كـ bytes
    team_name = event.pattern_match.group(1).decode('utf-8') if isinstance(event.pattern_match.group(1), bytes) else event.pattern_match.group(1)
    
    user_id = event.sender_id
    MAX_MEMBERS = 10  # تعيين قيمة ثابتة للحد الأقصى لعدد الأعضاء
    
    # التحقق من أن المستخدم غير مسجل بالفعل في فريق آخر
    for team in TEAMS.values():
        if user_id in team["members"]:
            return await event.reply("❌ أنت مسجل بالفعل في أحد الفرق.")
    
    # التحقق من أن الفريق غير موجود
    if team_name not in TEAMS:
        return await event.reply("❌ الفريق غير موجود.")
    
    # التحقق من أن الفريق غير ممتلئ
    if len(TEAMS[team_name]["members"]) >= MAX_MEMBERS:
        return await event.reply("❌ هذا الفريق ممتلئ بالفعل.")
    
    # إضافة المستخدم إلى الفريق
    TEAMS[team_name]["members"].append(user_id)
    await event.reply(f"✅ تم تسجيلك في فريق {team_name}.")
    
   
@zedub.bot_cmd(pattern="^/showt$")
async def show_teams(event):
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    text = "**📊 الفرق وأعضاؤها:**\n"
    for name, data in TEAMS.items():
        text += f"🔹 {name}:\n"
        for member in data["members"]:
            text += f"- [{member}](tg://user?id={member})\n"
    await event.reply(text)
    
    
@zedub.bot_cmd(pattern="^/pst$")
async def show_team_points(event):
    if not TEAM_MODE_STATUS:
        return await event.reply("❌ وضع الفرق غير مُفعل.")
    text = "**📊 نقاط الفرق:**\n"
    for name, data in TEAMS.items():
        text += f"🔹 {name}: {data['points']} نقاط\n"
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
        set_points(event.chat_id, user_id, get_points(event.chat_id, user_id) + points)  # تحديث قاعدة البيانات الفردية
        await event.reply(f"✅ تم إضافة {points} نقاط لفريق {team_name}.")
    else:
        TEAMS[team_name]["points"] = max(0, TEAMS[team_name]["points"] - points)
        set_points(event.chat_id, user_id, max(0, get_points(event.chat_id, user_id) - points))  # تحديث قاعدة البيانات الفردية
        await event.reply(f"❌ تم خصم {points} نقاط من فريق {team_name}.")
async def team_manage_points(event):
    """
    إدارة النقاط في وضع الفرق.
    """
    global TEAMS
    if not event.is_group:
        return await event.reply("❗️ يعمل فقط في المجموعات.")
    
    perms = await event.client.get_permissions(event.chat_id, event.sender_id)
    if not perms.is_admin:
        return await event.reply("❗️ الأمر متاح للمشرفين فقط.")
    
    args = event.pattern_match.group(1)
    args = args.split() if args else []
    cmd = event.text.split()[0].lower().replace(Config.COMMAND_HAND_LER, "/")
    
    points = 1
    
    if len(args) > 1:
        try:
            points = abs(int(args[1]))
        except Exception:
            pass
    
    user_id = await get_user_id(event, args)
    if not user_id:
        return await event.reply("❌ يرجى تحديد المستخدم.")
    
    # تحديد الفريق الذي ينتمي إليه المستخدم
    team_name = next((name for name, data in TEAMS.items() if user_id in data["members"]), None)
    if not team_name:
        return await event.reply("❌ المستخدم غير مسجل في أي فريق.")
    
    if cmd == "/p":
        # إضافة النقاط للفريق
        TEAMS[team_name]["points"] += points
        await event.reply(f"✅ تم إضافة {points} نقاط لفريق {team_name}.")
    else:
        # خصم النقاط من الفريق
        TEAMS[team_name]["points"] = max(0, TEAMS[team_name]["points"] - points)
        await event.reply(f"❌ تم خصم {points} نقاط من فريق {team_name}.")
        
@zedub.bot_cmd(pattern=r"^(.+)$")
async def update_team_names(event):
    global TEAMS
    if event.is_reply and event.reply_to_msg_id:
        names = event.pattern_match.group(1).split(",")
        names = [name.strip() for name in names]
        
        # تحديث أسماء الفرق
        old_keys = list(TEAMS.keys())
        for i, name in enumerate(names):
            TEAMS[name] = TEAMS.pop(old_keys[i])
        
        await event.reply("✅ تم تحديث أسماء الفرق بنجاح.")