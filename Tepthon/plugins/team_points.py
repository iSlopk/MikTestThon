import asyncio  
import sqlite3  
from telethon import events, Button  
from telethon.errors.rpcerrorlist import MessageAuthorRequiredError  
from telethon.tl.types import ChannelParticipantsAdmins  
from telethon.events import CallbackQuery
from . import zedub  
from ..Config import Config  
from ..core.managers import edit_or_reply  
  
plugin_category = "بوت النقاط"  
cmhd = Config.COMMAND_HAND_LER  
DB_PATH = "points_db.sqlite"  
  
TEAM_MODE = {}  # chat_id → bool  
TEAMS = {}      # chat_id → { 'count': int, 'names': [...], 'members': {team_idx: [user_ids] }, 'changed': set() }  
  
def get_db(): return sqlite3.connect(DB_PATH)  
def create_table():  
    with get_db() as db:  
        db.execute("""  
        CREATE TABLE IF NOT EXISTS points (chat_id INTEGER, user_id INTEGER, points INTEGER,  
            PRIMARY KEY(chat_id, user_id))  
        """)  
create_table()  
  
async def is_user_admin(event):  
    admins = await event.client.get_participants(event.chat_id, filter=ChannelParticipantsAdmins)  
    return any(a.id == event.sender_id for a in admins)  
  
def get_points(chat, user): ...  
def set_points(chat, user, pts): ...  
def get_all_points(chat): ...  
def reset_all_points(chat): ...  
  
async def safe_edit(event, text, **k):  
    try: await edit_or_reply(event, text, **k)  
    except MessageAuthorRequiredError: await event.reply(text, **k)  
  
@zedub.bot_cmd(pattern=fr"^{cmhd}tmod$")  
async def cmd_tmod(event):  
    if not await is_user_admin(event):
        return await safe_edit(event, "❗ للمشرفين فقط.")  

    TEAM_MODE[event.chat_id] = True  
    TEAMS[event.chat_id] = {
        'count': 2,
        'names': [],
        'members': {},
        'changed': set()
    }

    buttons = [  
        [Button.inline("🔙 وضع الأفراد", b"pmod")],  
        [Button.inline("🔧 إنشاء الفرق", b"setup_teams")]  
    ]  

    await event.reply("✅ تم تفعيل وضع الفرق.", buttons=buttons)
    await event.delete()
  
@zedub.bot_cmd(pattern=fr"^{cmhd}pmod$")  
async def cmd_pmod(event):  
    if not await is_user_admin(event): return await safe_edit(event, "❗ للمشرفين فقط.")  
    TEAM_MODE[event.chat_id] = False  
    return await safe_edit(event, "✅ تم الرجوع لوضع الأفراد.")  
  
# التعامل مع أزرار وضع الفرق  
@zedub.zedub.on(CallbackQuery)
async def callback_handler(event):
    chat = event.message.chat_id
    data = event.data.decode()

    if data == "pmod":
        TEAM_MODE[chat] = False
        return await event.edit("✅ تم العودة لوضع الأفراد.", buttons=None)

    if data == "setup_teams":
        kb = [
            [Button.inline(str(i), f"team_count_{i}") for i in range(2, 6)],
            [Button.inline(str(i), f"team_count_{i}") for i in range(6, 11)],
            [Button.inline("✔️ تحديد أسماء الفرق", b"team_names")]
        ]
        return await event.edit("اختر عدد الفرق:", buttons=kb)

    if data.startswith("team_count_"):
        n = int(data.split("_")[-1])
        TEAMS[chat]['count'] = n
        return await event.edit(
            f"✅ اخترت {n} فرق.\nاضغط لتعيين أسماء الفرق.",
            buttons=[[Button.inline("📝 أسماء الفرق", b"team_names")]]
        )

    if data == "team_names":
        return await event.reply("📩 أرسل أسماء الفرق مثل: (الصقور 🦅، الشجعان 👮🏻‍♂️)")

    if data == "start_signup":
        return await event.edit(
            "🔔 التسجيل مفتوح للفرق عبر أمر /tp\nيمكن لكل عضو تغيير فريقه مرة واحدة.",
            buttons=None
        )
        
  
  @zedub.bot_cmd(events.NewMessage)
