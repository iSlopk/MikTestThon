import os
import re
import glob
import urllib.request
from collections import defaultdict
import random

import ujson
import yt_dlp
from telethon import Button
from youtubesearchpython import VideosSearch
from yt_dlp.utils import DownloadError, ExtractorError, GeoRestrictedError

from ...Config import Config
from ...core import pool
from ...core.logger import logging
from ..aiohttp_helper import AioHttp
from ..progress import humanbytes
from .functions import sublists

LOGS = logging.getLogger(__name__)


def get_cookies_file():
    folder_path = f"{os.getcwd()}/rcookies"
    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        raise FileNotFoundError("No .txt files found in the specified folder.")
    cookie_txt_file = random.choice(txt_files)
    return cookie_txt_file


BASE_YT_URL = "https://www.youtube.com/watch?v="
YOUTUBE_REGEX = re.compile(
    r"(?:youtube\.com|youtu\.be)/(?:[\w-]+\?v=|embed/|v/|shorts/)?([\w-]{11})"
)
PATH = "./Mikthon/cache/ytsearch.json"

song_dl = "yt-dlp --cookies {get_cookies_file()} --force-ipv4 --write-thumbnail --add-metadata --embed-thumbnail -o './temp/%(title)s.%(ext)s' --extract-audio --audio-format mp3 --audio-quality {QUALITY} {video_link}"

thumb_dl = "yt-dlp --cookies {get_cookies_file()} --force-ipv4 -o './temp/%(title)s.%(ext)s' --write-thumbnail --skip-download {video_link}"
video_dl = "yt-dlp --cookies {get_cookies_file()} --force-ipv4 --write-thumbnail --add-metadata --embed-thumbnail -o './temp/%(title)s.%(ext)s' -f 'best[height<=480]' {video_link}"
name_dl = "yt-dlp --cookies {get_cookies_file()} --force-ipv4 --get-filename -o './temp/%(title)s.%(ext)s' {video_link}"


async def yt_search(rep):
    try:
        rep = urllib.parse.quote(rep)
        html = urllib.request.urlopen(
            f"https://www.youtube.com/results?search_query={zed}"
        )

        user_data = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        video_link = []
        k = 0
        for i in user_data:
            if user_data:
                video_link.append(f"https://www.youtube.com/watch?v={user_data[k]}")
            k += 1
            if k > 3:
                break
        if video_link:
            return video_link[0]
        return "Couldnt fetch results"
    except Exception:
        return "Couldnt fetch results"


async def ytsearch(query, limit):
    result = ""
    videolinks = VideosSearch(query.lower(), limit=limit)
    for v in videolinks.result()["result"]:
        textresult = f"[{v['title']}](https://www.youtube.com/watch?v={v['id']})\n"
        try:
            textresult += f"**- الوصـف : **`{v['descriptionSnippet'][-1]['text']}`\n"
        except Exception:
            textresult += "**- الوصـف : **`None`\n"
        textresult += f"**- المـده : **{v['duration']}  **- المشـاهـدات : **{v['viewCount']['short']}\n"
        result += f"☞ {textresult}\n"
    return result


class YT_Search_X:
    def __init__(self):
        if not os.path.exists(PATH):
            with open(PATH, "w") as f_x:
                ujson.dump({}, f_x)
        with open(PATH) as yt_db:
            self.db = ujson.load(yt_db)

    def store_(self, rnd_id: str, results: dict):
        self.db[rnd_id] = results
        self.save()

    def save(self):
        with open(PATH, "w") as outfile:
            ujson.dump(self.db, outfile, indent=4)


ytsearch_data = YT_Search_X()

"""
async def yt_data(rep):
    params = {"format": "json", "url": rep}
    url = "https://www.youtube.com/oembed"  # https://stackoverflow.com/questions/29069444/returning-the-urls-as-a-list-from-a-youtube-search-query
    query_string = urllib.parse.urlencode(params)
    url = f"{url}?{query_string}"
    with urllib.request.urlopen(url) as response:
        response_text = response.read()
        data = ujson.loads(response_text.decode())
    return data
"""


