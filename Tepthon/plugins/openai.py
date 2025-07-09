from telethon import events
from .. import zedub
from ..sql_helper.globals import gvarstatus, addgvar, delgvar
from telethon.tl.functions.channels import GetParticipantRequest
import openai

# استخدم API مفتوح أو مجاني مؤقتاً (استبدله بمفتاحك إن كنت تستخدم GPT فعلياً)
openai.api_key = "your-openai-api-key"

async def is_admin(chat, user, client):
    try:
        participant = await client(GetParticipantRequest(channel=chat, user_id=user))
        return participant.participant.admin_rights or participant.participant.rank
    except:
        return False

@zedub.bot_cmd(pattern="^/ai (on|off)$")
async def toggle_ai(event):
    chat_id = str(event.chat_id)
    sender = event.sender_id

    if not await is_admin(event.chat_id, sender, event.client):
        return await event.reply("❌ الأمر مخصص للمشرفين فقط.")

    action = event.pattern_match.group(1)
    if action == "on":
        addgvar(f"ai_status_{chat_id}", "on")
        await event.reply("✅ تم تفعيل المساعد الذكي (عمر).")
    else:
        delgvar(f"ai_status_{chat_id}")
        await event.reply("🛑 تم إيقاف المساعد الذكي (عمر).")

@zedub.on(events.NewMessage(pattern=None, func=lambda e: e.is_group))
async def ai_listener(event):
    chat_id = str(event.chat_id)
    status = gvarstatus(f"ai_status_{chat_id}")
    if not status or "on" not in status:
        return

    if "عمر" not in event.raw_text:
        return

    sender = await event.get_sender()
    prompt = event.raw_text.replace("عمر", "").strip()
    if not prompt:
        return

    await event.reply("⌛ جاري التفكير...")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # أو gpt-4 لو متاح
            messages=[
                {"role": "system", "content": "أنت مساعد اسمه عمر. قل: 'أنا عمر، نسخة الذكاء الاصطناعي' عند البداية."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response['choices'][0]['message']['content']
        await event.reply(f"👤 {sender.first_name}:\n\n{answer}")
    except Exception as e:
        await event.reply("❌ حدث خطأ أثناء توليد الرد.")