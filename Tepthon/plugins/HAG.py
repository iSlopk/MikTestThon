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