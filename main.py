#!/usr/bin/env python3
import os
import asyncio
import base64
import struct
import traceback
import time

from pyrogram import Client, filters
import pyrogram.errors as pyro_errors

# ---------- COMPATIBILITY SHIMS ----------
# 1) GroupcallForbidden shim (py-tgcalls older code expects it)
if not hasattr(pyro_errors, "GroupcallForbidden"):
    class GroupcallForbidden(pyro_errors.RPCError):
        """Compatibility shim for old PyTgCalls code."""
        pass
    pyro_errors.GroupcallForbidden = GroupcallForbidden

# 2) ntgcalls.InputMode shim (if binary misses this symbol)
try:
    import ntgcalls as _nt
    if not hasattr(_nt, "InputMode"):
        class _ShimInputMode:
            FILE = 0
            STREAM = 1
        _nt.InputMode = _ShimInputMode
except Exception:
    # ntgcalls may not be installed yet; we'll catch import errors later when importing pytgcalls
    _nt = None

# ---------- IMPORTS (after shims) ----------
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import MediaStream
except Exception as e:
    # If this fails, we still continue but will log nicely at startup.
    PyTgCalls = None
    MediaStream = None
    print("WARN: pytgcalls import failed at module load. Reason:", e)

from gtts import gTTS

# ---------- CONFIG (from env) ----------
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "letmein")  # set this in Railway secrets
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-1001234567890"))  # change
# NOTE: ADMIN_ID removed as requested

# ---------- CLIENTS ----------
bot = Client(
    "bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    # set workers/lazy parameters if needed
)

if SESSION_STRING:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)

# create call_py lazily after confirming pytgcalls imported
call_py = None
if PyTgCalls and user:
    try:
        call_py = PyTgCalls(user)
    except Exception as e:
        print("WARN: PyTgCalls init failed now:", e)
        call_py = None

# ---------- STATE ----------
# store authorized users after password provided (in-memory)
AUTHORIZED = set()
# small lock to protect AUTHORIZED
_auth_lock = asyncio.Lock()

def safe_print(*a, **k):
    print(*a, **k, flush=True)

# ---------- AUDIO processing ----------
async def convert_audio(input_file: str) -> str:
    """
    Convert audio to 'deep attractive' mp3 using ffmpeg filters.
    Output file: final_output.mp3
    """
    output_file = f"final_output_{int(time.time())}.mp3"
    # Lower pitch, resample and EQ to sound deeper & fuller
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}"'
    )
    safe_print("Running ffmpeg:", cmd)
    os.system(cmd)
    return output_file

# ---------- AUTH helpers ----------
async def is_authorized(user_id: int) -> bool:
    async with _auth_lock:
        return user_id in AUTHORIZED

async def authorize(user_id: int):
    async with _auth_lock:
        AUTHORIZED.add(user_id)

# ---------- COMMANDS ----------
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(_, message):
    user_id = message.from_user.id
    safe_print(f"/start from {user_id} ({message.from_user.username})")
    if await is_authorized(user_id):
        await message.reply_text("Bot already unlocked — welcome back! Use /help to see commands.")
        return

    await message.reply_text("🔐 Bot locked. Please send password to unlock (reply to this message).")
    # We expect next message to be the password. We'll catch it in on_message(text) handler.

@bot.on_message(filters.private & filters.text)
async def password_listener(_, message):
    user_id = message.from_user.id
    text = message.text.strip()
    # If already authorized, ignore here (so normal commands work)
    if await is_authorized(user_id):
        return  # let other handlers respond (like commands) — commands have their own decorators
    # treat this as possible password
    if text == BOT_PASSWORD:
        await authorize(user_id)
        await message.reply_text("✅ Password accepted. Bot unlocked — ab aap commands use kar sakte ho.\nUse /vcon to join VC.")
        safe_print(f"user {user_id} authorized via password.")
    else:
        await message.reply_text("❌ Password wrong. Dobara try karo.")

@bot.on_message(filters.command("help") & filters.private)
async def help_cmd(_, message):
    if not await is_authorized(message.from_user.id):
        await message.reply_text("Bot locked. Send password first.")
        return
    await message.reply_text(
        "**Voice Changer Bot Commands**\n\n"
        "• `/vcon` - Userbot joins VC (dummy short audio to force join)\n"
        "• `/vcoff` - Userbot leaves VC\n"
        "• Send voice note (in DM) - will be converted deep and played in VC\n"
        "• `/vct <text>` - speak text in deep voice in VC\n"
        "• `/stopvc` - stop current playing audio\n"
    )

