import os
import re
import uuid
import shutil
import asyncio
import logging
from datetime import datetime, timedelta

try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
    from telegram.ext import (
        ApplicationBuilder, CommandHandler,
        MessageHandler, CallbackQueryHandler,
        ContextTypes, filters
    )
except ImportError:
    print("❌ telegram module not installed. Please run: pip install python-telegram-bot")
    exit(1)

from yt_dlp import YoutubeDL

# --- CONFIGURATION ---
BOT_TOKEN = "7567180824:AAHDw3DvJkht4OOn8qVjYvkI4mhEMP7X868"
MAX_FILE_SIZE_MB = 49
CLEANUP_AFTER_HOURS = 24

YOUTUBE_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/"
TIKTOK_REGEX = r"(https?://)?(www\.)?tiktok\.com/"
INSTA_REGEX = r"(https?://)?(www\.)?instagram\.com/"
FACEBOOK_REGEX = r"(https?://)?(www\.)?(facebook\.com|fb\.watch)/"
TWITTER_REGEX = r"(https?://)?(twitter\.com|x\.com)/"
GENERAL_URL_REGEX = r"https?://[^\s]+"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)


# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = (
        "🎉 <b>Welcome to UNIVERSAL DOWNLOADER!</b>\n\n"
        "🚀 Download from:\n"
        "• <b>YouTube</b> → MP4 or MP3\n"
        "• <b>TikTok</b>, <b>Instagram</b> → Clean MP4 only\n"
        "• <b>Facebook</b>, <b>X</b>, <b>Others</b> → direct video\n\n"
        "🧹 Files clean after 24 hours.\n"
        "🔗 Just send a video URL.\n\n"
        "<i>Built by @kerajsrs 🛠</i>"
    )
    await update.message.reply_html(intro)


# --- ROUTING ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if re.search(YOUTUBE_REGEX, text):
        await send_youtube_options(update, text)
    elif any(re.search(p, text) for p in [TIKTOK_REGEX, INSTA_REGEX, FACEBOOK_REGEX, TWITTER_REGEX]):
        await download_and_send(text, update.message, audio_only=False)
    elif re.match(GENERAL_URL_REGEX, text):
        await download_and_send(text, update.message, audio_only=False)
    else:
        await update.message.reply_text("❗ Invalid or unsupported link.")


async def send_youtube_options(update: Update, url: str):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎥 Video (MP4)", callback_data=f"yt_video|{url}"),
        InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"yt_audio|{url}")
    ]])
    await update.message.reply_text("Choose format:", reply_markup=keyboard)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, url = query.data.split('|')
    audio_only = (action == "yt_audio")

    await query.edit_message_text("⏳ Please wait... downloading...")
    await download_and_send(url, query.message, audio_only)


# --- CORE DOWNLOADER ---
async def download_and_send(url: str, msg_source, audio_only=False):
    unique_id = str(uuid.uuid4())
    temp_dir = os.path.join(DOWNLOAD_DIR, unique_id)
    os.makedirs(temp_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': f'{temp_dir}/%(title).50s.%(ext)s',
        'format': 'bestaudio/best' if audio_only else 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4' if not audio_only else 'mp3',
        'noplaylist': True,
        'quiet': True,
        'writethumbnail': True,
        'writeinfojson': True,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }
        ] if audio_only else [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }
        ]
    }

    try:
        progress = await msg_source.reply_text("⏬ Processing your request...")

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = os.listdir(temp_dir)
        target_file = next((f for f in files if f.endswith(".mp4") or f.endswith(".mp3")), None)
        thumb_file = next((f for f in files if f.endswith(".jpg")), None)

        if not target_file:
            raise Exception("Download failed: file not found.")

        full_path = os.path.join(temp_dir, target_file)
        if os.path.getsize(full_path) > MAX_FILE_SIZE_MB * 1024 * 1024:
            await msg_source.reply_text("⚠️ File too large for Telegram (>50MB).")
            return

        caption = f"✅ Downloaded: <b>{target_file}</b>"
        if audio_only:
            await msg_source.reply_audio(audio=InputFile(full_path), caption=caption, parse_mode="HTML")
        else:
            await msg_source.reply_video(video=InputFile(full_path), caption=caption, parse_mode="HTML",
                                         thumbnail=os.path.join(temp_dir, thumb_file) if thumb_file else None)

        await progress.delete()

    except Exception as e:
        await msg_source.reply_text(f"❌ Error:\n<code>{str(e)}</code>", parse_mode="HTML")
    finally:
        await cleanup_old_files()


# --- CLEANUP ---
async def cleanup_old_files():
    now = datetime.now()
    for folder in os.listdir(DOWNLOAD_DIR):
        folder_path = os.path.join(DOWNLOAD_DIR, folder)
        if os.path.isdir(folder_path):
            modified = datetime.fromtimestamp(os.path.getmtime(folder_path))
            if now - modified > timedelta(hours=CLEANUP_AFTER_HOURS):
                shutil.rmtree(folder_path, ignore_errors=True)


# --- MAIN ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
