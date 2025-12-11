import os
import asyncio
import logging
from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "sudeepop")

AUTH_USERS = set()

# Clients
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)

call_py = PyTgCalls(user)

# Helpers
async def ensure_auth(message):
    if message.from_user.id in AUTH_USERS: return True
    await message.reply_text("⛔ Login karo: `/login password`")
    return False

async def convert_audio(file):
    out = "final.mp3"
    os.system(f'ffmpeg -y -i "{file}" -af "asetrate=44100*0.85,aresample=44100,equalizer=f=80:width_type=o:width=2:g=8" "{out}"')
    return out

# Commands
@bot.on_message(filters.command("start"))
async def start(_, m):
    await m.reply_text("✅ **Bot Online (v3.0 dev24)!**\nLogin: `/login <password>`")

@bot.on_message(filters.command("login"))
async def login(_, m):
    if len(m.command) > 1 and m.text.split(None, 1)[1].strip() == BOT_PASSWORD:
        AUTH_USERS.add(m.from_user.id)
        await m.reply_text("✅ Logged In!")
    else:
        await m.reply_text("❌ Wrong Password")

@bot.on_message(filters.command("vcon"))
async def vcon(_, m):
    if not await ensure_auth(m): return
    await m.reply_text("🔌 Joining...")
    try:
        await call_py.play(TARGET_CHAT_ID, MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3"))
        await m.reply_text("✅ Connected!")
    except Exception as e:
        await m.reply_text(f"Error: {e}")

@bot.on_message(filters.voice & filters.private)
async def voice(_, m):
    if not await ensure_auth(m): return
    sts = await m.reply_text("🎤 Processing...")
    dl = await m.download()
    try:
        out = await convert_audio(dl)
        await call_py.play(TARGET_CHAT_ID, MediaStream(out))
        await sts.edit_text("🔊 Playing!")
    except Exception as e:
        await sts.edit_text(f"Error: {e}")
    finally:
        if os.path.exists(dl): os.remove(dl)

# Runner
async def main():
    await bot.start()
    await user.start()
    await call_py.start()
    logger.info("BOT STARTED")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
    
