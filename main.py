# main.py
import os
import asyncio
import traceback
from typing import Set

from pyrogram import Client, filters
import pyrogram.errors as pyro_errors

# ====== compatibility shim (older pytgcalls expects this error class) ======
if not hasattr(pyro_errors, "GroupcallForbidden"):
    class GroupcallForbidden(pyro_errors.RPCError):
        """Compatibility shim for older pytgcalls expecting this error class."""
        pass
    pyro_errors.GroupcallForbidden = GroupcallForbidden

# ====== pytgcalls and TTS imports ======
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ====== CONFIG (env) ======
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")    # pyrogram session string (pyrogram format)
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "1234")    # set a strong password in Railway env
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))  # your group/channel VC ID

# ====== Clients ======
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)  # interactive if local

call_py = PyTgCalls(user)

# ====== runtime state ======
unlocked_users: Set[int] = set()  # who passed password

def log(*a, **k):
    print(*a, **k, flush=True)

# ====== helpers ======
async def convert_audio(input_file: str) -> str:
    """
    Convert input audio to a 'deep attractive' mp3 using ffmpeg filters.
    Returns path to output file.
    """
    output_file = "final_output.mp3"
    # lower pitch (asetrate), resample and apply mild EQ (tune params to taste)
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}" > /proc/1/fd/1 2>/proc/1/fd/2'
    )
    log("Running ffmpeg:", cmd)
    os.system(cmd)
    return output_file

# ====== COMMANDS ======
@bot.on_message(filters.private & filters.command("start"))
async def cmd_start(_, message):
    # ask for password (DM)
    await message.reply_text(
        "🔒 Bot protected. Kripya password bhejein to continue.\n\n"
        "Usage: reply with `/pass <your_password>`"
    )

@bot.on_message(filters.private & filters.command("pass"))
async def cmd_pass(_, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/pass <password>`")
        return

    pwd = message.text.split(None, 1)[1].strip()
    uid = message.from_user.id
    if pwd == BOT_PASSWORD:
        unlocked_users.add(uid)
        await message.reply_text("✅ Password sahi — ab commands use kar sakte ho.\nCommands:\n`/vcon` `/vcoff` `/stopvc` `/vct <text>`\nOR DM me voice note bhejo.")
    else:
        await message.reply_text("❌ Galat password. Dobara try karo.")

def user_unlocked(message):
    return message.from_user and message.from_user.id in unlocked_users

@bot.on_message(filters.private & filters.command("vcon"))
async def vc_on(_, message):
    if not user_unlocked(message):
        await message.reply_text("🔐 Pehle password do: `/pass <password>`")
        return
    msg = await message.reply_text("🔌 Joining VC (trying)...")
    try:
        # join by starting a short sample (any URL or file). Use a short hosted mp3 or local file.
        await call_py.play(TARGET_CHAT_ID, MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3"))
        await msg.edit_text("✅ Connected to VC — ab aap DM me voice bhej sakte ho.")
    except Exception as e:
        tb = traceback.format_exc()
        await msg.edit_text(f"❌ Error while joining VC:\n`{e}`")
        log("vc_on error:", tb)

@bot.on_message(filters.private & filters.command("vcoff"))
async def vc_off(_, message):
    if not user_unlocked(message):
        await message.reply_text("🔐 Pehle password do: `/pass <password>`")
        return
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 Disconnected from VC.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error while leaving VC:\n`{e}`")
        log("vc_off error:", tb)

@bot.on_message(filters.private & filters.command("stopvc"))
async def stop_vc(_, message):
    if not user_unlocked(message):
        await message.reply_text("🔐 Pehle password do: `/pass <password>`")
        return
    try:
        await call_py.stop(TARGET_CHAT_ID)
        await message.reply_text("⏹ Stopped current audio in VC.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error while stopping audio:\n`{e}`")
        log("stop_vc error:", tb)

@bot.on_message(filters.private & filters.command("vct"))
async def tts_handler(_, message):
    if not user_unlocked(message):
        await message.reply_text("🔐 Pehle password do: `/pass <password>`")
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: `/vct Tumhara text yahan`")
        return
    text = message.text.split(None, 1)[1]
    status = await message.reply_text("🗣 Generating TTS...")
    raw_file = "tts_raw.mp3"
    try:
        tts = gTTS(text=text, lang="hi")
        tts.save(raw_file)
        processed = await convert_audio(raw_file)
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed))
        await status.edit_text("🔊 Speaking in VC...")
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error in TTS:\n`{e}`")
        log("tts error:", tb)
    finally:
        for f in (raw_file, "final_output.mp3"):
            try:
                if os.path.exists(f): os.remove(f)
            except: pass

@bot.on_message(filters.private & filters.voice)
async def voice_handler(_, message):
    # only unlocked users can use it
    if not user_unlocked(message):
        await message.reply_text("🔐 Pehle password do: `/pass <password>`")
        return
    status = await message.reply_text("🎤 Processing voice note...")
    dl_file = None
    try:
        dl_file = await message.download()
        log("Downloaded:", dl_file)
        processed = await convert_audio(dl_file)
        log("Processed file:", processed)
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed))
        await status.edit_text("🔊 Playing in VC...")
        await asyncio.sleep(2)
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error while processing:\n`{e}`")
        log("voice_handler error:", tb)
    finally:
        for f in (dl_file, "final_output.mp3"):
            try:
                if f and os.path.exists(f): os.remove(f)
            except: pass

# ====== RUNNER ======
async def main():
    log("Starting bot + user clients...")
    try:
        await bot.start()
        log("Bot client started.")
    except Exception as e:
        log("Failed to start bot client:", e)
        raise

    try:
        await user.start()
        log("User client started.")
    except Exception as e:
        log("Failed to start user client:", e)
        # if session string invalid you'll see struct.error earlier; check logs
        raise

    try:
        await call_py.start()
        log("PyTgCalls started.")
    except Exception as e:
        log("Failed to start PyTgCalls:", e)
        raise

    log("Bot ready. Waiting...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Shutting down (keyboard).")
    except Exception:
        log("Unhandled exception in main:")
        traceback.print_exc()