async def receive_names(ev):
    chat = ev.chat_id

    # تأكد أن الرسالة في مجموعة ووضع الفرق مفعّل
    if not ev.is_group or not TEAM_MODE.get(chat):
        return

    # تأكد أن الأسماء لم تُحدد بعد (أي لا تزال في مرحلة إعداد الفرق)
    if TEAMS.get(chat) and not TEAMS[chat]['names']:
        text = ev.text.strip()

        # تقسيم النص إلى أسماء حسب الفاصلة العربية "،"
        names = [x.strip() for x in text.strip("()").split("،")]

        if len(names) == TEAMS[chat]['count']:
            TEAMS[chat]['names'] = names
            TEAMS[chat]['members'] = {i: [] for i in range(len(names))}
            await ev.reply("✅ تم تحديد الأسماء.", buttons=[[Button.inline("🚀 ابدأ التسجيل", b"start_signup")]])
        else:
            await ev.reply(f"⚠️ عدد الأسماء ({len(names)}) لا يطابق عدد الفرق المحدد ({TEAMS[chat]['count']})، حاول مجددًا.")
  
        # الترقب  
        @zedub.bot_cmd(events.NewMessage)  
        async def receive_names(ev):  
            if ev.is_group and ev.chat_id==chat and TEAM_MODE.get(chat):  
                text=ev.text.strip()  
                names=[x.strip() for x in text.strip("()").split("،")]  
                if len(names)==TEAMS[chat]['count']:  
                    TEAMS[chat]['names']=names  
                    TEAMS[chat]['members']={i:[] for i in range(len(names))}  
                    await ev.reply("✅ تم تحديد الأسماء.", buttons=[[Button.inline("🚀 ابدأ التسجيل", b"start_signup")]])  
                else:  
                    await ev.reply(f"عدد الأسماء != عدد الفرق ({TEAMS[chat]['count']}) حاول مجدداً.")  
                return  
    if data=="start_signup":  
        return await event.edit("🔔 التسجيل مفتوح للفرق بجهاز /tp\nيمكن لكل عضو تغيير فريقه مرة واحدة.", buttons=None)  
  
# أوامر نقاط فرق  
@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tp|{cmhd}tdp|{cmhd}trstp|{cmhd}tps)(?:\s+(.+))?$")  
async def team_points(event):  
    chat=event.chat_id  
    if not TEAM_MODE.get(chat): return  
    cmd=event.text.split()[0].lower().replace(cmhd,"/")  
    args=event.pattern_match.group(1)  
    args=args.split() if args else []  
    uid= await get_user_id(event,args)  
    if not uid: return await safe_edit(event, "❗ حدد مستخدم بالرد/ايدي")  
    # find their team  
    team_idx=None  
    for idx, members in TEAMS[chat]['members'].items():  
        if uid in members:  
            team_idx=idx; break  
    if cmd=="/tp":  
        if team_idx is not None: return await safe_edit(event, "❗ غير مسموح بتغيير الفريق أكثر من مرة.")  
        # عضو جديد  
        idx = uid % TEAMS[chat]['count']  
        TEAMS[chat]['members'].setdefault(idx,[]).append(uid)  
        TEAM_NAME=TEAMS[chat]['names'][idx]  
        return await safe_edit(event, f"✅ انضممت إلى فريق: {TEAM_NAME}")  
    if cmd=="/tdp":
        return await safe_edit(event, "🛠️ لم يتم تفعيل خصم النقاط بعد.")
        # خصم نفس النقاط الفريقية  
    if cmd=="/trstp":  
        TEAMS[chat]['members']={}  
        return await safe_edit(event,"✅ تم تصفير تسجيلات الفرق.")  
    if cmd=="/tps":  
        text="📊 فرق المجموعة:\n"  
        for idx,name in enumerate(TEAMS[chat]['names']):  
            mems=TEAMS[chat]['members'].get(idx,[])  
            ids=", ".join(str(u) for u in mems)  
            text+=f"• {name}: {ids}\n"  
        return await safe_edit(event,text)  
  
# تأكد من حفظ TEAMS وTEAM_MODE عند restart إذا أردت

@zedub.bot_cmd(pattern=fr"^(?:{cmhd}tp|{cmhd}tdp)(?:\s+(.+))?$")
async def manage_team_points(event):
    chat = event.chat_id
    if not TEAM_MODE.get(chat): return

    cmd = event.text.split()[0].lower().replace(cmhd, "/")
    args = event.pattern_match.group(1)
    args = args.split() if args else []
    uid = await get_user_id(event, args)
    if not uid:
        return await safe_edit(event, "❗ حدد مستخدم بالرد/منشن/آيدي")

    # حدد الفريق الذي ينتمي إليه المستخدم
    team_idx = None
    for idx, members in TEAMS[chat]['members'].items():
        if uid in members:
            team_idx = idx
            break

    if team_idx is None:
        return await safe_edit(event, "❗ هذا المستخدم غير مسجل في أي فريق.")

    # احصل على أعضاء الفريق بالكامل
    members = TEAMS[chat]['members'][team_idx]
    delta = 1 if cmd == "/tp" else -1

    for member_id in members:
        current = get_points(chat, member_id)
        new_pts = max(current + delta, 0)
        set_points(chat, member_id, new_pts)

    sign = "➕" if delta > 0 else "➖"
    team_name = TEAMS[chat]['names'][team_idx]
    return await safe_edit(event, f"{sign} تم {'إضافة' if delta > 0 else 'خصم'} نقطة لكل أعضاء فريق: {team_name}")