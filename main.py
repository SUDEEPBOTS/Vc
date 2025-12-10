import os
import asyncio
import base64
import struct
import traceback

from pyrogram import Client, filters
import pyrogram.errors as pyro_errors

# ========== Compatibility shim (py-tgcalls expects GroupcallForbidden in pyrogram.errors) ==========
if not hasattr(pyro_errors, "GroupcallForbidden"):
    class GroupcallForbidden(pyro_errors.RPCError):
        """Compatibility shim for older pytgcalls expecting this error class."""
        pass

    pyro_errors.GroupcallForbidden = GroupcallForbidden

# ========== Imports that depend on shim ==========
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ========== Configuration from env ==========
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "12345"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))

# ========== Clients ==========
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# If SESSION_STRING empty, user client will try to use file-based session "user_session"
if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)  # will require interactive auth if run locally

call_py = PyTgCalls(user)

# ========== Helpers ==========
def safe_print(*a, **k):
    print(*a, **k, flush=True)

async def convert_audio(input_file: str) -> str:
    """Convert input audio to a 'deep attractive' mp3 using ffmpeg filters."""
    output_file = "final_output.mp3"
    # ffmpeg filters: lower pitch (asetrate), resample, and a gentle EQ
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}" > /dev/null 2>&1'
    )
    safe_print("Running ffmpeg:", cmd)
    os.system(cmd)
    return output_file

# ========== Bot Command Handlers ==========
@bot.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(_, message):
    await message.reply_text(
        "**🎙 Voice Changer Bot Active!**\n\n"
        "• `/vcon` – Userbot VC join karega\n"
        "• `/vcoff` – Userbot VC leave karega\n"
        "• Private me voice note bhejo – Voic e deep karke VC me play hoga\n"
        "• `/vct <text>` – Text ko deep voice me VC par bolega\n"
        "• `/stopvc` – Current audio ko force stop karega\n\n"
        "_Make sure TARGET_CHAT_ID and ADMIN_ID are set correctly in env._"
    )

@bot.on_message(filters.command("vcon") & filters.user(ADMIN_ID))
async def vc_on(_, message):
    msg = await message.reply_text("🔌 Joining VC...")
    try:
        # Play a tiny dummy audio to ensure join; the file/URL can be anything short
        await call_py.play(TARGET_CHAT_ID, MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3"))
        await msg.edit_text("✅ **Connected!** Ab mujhe DM me voice note bhejo.")
    except Exception as e:
        tb = traceback.format_exc()
        await msg.edit_text(f"❌ Error while joining VC:\n`{e}`")
        safe_print("Error in vc_on:", tb)

@bot.on_message(filters.command("vcoff") & filters.user(ADMIN_ID))
async def vc_off(_, message):
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 VC se disconnect ho gaya.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error while leaving VC:\n`{e}`")
        safe_print("Error in vc_off:", tb)

@bot.on_message(filters.command("stopvc") & filters.user(ADMIN_ID))
async def stop_vc(_, message):
    try:
        await call_py.stop(TARGET_CHAT_ID)
        await message.reply_text("⏹ Current audio stop kar diya.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error while stopping audio:\n`{e}`")
        safe_print("Error in stop_vc:", tb)

# ========== Voice Note Handler (private messages to bot) ==========
@bot.on_message(filters.private & filters.voice & filters.user(ADMIN_ID))
async def voice_handler(_, message):
    status = await message.reply_text("🎤 Processing voice note...")
    dl_file = None
    try:
        dl_file = await message.download()
        safe_print("Downloaded voice note to", dl_file)

        processed_file = await convert_audio(dl_file)
        safe_print("Processed file created:", processed_file)

        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Speaking in VC...**")

        # wait a bit so it starts playing; real logic could check play state
        await asyncio.sleep(5)
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error while processing:\n`{e}`")
        safe_print("Error in voice_handler:", tb)
    finally:
        if dl_file and os.path.exists(dl_file):
            try: os.remove(dl_file)
            except: pass
        if os.path.exists("final_output.mp3"):
            try: os.remove("final_output.mp3")
            except: pass

# ========== Text to Speech ==========
@bot.on_message(filters.command("vct") & filters.user(ADMIN_ID))
async def tts_handler(_, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/vct Tumhara dialogue yahan`", quote=True)
        return

    text = message.text.split(None, 1)[1]
    status = await message.reply_text("🗣 Generating TTS...")
    raw_file = "tts_raw.mp3"
    try:
        tts = gTTS(text=text, lang="hi")
        tts.save(raw_file)
        safe_print("TTS saved to", raw_file)

        processed_file = await convert_audio(raw_file)
        safe_print("Processed TTS to", processed_file)

        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Speaking text in VC...**")
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error in TTS:\n`{e}`")
        safe_print("Error in tts_handler:", tb)
    finally:
        if os.path.exists(raw_file):
            try: os.remove(raw_file)
            except: pass
        if os.path.exists("final_output.mp3"):
            try: os.remove("final_output.mp3")
            except: pass

# ========== Runner ==========
async def main():
    safe_print("Starting bot + user clients...")
    try:
        await bot.start()
        safe_print("Bot client started.")
    except Exception as e:
        safe_print("Failed to start bot client:", e)
        raise

    try:
        await user.start()
        safe_print("User client started.")
    except struct.error as se:
        # Common symptom when SESSION_STRING is invalid or from another library (e.g., telethon).
        safe_print("Invalid session string or session format. struct.error:", se)
        safe_print("Make sure SESSION_STRING is a valid Pyrogram session string (not Telethon).")
        raise
    except Exception as e:
        safe_print("Failed to start user client:", e)
        raise

    try:
        await call_py.start()
        safe_print("PyTgCalls started.")
    except Exception as e:
        safe_print("Failed to start PyTgCalls:", e)
        raise

    safe_print("🤖 Voice Changer BOT STARTED!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("Shutting down (keyboard).")
    except Exception:
        safe_print("Unhandled exception in main:")
        traceback.print_exc()
