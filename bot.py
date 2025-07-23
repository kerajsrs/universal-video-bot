import os
import yt_dlp
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH")

# Allowed platforms
SUPPORTED_DOMAINS = ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "facebook.com", "fb.watch", "x.com", "twitter.com"]

app = Client("universal_video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Start Command ---
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "✨ Just send a valid video link and let the magic happen ✨\n\n"
        "Need help or want to request new features? Contact the creator.",
    )

# --- Main Handler ---
@app.on_message(filters.text & ~filters.command(["start"]))
async def downloader(client, message: Message):
    url = message.text.strip()
    logging.info(f"Received URL: {url}")

    if not any(domain in url for domain in SUPPORTED_DOMAINS):
        await message.reply("❌ Unsupported or invalid URL. Try a YouTube, Instagram, TikTok, Facebook or Twitter link.")
        return

    if "youtube.com" in url or "youtu.be" in url:
        buttons = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🎥 Video (MP4)", callback_data=f"yt_video|{url}"),
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"yt_audio|{url}")
            ]]
        )
        await message.reply("Please choose format:", reply_markup=buttons)
    else:
        await process_and_send(client, message, url, audio_only=False)

# --- Button Callback Handler ---
@app.on_callback_query()
async def button_handler(client, callback_query):
    await callback_query.answer()
    data = callback_query.data
    action, url = data.split("|", 1)

    audio_only = action == "yt_audio"
    await process_and_send(client, callback_query.message, url, audio_only)

# --- Core Function ---
async def process_and_send(client, message: Message, url: str, audio_only: bool = False):
    msg = await message.reply("⏳ Processing your download...")
    file_id = uuid4().hex

    ydl_opts = {
        "format": "bestaudio/best" if audio_only else "best",
        "outtmpl": f"{file_id}.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp3" if audio_only else "mp4",
        "noplaylist": True,
        "geo_bypass": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get("title", "Downloaded")
            ext = "mp3" if audio_only else filename.split(".")[-1]
            final_file = f"{file_id}.{ext}"

        if os.path.exists(final_file):
            caption = f"✅ <b>{title}</b>"
            await message.reply_document(final_file, caption=caption, parse_mode="HTML")
            await msg.delete()
            os.remove(final_file)
        else:
            await msg.edit("❌ Download failed. File not found.")
    except Exception as e:
        logging.error("Download error", exc_info=e)
        await msg.edit(f"❌ Error: {str(e)}")

