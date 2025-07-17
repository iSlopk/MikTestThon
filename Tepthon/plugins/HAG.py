# Plugin: hroof game
# Author: Mik
# Description: لعبة حروف تفاعلية بين فريقين بلونين وخلية سداسية

import random
import math
import io
from PIL import Image, ImageDraw, ImageFont
from telethon import events, Button, types
from . import zedub
from ..core.logger import logging
from userbot import Config

logger = logging.getLogger(__name__)

plugin_category = "ألعاب"
cmhd = Config.COMMAND_HAND_LER

ACTIVE_GAMES = {}

AVAILABLE_COLORS = ["🔴", "🔵", "🟠", "🟡", "🟢", "🟣"]
ARABIC_LETTERS = list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")


def draw_board_image(board, team_colors, captured_cells=None):
    captured_cells = captured_cells or {}
    width, height = 600, 500
    cell_size = 60
    hex_height = cell_size
    hex_width = cell_size * 1.15
    font = ImageFont.truetype("Tepthon/assets/NotoNaskhArabic-Regular.ttf", 28)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    center_x, center_y = width // 2, 60
    offset_x, offset_y = int(hex_width * 0.9), int(hex_height * 0.75)

    for row_idx, row in enumerate(board):
        for col_idx, letter in enumerate(row):
            if not letter:
                continue
            x = center_x + (col_idx - len(row) // 2) * offset_x
            y = center_y + row_idx * offset_y

            team = captured_cells.get(letter)
            color_hex = "lightgrey"
            if team:
                color_emoji = team_colors[team]
                color_map = {
                    "🔴": "red", "🔵": "blue", "🟠": "orange",
                    "🟡": "yellow", "🟢": "green", "🟣": "purple"
                }
                color_hex = color_map.get(color_emoji, "lightgrey")

            draw_hexagon(draw, x, y, cell_size, fill=color_hex)
            w, h = draw.textsize(letter, font=font)
            draw.text((x - w//2, y - h//2), letter, fill="black", font=font)

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr


def draw_hexagon(draw, x, y, size, fill="grey"):
    angle = 60
    points = []
    for i in range(6):
        angle_rad = (angle * i + 30) * math.pi / 180
        px = x + size * 0.95 * math.cos(angle_rad)
        py = y + size * 0.95 * math.sin(angle_rad)
        points.append((px, py))
    draw.polygon(points, fill=fill, outline="black")


def check_win_condition(game):
    board = game["board"]
    captures = game["captured_cells"]
    team_data = game["team_data"]

    for team in team_data:
        if has_path(team, board, captures, direction="horizontal"):
            game["winner"] = team
            return True
        if has_path(team, board, captures, direction="vertical"):
            game["winner"] = team
            return True
    return False


def has_path(team, board, captures, direction):
    rows = len(board)
    cols = max(len(row) for row in board)
    visited = set()

    def dfs(r, c):
        if (r, c) in visited:
            return False
        visited.add((r, c))
        if direction == "horizontal" and c == cols - 1:
            return True
        if direction == "vertical" and r == rows - 1:
            return True

        neighbors = get_neighbors(board, r, c)
        for nr, nc in neighbors:
            if not (0 <= nr < rows and 0 <= nc < len(board[nr])):
                continue
            letter = board[nr][nc]
            if letter and captures.get(letter) == team:
                if dfs(nr, nc):
                    return True
        return False

    for r in range(rows):
        for c in range(len(board[r])):
            letter = board[r][c]
            if not letter or captures.get(letter) != team:
                continue
            if (direction == "horizontal" and c == 0) or (direction == "vertical" and r == 0):
                if dfs(r, c):
                    return True
    return False


def get_neighbors(board, r, c):
    return [
        (r - 1, c), (r + 1, c),
        (r, c - 1), (r, c + 1),
        (r - 1, c + 1), (r + 1, c - 1)
    ]


async def announce_winner(client, chat_id, game):
    winner = game["winner"]
    members = game["team_data"][winner]["members"]
    users_txt = "\n".join([f"- [{user.first_name}](tg://user?id={user.id})" for user in members]) if members else "لا يوجد أعضاء."

    await client.send_message(
        chat_id,
        f"🏆 الفريق الفائز هو: {game['team_data'][winner]['color']} **{winner}**!\n\n🎉 الأعضاء:\n{users_txt}"
    )


@zedub.tgbot.on(events.NewMessage(pattern=fr"^{cmhd}hroof (on|off)$"))
async def toggle_hroof(event):
    chat_id = event.chat_id
    arg = event.pattern_match.group(1)
    if not event.is_group:
        return await event.reply("❌ يجب استخدام هذا الأمر داخل مجموعة.")
    if not (await event.client.get_permissions(chat_id, event.sender_id)).is_admin:
        return await event.reply("❌ فقط المشرفين يمكنهم استخدام هذا الأمر.")

    if arg == "on":
        ACTIVE_GAMES[chat_id] = {"status": "waiting", "team_data": {}, "captured_cells": {}}
        await event.reply("✅ تم تفعيل لعبة الحروف في هذه المجموعة.")
    else:
        ACTIVE_GAMES.pop(chat_id, None)
        await event.reply("🛑 تم إيقاف لعبة الحروف في هذه المجموعة.")


# ملاحظة: باقي الأوامر مثل /hstart و /showt و /hlist لم تُدرج هنا لضيق الرسالة، لكن جاهزة للإكمال.

@zedub.tgbot.on(events.NewMessage(pattern=fr"^{cmhd}hroof$"))
async def hroof_start_setup(event):
    chat_id = event.chat_id
    if chat_id not in ACTIVE_GAMES or ACTIVE_GAMES[chat_id]["status"] != "waiting":
        return await event.reply("❌ اللعبة غير مفعلة.\nقم بتفعيلها باستخدام `/hroof on`.")
        
    COMMAND_HAND_LER = "/"
    game = ACTIVE_GAMES[chat_id]
    game["team_data"] = {}

    buttons = [[Button.inline(color, data=f"hroof_color_{color}") for color in AVAILABLE_COLORS[i:i+3]] for i in range(0, 6, 3)]
    buttons.append([Button.inline("📝 تسمية الفريقين", data="hroof_name_teams")])

    await event.reply("🎮 اختر لونين للفريقين:", buttons=buttons)


@zedub.tgbot.on(events.CallbackQuery(pattern=r"hroof_color_(.+)"))
async def color_selection_handler(event):
    chat_id = event.chat_id
    color = event.pattern_match.group(1)
    game = ACTIVE_GAMES.get(chat_id)

    if not game or game["status"] != "waiting":
        return await event.answer("❌ اللعبة غير مفعلة", alert=True)

    selected = [data["color"] for data in game["team_data"].values()]
    if color in selected:
        return await event.answer("❗️تم اختيار هذا اللون مسبقاً", alert=True)

    user = await event.get_sender()
    team_key = f"team{len(game['team_data'])+1}"
    game["team_data"][team_key] = {
        "color": color,
        "name": f"فريق {len(game['team_data'])+1}",
        "members": [user]
    }

    await event.answer(f"✅ تم اختيار اللون {color}")
    if len(game["team_data"]) == 2:
        await event.edit("🎯 تم اختيار لونين. الآن اضغط على زر **تسمية الفريقين** لتسمية الفرق.")


@zedub.tgbot.on(events.CallbackQuery(pattern=r"hroof_name_teams"))
async def name_teams_handler(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)

    if not game or len(game["team_data"]) != 2:
        return await event.answer("❌ يجب اختيار لونين أولاً", alert=True)

    await event.edit("📝 أرسل أسماء الفريقين كل اسم في سطر (اسم في الأعلى واسم في السطر الثاني).")


@zedub.tgbot.on(events.NewMessage(incoming=True))
async def name_receive(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game or game.get("status") != "waiting":
        return

    if len(game["team_data"]) != 2 or "name_updated" in game:
        return

    text = event.raw_text.strip()
    lines = text.splitlines()
    if len(lines) != 2:
        return await event.reply("❗️يرجى إرسال اسمين فقط في سطرين.")

    team_keys = list(game["team_data"].keys())
    game["team_data"][team_keys[0]]["name"] = lines[0]
    game["team_data"][team_keys[1]]["name"] = lines[1]
    game["name_updated"] = True

    await event.reply(
        f"✅ تم تسمية الفرق:\n\n"
        f"{game['team_data'][team_keys[0]]['color']} {lines[0]}\n"
        f"{game['team_data'][team_keys[1]]['color']} {lines[1]}\n\n"
        f"اضغط على الزر أدناه لتشكيل الخلية.",
        buttons=[[Button.inline("🧩 تشكيل الخلية", data="hroof_generate")]]
    )


@zedub.tgbot.on(events.CallbackQuery(pattern=r"hroof_generate"))
async def generate_hex_board(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)

    if not game or game.get("status") != "waiting":
        return await event.answer("❌ لا يمكن تشكيل الخلية الآن", alert=True)

    board = []
    letter_pool = random.sample(ARABIC_LETTERS * 2, 19)
    layout = [3, 4, 5, 4, 3]

    idx = 0
    for row_len in layout:
        row = []
        for _ in range(row_len):
            row.append(letter_pool[idx])
            idx += 1
        board.append(row)

    game["board"] = board
    game["status"] = "ready"

    img = draw_board_image(board, {k: v["color"] for k, v in game["team_data"].items()})
    caption = generate_caption(game)

    await event.edit("📡 تم تشكيل الخلية:")
    await event.client.send_file(chat_id, img, caption=caption)

    await event.respond("🔽 اختر الحرف الذي تم التقاطه", buttons=[
        [Button.inline(letter, data=f"hroof_pick_{letter}") for letter in row] for row in board
    ])


def generate_caption(game):
    txt = ""
    for k, team in game["team_data"].items():
        claimed = [l for l, owner in game["captured_cells"].items() if owner == k]
        txt += f"{team['color']} **{team['name']}** : {' '.join(claimed) if claimed else '(لا شيء)'}\n"
    return txt


@zedub.tgbot.on(events.CallbackQuery(pattern=r"hroof_pick_(.+)"))
async def pick_letter(event):
    chat_id = event.chat_id
    letter = event.pattern_match.group(1)
    game = ACTIVE_GAMES.get(chat_id)

    if not game or game["status"] != "ready":
        return await event.answer("❌ لا يمكن التقاط الحروف الآن", alert=True)

    if letter in game["captured_cells"]:
        return await event.answer("❗️هذا الحرف تم التقاطه مسبقاً", alert=True)

    team_buttons = [
        Button.inline(team["color"], data=f"hroof_capture_{letter}_{key}")
        for key, team in game["team_data"].items()
    ]
    await event.respond(f"🎯 اختر الفريق الذي التقط الحرف `{letter}`", buttons=[team_buttons])


@zedub.tgbot.on(events.CallbackQuery(pattern=r"hroof_capture_(.+)_(.+)"))
async def capture_letter(event):
    letter, team_key = event.pattern_match.group(1), event.pattern_match.group(2)
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)

    if not game or team_key not in game["team_data"]:
        return await event.answer("❌ خطأ في الفريق أو اللعبة", alert=True)

    game["captured_cells"][letter] = team_key

    img = draw_board_image(game["board"], {k: v["color"] for k, v in game["team_data"].items()}, game["captured_cells"])
    caption = generate_caption(game)

    await event.client.send_file(chat_id, img, caption=caption)

    if check_win_condition(game):
        await announce_winner(event.client, chat_id, game)
        game["status"] = "finished"


@zedub.tgbot.on(events.NewMessage(pattern=fr"^{cmhd}hstart$"))
async def start_game_command(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game or game["status"] != "ready":
        return await event.reply("❌ لا يمكن بدء اللعبة الآن.")
    game["status"] = "playing"
    await event.reply("🚀 تم بدء اللعبة بنجاح!")


@zedub.tgbot.on(events.NewMessage(pattern=fr"^{cmhd}showt$"))
async def show_teams(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game:
        return await event.reply("❌ لا توجد لعبة مفعلة.")
    msg = ""
    for k, team in game["team_data"].items():
        members = team["members"]
        users_txt = "\n".join([f"- [{u.first_name}](tg://user?id={u.id})" for u in members]) if members else "لا أحد"
        msg += f"{team['color']} **{team['name']}**:\n{users_txt}\n\n"
    await event.reply(msg)


@zedub.tgbot.on(events.NewMessage(pattern=fr"^{cmhd}hlist$"))
async def show_board_status(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game or "board" not in game:
        return await event.reply("❌ لا توجد خلية حالياً.")
    img = draw_board_image(game["board"], {k: v["color"] for k, v in game["team_data"].items()}, game["captured_cells"])
    caption = generate_caption(game)
    await event.reply(file=img, message=caption)