async def get_ytthumb(videoid: str):
    thumb_quality = [
        "maxresdefault.jpg",  # Best quality
        "hqdefault.jpg",
        "sddefault.jpg",
        "mqdefault.jpg",
        "default.jpg",  # Worst quality
    ]
    thumb_link = "https://i.imgur.com/4LwPLai.png"
    for qualiy in thumb_quality:
        link = f"https://i.ytimg.com/vi/{videoid}/{qualiy}"
        if await AioHttp().get_status(link) == 200:
            thumb_link = link
            break
    return thumb_link


def get_yt_video_id(url: str):
    if match := YOUTUBE_REGEX.search(url):
        return match.group(1)


# Based on https://gist.github.com/AgentOak/34d47c65b1d28829bb17c24c04a0096f
def get_choice_by_id(choice_id, media_type: str):
    if choice_id == "mkv":
        # default format selection
        choice_str = "bestvideo+bestaudio/best"
        disp_str = "best(video+audio)"
    elif choice_id == "mp3":
        choice_str = "320"
        disp_str = "320 Kbps"
    elif choice_id == "mp4":
        # Download best Webm / Mp4 format available or any other best if no mp4
        # available
        choice_str = "bestvideo[ext=webm]+251/bestvideo[ext=mp4]+(258/256/140/bestaudio[ext=m4a])/bestvideo[ext=webm]+(250/249)/best"
        disp_str = "best(video+audio)[webm/mp4]"
    else:
        disp_str = str(choice_id)
        choice_str = (
            f"{disp_str}+(258/256/140/bestaudio[ext=m4a])/best"
            if media_type == "v"
            else disp_str
        )

    return choice_str, disp_str


async def result_formatter(results: list):
    output = {}
    for index, r in enumerate(results, start=1):
        v_deo_id = r.get("id")
        thumb = await get_ytthumb(v_deo_id)
        upld = r.get("channel")
        title = f'<a href={r.get("link")}><b>{r.get("title")}</b></a>\n'
        out = title
        if r.get("descriptionSnippet"):
            out += "<code>{}</code>\n\n".format(
                "".join(x.get("text") for x in r.get("descriptionSnippet"))
            )
        out += f'<b>❯  المـده :</b> {r.get("accessibility").get("duration")}\n'
        views = f'<b>❯  المشـاهـدات :</b> {r.get("viewCount").get("short")}\n'
        out += views
        out += f'<b>❯  تاريـخ الرفـع :</b> {r.get("publishedTime")}\n'
        if upld:
            out += "<b>❯  القنـاة :</b> "
            out += f'<a href={upld.get("link")}>{upld.get("name")}</a>'

        output[index] = dict(
            message=out,
            thumb=thumb,
            video_id=v_deo_id,
            list_view=f'<img src={thumb}><b><a href={r.get("link")}>{index}. {r.get("accessibility").get("title")}</a></b><br>',
        )

    return output


def yt_search_btns(
    data_key: str, page: int, vid: str, total: int, del_back: bool = False
):
    buttons = [
        [
            Button.inline(
                text="رجـوع ⬅️",
                data=f"ytdl_back_{data_key}_{page}",
            ),
            Button.inline(
                text=f"{page} / {total}",
                data=f"ytdl_next_{data_key}_{page}",
            ),
        ],
        [
            Button.inline(
                text="عرض الكل 📜",
                data=f"ytdl_listall_{data_key}_{page}",
            ),
            Button.inline(
                text="⬇️ تحميـل",
                data=f"ytdl_download_{vid}_0",
            ),
        ],
    ]
    if del_back:
        buttons[0].pop(0)
    return buttons


