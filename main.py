import os
import asyncio
import traceback
from pyrogram import Client, filters, idle
import pyrogram.errors as pyro_errors

# ========== COMPATIBILITY SHIM (Crash Fix) ==========
# Agar Pyrogram me GroupcallForbidden missing hai to fake bana denge
if not hasattr(pyro_errors, "GroupcallForbidden"):
    class GroupcallForbidden(pyro_errors.RPCError):
        pass
    pyro_errors.GroupcallForbidden = GroupcallForbidden

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ========== CONFIGURATION ==========
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "sudeepop") # Login Password

# Authorized Users List (Runtime)
AUTH_USERS = set()

# ========== CLIENTS SETUP ==========
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    print("⚠️ WARNING: SESSION_STRING missing hai! VC nahi chalega.")
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)

call_py = PyTgCalls(user)

# ========== HELPER FUNCTIONS ==========
def safe_print(*a, **k):
    print(*a, **k, flush=True)

async def convert_audio(input_file: str) -> str:
    """Audio ko Deep + Bass Boosted banata hai"""
    output_file = "final_output.mp3"
    # Filter: Pitch 0.85 (Deep) + Bass Boost
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,'
        f'equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}" > /dev/null 2>&1'
    )
    os.system(cmd)
    return output_file

async def ensure_auth(message) -> bool:
    """Check karta hai user logged in hai ya nahi"""
    if message.from_user.id in AUTH_USERS:
        return True
    await message.reply_text("⛔ **Access Denied!**\nPehle login karo: `/login password`")
    return False

# ========== AUTH COMMANDS ==========

@bot.on_message(filters.command("start") & filters.private)
async def start(_, message):
    await message.reply_text(
        "**🎙 Voice Changer Bot Online!**\n\n"
        "Security: **Active** 🔒\n"
        "Login karne ke liye: `/login <password>` bhejo."
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
            "Commands:\n"
            "• `/vcon` - Join VC\n"
            "• `/vcoff` - Leave VC\n"
            "• **Voice Note** - Play in Deep Voice\n"
            "• `/vct <text>` - Speak Text"
        )
    else:
        await message.reply_text("❌ Galat Password!")

# ========== VC CONTROLS ==========

@bot.on_message(filters.command("vcon"))
async def vc_on(_, message):
    if not await ensure_auth(message): return
    msg = await message.reply_text("🔌 Joining VC...")
    try:
        await call_py.play(TARGET_CHAT_ID, MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3"))
        await msg.edit_text("✅ **Connected!** Voice note bhejo.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`")

@bot.on_message(filters.command("vcoff"))
async def vc_off(_, message):
    if not await ensure_auth(message): return
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 Disconnected.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

@bot.on_message(filters.command("stopvc"))
async def stop_vc(_, message):
    if not await ensure_auth(message): return
    try:
        await call_py.stop(TARGET_CHAT_ID)
        await message.reply_text("⏹ Stopped.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

# ========== VOICE & TTS HANDLERS ==========

@bot.on_message(filters.private & filters.voice)
async def voice_handler(_, message):
    if not await ensure_auth(message): return
    status = await message.reply_text("🎤 Processing...")
    dl_file = None
    try:
        dl_file = await message.download()
        processed = await convert_audio(dl_file)
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed))
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
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed))
        await status.edit_text("🔊 **Speaking...**")
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if os.path.exists(raw): os.remove(raw)
        if os.path.exists("final_output.mp3"): os.remove("final_output.mp3")

# ========== MAIN RUNNER (IDLE FIXED) ==========
async def main():
    safe_print("🚀 Starting Services...")
    
    # 1. Start Bot
    try:
        await bot.start()
        info = await bot.get_me()
        safe_print(f"✅ Bot Started: @{info.username}")
    except Exception as e:
        safe_print("❌ Bot Error:", e)
        return

    # 2. Start Userbot
    try:
        await user.start()
        safe_print("✅ Userbot Started")
    except Exception as e:
        safe_print("❌ Userbot Error (Check String Session):", e)
        return

    # 3. Start Call Client
    try:
        await call_py.start()
        safe_print("✅ PyTgCalls Started")
    except Exception as e:
        safe_print("❌ PyTgCalls Error:", e)
        return

    safe_print("🤖 BOT IS LIVE! Send /start in DM.")
    
    # Ye line bot ko zinda rakhti hai (Polling ka kaam karti hai)
    await idle()
    
    # Stop services on close
    await call_py.stop()
    await user.stop()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
    
