import re
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from yt_dlp import YoutubeDL

# --- YOUR BOT TOKEN ---
BOT_TOKEN = "7567180824:AAHDw3DvJkht4OOn8qVjYvkI4mhEMP7X868"

# --- Regex patterns for platform detection ---
YOUTUBE_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/"
TIKTOK_REGEX = r"(https?://)?(www\.)?tiktok\.com/"
INSTA_REGEX = r"(https?://)?(www\.)?instagram\.com/"
FACEBOOK_REGEX = r"(https?://)?(www\.)?(facebook\.com|fb\.watch)/"
TWITTER_REGEX = r"(https?://)?(www\.)?(twitter\.com|x\.com)/"

# --- /start command handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = (
        "🎉 <b>Welcome to UNIVERSAL DOWNLOADER!</b>\n\n"
        "🚀 Download videos & audio from your favorite platforms:\n"
        "• 🎥 <b>YouTube</b> → choose MP4 or MP3\n"
        "• 🎵 <b>TikTok</b>, <b>Instagram</b> → clean no-watermark videos\n"
        "• 📘 <b>Facebook</b>, <b>Twitter/X</b> → direct video download\n\n"
        "📌 Just send a valid video link and let the magic happen ✨\n\n"
        "<i>Need help or want to request new features? Contact the creator.</i>"
    )
    await update.message.reply_html(intro)

# --- Handle all incoming messages ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if re.search(YOUTUBE_REGEX, text):
        await send_youtube_options(update, text)
    elif any(re.search(p, text) for p in [TIKTOK_REGEX, INSTA_REGEX, FACEBOOK_REGEX, TWITTER_REGEX]):
        await download_and_send(text, update.message, audio_only=False)
    else:
        await update.message.reply_text("❗ Unsupported or invalid link.\nTry YouTube, TikTok, Instagram, Facebook, or Twitter.")

# --- Show inline buttons for YouTube formats ---
async def send_youtube_options(update: Update, url: str):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎥 Video (MP4)", callback_data=f"yt_video|{url}"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"yt_audio|{url}")
        ]
    ])
    await update.message.reply_text("Choose a format to download:", reply_markup=keyboard)

# --- Handle YouTube button clicks ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, url = query.data.split('|')
    audio_only = (action == "yt_audio")

    await query.edit_message_text("📥 Downloading... Please wait...")
    await download_and_send(url, query.message, audio_only)

# --- Download and send the video/audio file ---
async def download_and_send(url: str, msg_source, audio_only=False):
    filename = "download.mp3" if audio_only else "download.mp4"

    ydl_opts = {
        'outtmpl': filename,
        'format': 'bestaudio/best' if audio_only else 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4' if not audio_only else 'mp3',
        'noplaylist': True,
        'quiet': True
    }

    try:
        progress = await msg_source.reply_text("⏬ Processing your download...")

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Check size limit (Telegram max ~50MB)
        if os.path.getsize(filename) > 50 * 1024 * 1024:
            await msg_source.reply_text("⚠️ File is too large to send on Telegram (limit is ~50MB). Try a smaller video.")
            os.remove(filename)
            return

        if audio_only:
            await msg_source.reply_audio(audio=open(filename, 'rb'))
        else:
            await msg_source.reply_video(video=open(filename, 'rb'))

        await progress.delete()

    except Exception as e:
        await msg_source.reply_text(f"❌ Download failed.\n<code>{str(e)}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# --- Run the bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
