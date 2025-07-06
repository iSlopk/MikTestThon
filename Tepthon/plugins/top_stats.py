import io
import asyncio
from PIL import Image, ImageDraw, ImageFont
from telethon import events, Button, types, utils
from telethon.tl.functions.stats import GetBroadcastStatsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..Config import Config

cmhd = Config.COMMAND_HAND_LER
bot = zedub.tgbot

async def fetch_top_senders(chat_id, limit):
    stats = await zedub(GetBroadcastStatsRequest(channel=chat_id))
    return stats.top_senders[:limit]

async def fetch_user_details(uid):
    user = await zedub(GetFullUserRequest(uid))
    photo = None
    try:
        photos = await zedub(GetUserPhotosRequest(uid, limit=1))
        if photos.photos:
            raw = await zedub.download_media(photos.photos[0], bytes)
            photo = Image.open(io.BytesIO(raw)).resize((128,128))
    except Exception:
        pass
    return user, photo

def build_top_image(results):
    rows = len(results)
    height = 200 * rows
    img = Image.new("RGB", (500, height), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 24)
    for idx, (user, count, photo) in enumerate(results):
        y0 = idx * 200 + 10
        if photo:
            img.paste(photo, (20, y0))
        name = user.user.first_name + (f" {user.user.last_name}" if user.user.last_name else "")
        uname = user.user.username or "‏"
        draw.text((160, y0+10), f"{idx+1}. {name}  @{uname}", fill="black", font=font)
        draw.text((160, y0+50), f"📨 الرسائل: {count}", fill="gray", font=font)
    return img

def build_rank_image(user, uid, count, photo):
    # أبعاد الصورة: مثلاً عرض 600 بكسل وارتفاع 200
    width, height = 600, 200
    img = Image.new("RGB", (width, height), (30, 30, 30))  # خلفية داكنة
    draw = ImageDraw.Draw(img)

    # خطوط النص
    font_name = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 28)
    font_info = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 22)
    font_bio = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 20)

    # فارغة إذا ما فيه صورة شخصية
    if photo:
        photo = photo.resize((160, 160))
        img.paste(photo, (20, 20))
    else:
        draw.rectangle((20,20,180,180), fill=(60,60,60))

    # الاسم بجانب الصورة
    name = user.user.first_name + (f" {user.user.last_name}" if user.user.last_name else "")
    draw.text((200, 30), name, fill="white", font=font_name)

    # على الجانب الأيسر: معرف، ايدي، رانك
    uname = f"@{user.user.username}" if user.user.username else "-"
    draw.text((200, 70), uname, fill="lightgray", font=font_info)
    draw.text((200, 100), f"🆔 {uid}", fill="lightgray", font=font_info)
    # هنا الرانك في التوب مثلاً تحط count كرانك
    draw.text((200, 130), f"🏅 الرتبة: {count}", fill="white", font=font_info)

    # البايو في الوسط-اليمين
    bio = user.full_user.about or ""
    draw.text((20, 180), bio, fill="gray", font=font_bio)

    return img

def build_special_top(user, count, photo, rank):
    """بطاقات مخصصة للمراتب 1–3"""
    colors = {
        1: (212,175,55),
        2: (192,192,192),
        3: (205,127,50),
    }
    img = Image.new("RGB", (600, 300), colors[rank])
    draw = ImageDraw.Draw(img)
    font_large = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 32)
    font_small = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 24)

    # الصورة
    if photo:
        img.paste(photo.resize((200,200)), (20, 50))

    # النصوص
    name = user.user.first_name + (f" {user.user.last_name}" if user.user.last_name else "")
    uname = f"@{user.user.username}" if user.user.username else ""
    draw.text((240, 60), f"{rank}. {name}", fill="black", font=font_large)
    draw.text((240, 110), uname, fill="black", font=font_small)
    draw.text((240, 160), f"📨 رسائل: {count}", fill="black", font=font_small)

    return img


@bot.on(events.NewMessage(pattern=fr"^{cmhd}توب(\d+)$"))
async def top_n_handler(event):
    n = int(event.pattern_match.group(1))
    await event.delete()
    top = await fetch_top_senders(event.chat_id, n)
    results = []
    for s in top:
        user_obj, photo = await fetch_user_details(s.user_id)
        results.append((user_obj, s.msg_count, photo))

    if n <= 3:
        # إرسال بطاقة مخصصة لكل من توب 1، 2، 3
        for idx, (user_obj, cnt, photo) in enumerate(results, start=1):
            img = build_special_top(user_obj, cnt, photo, idx)
            b = io.BytesIO(); img.save(b, "PNG"); b.seek(0)
            await event.respond(file=b, caption=f"🏆 المرتبة {idx}")
    else:
        # إرسال قائمة نصية عادية
        text = f"🏆 أفضل {n} حسب عدد الرسائل:\n\n"
        for idx, (user_obj, cnt, _) in enumerate(results, 1):
            name = user_obj.user.first_name + (f" {user_obj.user.last_name}" if user_obj.user.last_name else "")
            uname = f"@{user_obj.user.username}" if user_obj.user.username else ""
            text += f"{idx}. {name} {uname} — {cnt} رسائل\n"
        await edit_or_reply(event, text)

@zedub.bot_cmd(pattern=fr"^{cmhd}تصنيف(?:\s+(.+))?$")
async def rank_handler(event):
    args = event.pattern_match.group(1)
    uid = None

    if args:
        if args.strip().isdigit():
            uid = int(args)
        else:
            ent = await zedub.get_entity(args.strip())
            uid = ent.id
    elif event.is_reply:
        uid = (await event.get_reply_message()).sender_id

    if not uid:
        return await edit_or_reply(event, "❗ لم يتم تحديد مستخدم.")

    # جلب إحصائيات التفاعل للعثور على ترتيب المستخدم
    top = await fetch_top_senders(event.chat_id, 1000)
    rank_position = 0
    for i, sender in enumerate(top, 1):
        if sender.user_id == uid:
            rank_position = i
            break

    # جلب بيانات المستخدم وصورته الشخصية
    user_obj, photo = await fetch_user_details(uid)

    # إنشاء الصورة وتصميم البطاقة
    img = build_rank_image(user_obj, uid, rank_position, photo)
    b = io.BytesIO()
    img.save(b, "PNG")
    b.seek(0)

    await edit_or_reply(event, file=b)