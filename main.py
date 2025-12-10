import os
import asyncio
import logging
from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import InputAudioStream
from pytgcalls.types import InputStream
from gtts import gTTS

# ================= LOGGING (Debugging ke liye) =================
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

# Authorized Users (Runtime)
AUTH_USERS = set()

# ================= CLIENTS SETUP =================
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    logger.warning("⚠️ SESSION_STRING missing! VC commands work nahi karenge.")
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)

call_py = PyTgCalls(user)

# ================= HELPER FUNCTIONS =================
async def ensure_auth(message) -> bool:
    """Check karta hai user logged in hai ya nahi"""
    if message.from_user.id in AUTH_USERS:
        return True
    await message.reply_text("⛔ **Access Denied!**\nPehle login karo: `/login password`")
    return False

async def convert_audio(input_file: str) -> str:
    """FFmpeg se Deep Voice effect lagata hai"""
    output_file = "final_output.mp3"
    # Deep Voice Filter
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
    logger.info(f"Command /start by {message.from_user.first_name}")
    await message.reply_text(
        "**🎙 Voice Changer Bot Online! (V2)**\n\n"
        "Status: `PyTgCalls v2 Connected` ✅\n"
        "Security: **Locked** 🔒\n\n"
        "🔓 **Unlock karne ke liye:**\n"
        "`/login <password>` bhejo."
    )

@bot.on_message(filters.command("login") & filters.private)
async def login_handler(_, message):
    if len(message.command) < 2:
        await message.reply_text("❓ Usage: `/login sudeepop`")
        return

    password = message.text.split(None, 1)[1].strip()
    if password == BOT_PASSWORD:
        AUTH_USERS.add(message.from_user.id)
        await message.reply_text(
            "✅ **Login Successful!**\n\n"
            "Try these:\n"
            "• `/vcon` - Connect VC\n"
            "• **Voice Note** - Bhejo aur jadu dekho!"
        )
    else:
        await message.reply_text("❌ Galat Password!")

# ================= VC CONTROLS (V2 Syntax) =================

@bot.on_message(filters.command("vcon"))
async def vc_on(_, message):
    if not await ensure_auth(message): return
    msg = await message.reply_text("🔌 Joining VC...")
    try:
        # V2 Syntax: join_group_call use hota hai, play nahi
        await call_py.join_group_call(
            TARGET_CHAT_ID,
            InputStream(
                InputAudioStream(
                    "https://filesamples.com/samples/audio/mp3/sample3.mp3",
                ),
            ),
        )
        await msg.edit_text("✅ **Connected!** Voice note bhejo.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`")

@bot.on_message(filters.command("vcoff"))
async def vc_off(_, message):
    if not await ensure_auth(message): return
    try:
        await call_py.leave_group_call(TARGET_CHAT_ID)
        await message.reply_text("👋 Disconnected.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

@bot.on_message(filters.command("stopvc"))
async def stop_vc(_, message):
    if not await ensure_auth(message): return
    try:
        # V2 me stop ka direct method alag hai, hum leave use kar sakte hain
        # Ya bas naya stream play kar do silent
        await message.reply_text("⏹ Is version me `/vcoff` use karein stop ke liye.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

# ================= VOICE & TTS HANDLERS =================

@bot.on_message(filters.private & filters.voice)
async def voice_handler(_, message):
    if not await ensure_auth(message): return
    status = await message.reply_text("🎤 Processing...")
    dl_file = None
    try:
        dl_file = await message.download()
        processed = await convert_audio(dl_file)
        
        # Streaming to VC
        await call_py.change_stream(
            TARGET_CHAT_ID,
            InputStream(
                InputAudioStream(
                    processed,
                ),
            ),
        )
        
        await status.edit_text("🔊 **Playing in VC!**")
        await asyncio.sleep(5)
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if dl_file and os.path.exists(dl_file): os.remove(dl_file)
        if os.path.exists("final_output.mp3"): os.remove("final_output.mp3")

@bot.on_message(filters.command("vct"))
async def tts_handler(_, message):
    if not await ensure_auth(message): return
    if len(message.command) < 2:
        await message.reply_text("Usage: `/vct Hello`")
        return
    
    text = message.text.split(None, 1)[1]
    status = await message.reply_text("🗣 Generating...")
    raw = "tts.mp3"
    try:
        tts = gTTS(text=text, lang="hi")
        tts.save(raw)
        processed = await convert_audio(raw)
        
        await call_py.change_stream(
            TARGET_CHAT_ID,
            InputStream(
                InputAudioStream(
                    processed,
                ),
            ),
        )
        await status.edit_text("🔊 **Speaking...**")
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if os.path.exists(raw): os.remove(raw)
        if os.path.exists("final_output.mp3"): os.remove("final_output.mp3")

# ================= MAIN RUNNER =================
async def main():
    logger.info("🚀 Starting Services...")
    
    await bot.start()
    await user.start()
    await call_py.start()
    
    logger.info("🤖 BOT IS LIVE! Send /start in DM.")
    
    await idle()
    
    await call_py.stop()
    await user.stop()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
    