@pool.run_in_thread
def download_button(vid: str, body: bool = False):  # sourcery no-metrics
    # sourcery skip: low-code-quality
    try:
        vid_data = yt_dlp.YoutubeDL({"no-playlist": True, "cookiefile": get_cookies_file()}).extract_info(
            BASE_YT_URL + vid, download=False
        )
    except ExtractorError:
        vid_data = {"formats": []}
    buttons = [
        [
            Button.inline("⭐️ اعلى دقـه - 📹 MKV", data=f"ytdl_download_{vid}_mkv_v"),
            Button.inline(
                "⭐️ اعلى دقـه - 📹 WebM/MP4",
                data=f"ytdl_download_{vid}_mp4_v",
            ),
        ]
    ]
    # ------------------------------------------------ #
    qual_dict = defaultdict(lambda: defaultdict(int))
    qual_list = ["144p", "240p", "360p", "480p", "720p", "1080p", "1440p"]
    audio_dict = {}
    # ------------------------------------------------ #
    for video in vid_data["formats"]:
        if video.get("filesize"):
            fr_note = video.get("format_note")
            fr_id = int(video.get("format_id"))
            fr_size = video.get("filesize")
            if video.get("ext") == "mp4":
                for frmt_ in qual_list:
                    if fr_note in (frmt_, f"{frmt_}60"):
                        qual_dict[frmt_][fr_id] = fr_size
            if video.get("acodec") != "none":
                bitrrate = int(video.get("abr", 0)) if video.get("abr", 0) else 0 # تم اضافتها مع الكوكيز
                if bitrrate != 0:
                    audio_dict[
                        bitrrate
                    ] = f"🎵 {bitrrate}Kbps ({humanbytes(fr_size) or 'N/A'})"

    video_btns = []
    for frmt in qual_list:
        frmt_dict = qual_dict[frmt]
        if len(frmt_dict) != 0:
            frmt_id = sorted(list(frmt_dict))[-1]
            frmt_size = humanbytes(frmt_dict.get(frmt_id)) or "N/A"
            video_btns.append(
                Button.inline(
                    f"📹 {frmt} ({frmt_size})",
                    data=f"ytdl_download_{vid}_{frmt_id}_v",
                )
            )
    buttons += sublists(video_btns, width=2)
    buttons += [
        [Button.inline("⭐️ اعلى دقـه - 🎵 320Kbps - MP3", data=f"ytdl_download_{vid}_mp3_a")]
    ]
    buttons += sublists(
        [
            Button.inline(audio_dict.get(key_), data=f"ytdl_download_{vid}_{key_}_a")
            for key_ in sorted(audio_dict.keys())
        ],
        width=2,
    )
    if body:
        vid_body = f"<a href={vid_data.get('webpage_url')}><b>[{vid_data.get('title')}]</b></a>"
        return vid_body, buttons
    return buttons


@pool.run_in_thread
def _tubeDl(url: str, starttime, uid: str):
    ydl_opts = {
        "addmetadata": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "outtmpl": os.path.join(
            Config.TEMP_DIR, str(starttime), "%(title)s-%(format)s.%(ext)s"
        ),
        #         "logger": LOGS,
        "format": uid,
        "writethumbnail": True,
        "prefer_ffmpeg": True,
        "postprocessors": [
            {"key": "FFmpegMetadata"}
            # ERROR R15: Memory quota vastly exceeded
            # {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
        ],
        "quiet": True,
        "no_warnings": True,
        "cookiefile" : get_cookies_file(),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            x = ydl.download([url])
    except DownloadError as e:
        LOGS.error(e)
    except GeoRestrictedError:
        LOGS.error("هذا الفيديو غير متاح  في بلدك")
    else:
        return x


@pool.run_in_thread
def _mp3Dl(url: str, starttime, uid: str):
    _opts = {
        "outtmpl": os.path.join(Config.TEMP_DIR, str(starttime), "%(title)s.%(ext)s"),
        #         "logger": LOGS,
        "writethumbnail": True,
        "prefer_ffmpeg": True,
        "format": "bestaudio/best",
        "geo_bypass": True,
        "nocheckcertificate": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": uid,
            },
            {"key": "EmbedThumbnail"},  # ERROR: Conversion failed!
            {"key": "FFmpegMetadata"},
        ],
        "quiet": True,
        "no_warnings": True,
        "cookiefile" : get_cookies_file(),
    }
    try:
        with yt_dlp.YoutubeDL(_opts) as ytdl:
            dloader = ytdl.download([url])
    except Exception as y_e:
        LOGS.exception(y_e)
        return y_e
    else:
        return dloader
