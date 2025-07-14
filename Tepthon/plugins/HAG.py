# Plugin: hroof game
# Author: Mik
# Description: لعبة حروف تفاعلية بين فريقين بلونين وخلية سداسية

import random
import asyncio
from telethon import events, Button
from . import zedub
from ..core.logger import logging

logger = logging.getLogger(__name__)

plugin_category = "ألعاب"
cmhd = Config.COMMAND_HAND_LER

ACTIVE_GAMES = {}

AVAILABLE_COLORS = ["🔴", "🔵", "🟠", "🟡", "🟢", "🟣"]
ARABIC_LETTERS = list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")

def generate_board():
    letters = random.sample(ARABIC_LETTERS, 19)
    return letters

def render_board(board, captures, team_colors):
    result = "**🎮 خلية الحروف:**\n\n"
    layout = [
        [0, 1, 2],
        [3, 4, 5, 6],
        [7, 8, 9, 10, 11],
        [12, 13, 14, 15],
        [16, 17, 18]
    ]
    for row in layout:
        line = " " * (6 - len(row))
        for i in row:
            color = ""
            for team, letters in captures.items():
                if board[i] in letters:
                    color = team_colors[team]
            line += f"[{color}{board[i]}] "
        result += line + "\n"
    return result

def get_team_display(team_data, captures, board):
    result = ""
    for team, users in team_data.items():
        team_name = team
        color = users["color"]
        claimed_letters = captures.get(team, [])
        captured = "، ".join(claimed_letters) if claimed_letters else "لا شيء"
        result += f"{color} **{team_name}** : ({captured})\n"
    return result

@zedub.bot_cmd(pattern=fr"^{cmhd}hroof(?: (on|off))?$")
async def toggle_hroof(event):
    chat_id = event.chat_id
    arg = event.pattern_match.group(1)
    if not arg:
        await event.reply("❗ يرجى تحديد on أو off.\nمثال:\n`/hroof on`")
        return

    if arg == "on":
        if chat_id in ACTIVE_GAMES:
            await event.reply("⚠️ اللعبة مفعلة مسبقًا!")
            return
        ACTIVE_GAMES[chat_id] = {
            "state": "choose_colors",
            "team_colors": {},
            "team_data": {},
            "board": [],
            "captures": {},
            "players": {},
            "cell_msg_id": None
        }
        buttons = [[Button.inline(c, data=f"hc_color|{c}") for c in AVAILABLE_COLORS[:3]],
                   [Button.inline(c, data=f"hc_color|{c}") for c in AVAILABLE_COLORS[3:]],
                   [Button.inline("📝 تسمية الفريقين", data="hc_name_teams")]]
        await event.reply("🎯 تم تفعيل اللعبة! اختر لونين للفريقين:", buttons=buttons)
    else:
        if chat_id in ACTIVE_GAMES:
            del ACTIVE_GAMES[chat_id]
            await event.reply("🛑 تم إيقاف اللعبة.")
        else:
            await event.reply("❗ اللعبة غير مفعلة أساسًا.")
            

@zedub.tgbot.on(events.CallbackQuery(pattern=r"hc_color\|(.+)"))
async def handle_color_selection(event):
    chat_id = event.chat_id
    color = event.pattern_match.group(1)
    game = ACTIVE_GAMES.get(chat_id)
    if not game or game["state"] != "choose_colors":
        return await event.answer("❌ لا يمكنك تحديد الألوان الآن.", alert=True)

    if color in game["team_colors"].values():
        return await event.answer("❗ اللون مستخدم مسبقًا", alert=True)

    if len(game["team_colors"]) >= 2:
        return await event.answer("❗ تم اختيار لونين بالفعل.", alert=True)

    team_num = len(game["team_colors"]) + 1
    game["team_colors"][f"team{team_num}"] = color
    await event.answer(f"✅ تم اختيار اللون {color}")

    if len(game["team_colors"]) == 2:
        await event.edit("🔢 تم اختيار اللونين بنجاح!\nاضغط على الزر أدناه لتسمية الفريقين:",
                         buttons=[[Button.inline("📝 تسمية الفريقين", data="hc_name_teams")]])

