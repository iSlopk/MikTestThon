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
    font = ImageFont.truetype("arial.ttf", 24)
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
    img = Image.new("RGB", (500, 200), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 24)
    if photo:
        img.paste(photo, (20, 20))
    name = user.user.first_name + (f" {user.user.last_name}" if user.user.last_name else "")
    uname = user.user.username or ""
    draw.text((160, 30), name, fill="black", font=font)
    draw.text((160, 70), f"@{uname}", fill="gray", font=font)
    draw.text((160, 110), f"🆔 {uid}", fill="gray", font=font)
    draw.text((160, 150), f"📨 الرسائل: {count}", fill="black", font=font)
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
        img = build_top_image(results)
        b = io.BytesIO(); img.save(b, "PNG"); b.seek(0)
        await event.reply(file=b, caption=f"🏆 أفضل {n}")
    else:
        text = f"🏆 أفضل {n} حسب عدد الرسائل:\n\n"
        for idx, (user_obj, cnt, _) in enumerate(results, 1):
            name = user_obj.user.first_name + (f" {user_obj.user.last_name}" if user_obj.user.last_name else "")
            uname = f"@{user_obj.user.username}" if user_obj.user.username else ""
            text += f"{idx}. {name} {uname} — {cnt} رسائل\n"
        await edit_or_reply(event, text)

@bot.on(events.NewMessage(pattern=fr"^{cmhd}تصنيف(?:\s+(.+))?$"))
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
    top = await fetch_top_senders(event.chat_id, 1000)
    count = next((s.msg_count for s in top if s.user_id == uid), 0)
    user_obj, photo = await fetch_user_details(uid)
    img = build_rank_image(user_obj, uid, count, photo)
    b = io.BytesIO(); img.save(b, "PNG"); b.seek(0)
    await edit_or_reply(event, file=b)