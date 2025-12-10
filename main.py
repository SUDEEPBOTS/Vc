import os
import asyncio
import logging
from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ================= DEBUGGING SETUP =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================= CONFIGURATION =================
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "sudeepop")

# Authorized Users
AUTH_USERS = set()

# ================= CLIENTS SETUP =================
# Bot Client
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User Client (For VC)
if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    logger.warning("⚠️ SESSION_STRING missing!")
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)

# PyTgCalls Client (v3.0.0.dev24)
call_py = PyTgCalls(user)

# ================= HELPER FUNCTIONS =================
async def ensure_auth(message) -> bool:
    if message.from_user.id in AUTH_USERS:
        return True
    await message.reply_text("⛔ **Locked!** Login required: `/login password`")
    return False

async def convert_audio(input_file: str) -> str:
    output_file = "final_output.mp3"
    # Deep Voice + Bass Boost Filter
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,'
        f'equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}" -loglevel error'
    )
    os.system(cmd)
    return output_file

# ================= BOT COMMANDS =================

@bot.on_message(filters.command("start") & filters.private)
async def start(_, message):
    await message.reply_text(
        "**🎙 Voice Changer Bot (Final V3)**\n\n"
        "Status: `Online` ✅\n"
        "Login: `/login <password>`"
    )

@bot.on_message(filters.command("login") & filters.private)
async def login_handler(_, message):
    if len(message.command) < 2: return
    if message.text.split(None, 1)[1].strip() == BOT_PASSWORD:
        AUTH_USERS.add(message.from_user.id)
        await message.reply_text("✅ **Logged In!** Try `/vcon`")
    else:
        await message.reply_text("❌ Wrong Password")

# ================= VC COMMANDS =================

@bot.on_message(filters.command("vcon"))
async def vc_on(_, message):
    if not await ensure_auth(message): return
    msg = await message.reply_text("🔌 Joining VC...")
    try:
        # dev24 Syntax: play() + MediaStream()
        await call_py.play(
            TARGET_CHAT_ID,
            MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3")
        )
        await msg.edit_text("✅ **Connected!** Voice note bhejo.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`")

@bot.on_message(filters.command("vcoff"))
async def vc_off(_, message):
    if not await ensure_auth(message): return
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 Left VC.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

@bot.on_message(filters.private & filters.voice)
async def voice_handler(_, message):
    if not await ensure_auth(message): return
    status = await message.reply_text("🎤 Processing...")
    dl_file = await message.download()
    try:
        processed = await convert_audio(dl_file)
        
        # Play Processed Audio
        await call_py.play(
            TARGET_CHAT_ID,
            MediaStream(processed)
        )
        await status.edit_text("🔊 **Playing Deep Voice!**")
        await asyncio.sleep(5)
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if os.path.exists(dl_file): os.remove(dl_file)

# ================= RUNNER =================
async def main():
    logger.info("🚀 Starting Bot...")
    await bot.start()
    await user.start()
    await call_py.start()
    logger.info("🤖 BOT IS LIVE!")
    await idle()
    await call_py.stop()
    await user.stop()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
    