@zedub.tgbot.on(events.CallbackQuery(pattern=r"hc_name_teams"))
async def ask_team_names(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game:
        return await event.answer("❌ اللعبة غير مفعلة.", alert=True)
    game["state"] = "waiting_team_names"
    await event.respond("📝 أرسل أسماء الفريقين بهذا الشكل:\n\n`TeamA - TeamB`")

@zedub.tgbot.on(events.NewMessage(pattern=r"^(.+?)\s*-\s*(.+)$"))
async def receive_team_names(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game or game["state"] != "waiting_team_names":
        return

    name1, name2 = event.pattern_match.group(1).strip(), event.pattern_match.group(2).strip()
    colors = list(game["team_colors"].values())
    game["team_data"] = {
        name1: {"color": colors[0], "members": []},
        name2: {"color": colors[1], "members": []}
    }
    game["captures"] = {name1: [], name2: []}
    game["state"] = "ready"

    await event.reply(
        f"✅ تم تعيين أسماء الفرق:\n{colors[0]} **{name1}**\n{colors[1]} **{name2}**",
        buttons=[[Button.inline("🔲 تشكيل الخلية", data="hc_make_board")]]
    )
    
def generate_hex_board():
    letters = random.sample(ARABIC_LETTERS, 19)
    board = [
        [None, None, letters[0], letters[1], letters[2]],
        [None, letters[3], letters[4], letters[5], letters[6]],
        [letters[7], letters[8], letters[9], letters[10], letters[11]],
        [None, letters[12], letters[13], letters[14], letters[15]],
        [None, None, letters[16], letters[17], letters[18]]
    ]
    return board

@zedub.tgbot.on(events.CallbackQuery(pattern=r"hc_make_board"))
async def build_board_handler(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game or game["state"] != "ready":
        return await event.answer("❗ لا يمكن تشكيل الخلية الآن.", alert=True)

    game["board"] = generate_hex_board()
    game["state"] = "board_built"

    image_bytes = draw_board_image(game["board"], game["team_colors"])
    file = types.InputMediaUploadedPhoto(await event.client.upload_file(image_bytes))

    team_text = get_team_display(game["team_data"], game["captures"], game["board"])
    msg = await event.client.send_file(
        chat_id,
        file=file,
        caption=f"📍 **خلية اللعبة:**\n\n{team_text}",
        buttons=generate_letter_buttons(game["board"]),
    )

    game["cell_msg_id"] = msg.id
    
def generate_letter_buttons(board):
    letters_flat = [cell for row in board for cell in row if cell]
    buttons = []
    row = []
    for i, letter in enumerate(letters_flat):
        row.append(Button.inline(letter, data=f"hc_pick_letter|{letter}"))
        if (i + 1) % 6 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons
    
@zedub.tgbot.on(events.CallbackQuery(pattern=r"hc_pick_letter\|(.+)"))
async def pick_letter_handler(event):
    chat_id = event.chat_id
    game = ACTIVE_GAMES.get(chat_id)
    if not game or game["state"] != "board_built":
        return await event.answer("❗ اللعبة غير جاهزة بعد.", alert=True)

    letter = event.pattern_match.group(1)
    if letter in game["captured_cells"]:
        return await event.answer("❗ هذا الحرف تم التقاطه بالفعل.", alert=True)

    # حفظ الحرف الذي سيتم تحديد فريق له الآن
    game["pending_letter"] = letter

    # أزرار الفرق حسب الألوان
    buttons = []
    for team, data in game["team_data"].items():
        color = data["color"]
        buttons.append([Button.inline(f"{color} {team}", data=f"hc_capture_letter|{letter}|{team}")])

    await event.answer()
    await event.respond(f"❓ من الفريق الذي التقط الحرف **{letter}**؟", buttons=buttons)
    
    