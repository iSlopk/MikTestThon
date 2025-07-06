import io
import asyncio
from PIL import Image, ImageDraw, ImageFont
from telethon import Button, events
from telethon.tl.functions.stats import GetBroadcastStatsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from ..core.session import zedub
from ..core.managers import edit_or_reply
from ..Config import Config

cmhd = Config.COMMAND_HAND_LER

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
    except:
        pass
    return user, photo

def build_special_top(user, count, photo, rank):
    colors = {1: (212,175,55), 2: (192,192,192), 3: (205,127,50)}
    img = Image.new("RGB", (600, 300), colors.get(rank, (245,245,245)))
    draw = ImageDraw.Draw(img)
    font_large = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 32)
    font_small = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 24)

    if photo:
        img.paste(photo.resize((200,200)), (20, 50))
    name = user.user.first_name + (f" {user.user.last_name}" if user.user.last_name else "")
    uname = f"@{user.user.username}" if user.user.username else ""
    draw.text((240, 60), f"{rank}. {name}", fill="black", font=font_large)
    draw.text((240, 110), uname, fill="black", font=font_small)
    draw.text((240, 160), f"📨 رسائل: {count}", fill="black", font=font_small)

    return img

def build_rank_image(user, uid, rank_pos, photo):
    width, height = 600, 220
    img = Image.new("RGB", (width, height), (30,30,30))
    draw = ImageDraw.Draw(img)
    font_name = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 28)
    font_info = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 22)
    font_bio  = ImageFont.truetype("Tepthon/plugins/assets/NotoNaskhArabic-Regular.ttf", 20)

    if photo:
        img.paste(photo.resize((160,160)), (20,20))
    else:
        draw.rectangle((20,20,180,180), fill=(60,60,60))

    name = user.user.first_name + (f" {user.user.last_name}" if user.user.last_name else "")
    draw.text((200, 30), name, fill="white", font=font_name)
    uname = f"@{user.user.username}" if user.user.username else "-"
    draw.text((200, 70), uname, fill="lightgray", font=font_info)
    draw.text((200, 105), f"🆔 {uid}", fill="lightgray", font=font_info)
    draw.text((200, 140), f"🏅 الرتبة: {rank_pos}", fill="white", font=font_info)

    bio = getattr(user.full_user, "about", "") or ""
    draw.text((20, 190), bio, fill="gray", font=font_bio)

    return img

@zedub.bot_cmd(pattern=fr"^{cmhd}توب(\d+)$")
async def top_n_handler(event):
    n = int(event.pattern_match.group(1))
    try:
        await event.delete()
    except:
        pass

    top = await fetch_top_senders(event.chat_id, n)
    if not top:
        return await edit_or_reply(event, "❗ لا يوجد بيانات تفاعل متاحة.")

    results = []
    for s in top:
        user_obj, photo = await fetch_user_details(s.user_id)
        results.append((user_obj, s.msg_count, photo))

    if n <= 3:
        for idx, (user_obj, cnt, photo) in enumerate(results, start=1):
            img = build_special_top(user_obj, cnt, photo, idx)
            b = io.BytesIO()
            img.save(b, "JPEG")
            b.seek(0)
            await event.respond(file=b, caption=f"🏆 المرتبة {idx}")
    else:
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
        return await edit_or_reply(event, "❗ لم يتم تحديد المستخدم.")

    top = await fetch_top_senders(event.chat_id, 1000)
    rank_position = next((i for i, s in enumerate(top,1) if s.user_id == uid), 0)
    if rank_position == 0:
        return await edit_or_reply(event, "❗ المستخدم غير موجود ضمن أعلى المتفاعلين.")

    user_obj, photo = await fetch_user_details(uid)
    img = build_rank_image(user_obj, uid, rank_position, photo)
    b = io.BytesIO()
    img.save(b, "JPEG")
    b.seek(0)
    await edit_or_reply(event, file=b)