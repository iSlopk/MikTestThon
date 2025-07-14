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