import os
import asyncio
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

# Admin ID hata diya, ab sirf password se auth hoga
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))

# Password env se (Railway me BOT_PASSWORD set kar sakta hai)
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "sudeepop")  # yahan apna secret rakhna

# In-memory authorized users (runtime ke liye)
AUTH_USERS = set()

# ========== Clients ==========
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if SESSION_STRING:
    # IMPORTANT: yahan **Pyrogram** ka session string chahiye, Telethon wala nahi chalega
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    user = Client("user_session", api_id=API_ID, api_hash=API_HASH)

call_py = PyTgCalls(user)

# ========== Helpers ==========
def safe_print(*a, **k):
    print(*a, **k, flush=True)


async def convert_audio(input_file: str) -> str:
    """Convert input audio to a 'deep attractive' mp3 using ffmpeg filters."""
    output_file = "final_output.mp3"
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,'
        f'equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}" > /dev/null 2>&1'
    )
    safe_print("Running ffmpeg:", cmd)
    os.system(cmd)
    return output_file


async def ensure_auth(message) -> bool:
    """Check karega user authorized hai ya nahi."""
    user = message.from_user
    if not user:
        return False

    if user.id not in AUTH_USERS:
        await message.reply_text(
            "⛔ Pehle password se login karo.\n\n"
            "1. DM me `/start` bhejo.\n"
            "2. Phir `/login <password>` bhejo."
        )
        return False
    return True


# ========== AUTH SYSTEM ==========

@bot.on_message(filters.command("start") & filters.private)
async def start(_, message):
    await message.reply_text(
        "**🎙 Voice Changer Bot Ready!**\n\n"
        "Yeh bot password protected hai.\n\n"
        "**Login steps:**\n"
        "1. ` /login <password>` DM me bhejo.\n"
        "   Example: ` /login sudeepop`\n\n"
        "Password sahi hua to tumhe access mil jayega."
    )


@bot.on_message(filters.command("login") & filters.private)
async def login_handler(_, message):
    if len(message.command) < 2:
        await message.reply_text(
            "❓ Usage: `/login <password>`\n"
            "Example: `/login sudeepop`",
            quote=True,
        )
        return

    given_password = message.text.split(None, 1)[1].strip()

    if given_password == BOT_PASSWORD:
        user_id = message.from_user.id
        AUTH_USERS.add(user_id)
        await message.reply_text(
            "✅ **Login successful!**\n\n"
            "Ab tum ye commands use kar sakte ho:\n"
            "• `/vcon` – VC join\n"
            "• `/vcoff` – VC leave\n"
            "• `/stopvc` – audio stop\n"
            "• DM me voice note – deep voice me VC par play\n"
            "• `/vct <text>` – text ko deep voice me bolna"
        )
        safe_print("User authorized:", user_id)
    else:
        await message.reply_text("❌ Galat password. Dubara try karo.")


# ========== Bot Command Handlers (ab password based auth) ==========

@bot.on_message(filters.command("vcon"))
async def vc_on(_, message):
    if not await ensure_auth(message):
        return

    msg = await message.reply_text("🔌 Joining VC...")
    try:
        await call_py.play(
            TARGET_CHAT_ID,
            MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3")
        )
        await msg.edit_text("✅ **Connected!** Ab mujhe DM me voice note bhejo.")
    except Exception as e:
        tb = traceback.format_exc()
        await msg.edit_text(f"❌ Error while joining VC:\n`{e}`")
        safe_print("Error in vc_on:", tb)


@bot.on_message(filters.command("vcoff"))
async def vc_off(_, message):
    if not await ensure_auth(message):
        return

    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 VC se disconnect ho gaya.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error while leaving VC:\n`{e}`")
        safe_print("Error in vc_off:", tb)


@bot.on_message(filters.command("stopvc"))
async def stop_vc(_, message):
    if not await ensure_auth(message):
        return

    try:
        await call_py.stop(TARGET_CHAT_ID)
        await message.reply_text("⏹ Current audio stop kar diya.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Error while stopping audio:\n`{e}`")
        safe_print("Error in stop_vc:", tb)


# ========== Voice Note Handler (private DM) ==========

@bot.on_message(filters.private & filters.voice)
async def voice_handler(_, message):
    if not await ensure_auth(message):
        return

    status = await message.reply_text("🎤 Processing voice note...")
    dl_file = None
    try:
        dl_file = await message.download()
        safe_print("Downloaded voice note to", dl_file)

        processed_file = await convert_audio(dl_file)
        safe_print("Processed file created:", processed_file)

        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Speaking in VC...**")

        await asyncio.sleep(5)
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error while processing:\n`{e}`")
        safe_print("Error in voice_handler:", tb)
    finally:
        try:
            if dl_file and os.path.exists(dl_file):
                os.remove(dl_file)
            if os.path.exists("final_output.mp3"):
                os.remove("final_output.mp3")
        except:
            pass


# ========== Text to Speech ==========
@bot.on_message(filters.command("vct"))
async def tts_handler(_, message):
    if not await ensure_auth(message):
        return

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
        try:
            if os.path.exists(raw_file):
                os.remove(raw_file)
            if os.path.exists("final_output.mp3"):
                os.remove("final_output.mp3")
        except:
            pass


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
    except Exception as e:
        safe_print("Failed to start user client:", e)
        safe_print("NOTE: SESSION_STRING Pyrogram ka valid string hona chahiye (Telethon nahi).")
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
