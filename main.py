import os
import asyncio
import logging
from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ================= DEBUGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= CONFIGURATION =================
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))

# ================= CLIENTS =================
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    logger.warning("⚠️ SESSION_STRING missing!")
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)

call_py = PyTgCalls(user)

# ================= AUDIO CONVERTER =================
async def convert_audio(input_file):
    output_file = "final_output.mp3"
    # Deep Voice Effect (Pitch 0.85 + Bass Boost)
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,'
        f'equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}" -loglevel error'
    )
    os.system(cmd)
    return output_file

# ================= COMMANDS =================

@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "✅ **Voice Changer Bot Ready!**\n\n"
        "1. `/vcon` - Connect to VC\n"
        "2. **Send Voice Note** - Play Deep Voice\n"
        "3. `/vcoff` - Disconnect"
    )

@bot.on_message(filters.command("vcon"))
async def vcon(_, message):
    msg = await message.reply_text("🔌 Joining VC...")
    try:
        await call_py.play(
            TARGET_CHAT_ID,
            MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3")
        )
        await msg.edit_text("✅ **Connected!** Ab Voice Note bhejo.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`")

@bot.on_message(filters.command("vcoff"))
async def vcoff(_, message):
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 Left VC.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

@bot.on_message(filters.voice & filters.private)
async def voice_handler(_, message):
    sts = await message.reply_text("🎤 Processing...")
    dl_file = await message.download()
    try:
        out = await convert_audio(dl_file)
        await call_py.play(TARGET_CHAT_ID, MediaStream(out))
        await sts.edit_text("🔊 **Playing Deep Voice!**")
        await asyncio.sleep(5)
    except Exception as e:
        await sts.edit_text(f"❌ Error: `{e}`")
    finally:
        if os.path.exists(dl_file): os.remove(dl_file)

# ================= RUNNER =================
async def main():
    await bot.start()
    await user.start()
    await call_py.start()
    logger.info("🤖 BOT STARTED!")
    await idle()
    await call_py.stop()
    await user.stop()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
    