@bot.on_message(filters.command("vcon") & filters.private)
async def vc_on(_, message):
    if not await is_authorized(message.from_user.id):
        await message.reply_text("Bot locked. Send password first.")
        return

    msg = await message.reply_text("🔌 Joining VC...")
    try:
        if call_py is None or MediaStream is None:
            await msg.edit_text("❌ Voice backend not available (pytgcalls not initialized). Check logs.")
            return

        # Play tiny sample to join VC
        await call_py.play(TARGET_CHAT_ID, MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3"))
        await msg.edit_text("✅ Connected to VC. Ab mujhe DM me voice bhejo.")
    except Exception as e:
        tb = traceback.format_exc()
        await msg.edit_text(f"❌ Error while joining VC:\n`{e}`")
        safe_print("Error in vc_on:", tb)

@bot.on_message(filters.command("vcoff") & filters.private)
async def vc_off(_, message):
    if not await is_authorized(message.from_user.id):
        await message.reply_text("Bot locked. Send password first.")
        return
    try:
        if call_py is None:
            await message.reply_text("Voice backend not available.")
            return
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 Disconnected from VC.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error while leaving VC:\n`{e}`")
        safe_print("Error in vc_off:", tb)

@bot.on_message(filters.command("stopvc") & filters.private)
async def stop_vc(_, message):
    if not await is_authorized(message.from_user.id):
        await message.reply_text("Bot locked. Send password first.")
        return
    try:
        if call_py is None:
            await message.reply_text("Voice backend not available.")
            return
        await call_py.stop(TARGET_CHAT_ID)
        await message.reply_text("⏹ Audio stopped in VC.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error stopping audio:\n`{e}`")
        safe_print("Error in stop_vc:", tb)

# ---------- VOICE note handler (DM) ----------
@bot.on_message(filters.private & filters.voice)
async def voice_handler(_, message):
    user_id = message.from_user.id
    if not await is_authorized(user_id):
        await message.reply_text("Bot locked. Send password first.")
        return

    status = await message.reply_text("🎤 Processing voice note...")
    dl_file = None
    try:
        dl_file = await message.download()
        safe_print("Downloaded voice note to", dl_file)
        processed_file = await convert_audio(dl_file)
        safe_print("Processed file:", processed_file)

        if call_py is None or MediaStream is None:
            await status.edit_text("❌ Voice backend not available (pytgcalls not initialized).")
            return
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 Playing in VC...")
        await asyncio.sleep(5)
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error while processing:\n`{e}`")
        safe_print("Error in voice_handler:", tb)
    finally:
        try:
            if dl_file and os.path.exists(dl_file): os.remove(dl_file)
        except: pass
        try:
            if os.path.exists(processed_file): os.remove(processed_file)
        except: pass

# ---------- TTS ----------
@bot.on_message(filters.command("vct") & filters.private)
async def tts_handler(_, message):
    user_id = message.from_user.id
    if not await is_authorized(user_id):
        await message.reply_text("Bot locked. Send password first.")
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: /vct <text>")
        return

    txt = message.text.split(None,1)[1]
    status = await message.reply_text("🗣 Generating TTS...")
    raw = f"tts_{int(time.time())}.mp3"
    try:
        tts = gTTS(text=txt, lang="hi")
        tts.save(raw)
        safe_print("TTS saved to", raw)
        processed = await convert_audio(raw)
        if call_py is None or MediaStream is None:
            await status.edit_text("❌ Voice backend not available (pytgcalls not initialized).")
            return
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed))
        await status.edit_text("🔊 Speaking in VC...")
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error in TTS:\n`{e}`")
        safe_print("Error in tts_handler:", tb)
    finally:
        try: os.remove(raw)
        except: pass
        try: os.remove(processed)
        except: pass

# ---------- RUNNER ----------
async def main():
    safe_print("Starting bot and user clients...")
    try:
        await bot.start()
        safe_print("Bot started.")
    except Exception as e:
        safe_print("Failed to start bot:", e)
        raise

    try:
        await user.start()
        safe_print("User client started.")
    except struct.error as se:
        safe_print("Invalid session string format. Is SESSION_STRING a Pyrogram string? error:", se)
        raise
    except Exception as e:
        safe_print("Failed to start user client:", e)
        raise

    global call_py
    if call_py is None:
        try:
            # try to initialize PyTgCalls now that user client exists
            from pytgcalls import PyTgCalls
            from pytgcalls.types import MediaStream  # ensure this imports
            call_py = PyTgCalls(user)
            safe_print("PyTgCalls initialized.")
        except Exception as e:
            safe_print("PyTgCalls could not be initialized:", e)
            # don't raise here — bot can still respond, but VC will be unavailable.

    safe_print("Bot ready. Waiting for messages...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("Shutting down.")
    except Exception:
        safe_print("Unhandled exception:")
        traceback.print_exc()
