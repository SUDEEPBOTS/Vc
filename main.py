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

TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))  # VC wale group / channel ka ID
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "sudeep-op")      # Apna password yahan env me set kar

# ========== Global state ==========
UNLOCKED_USERS = set()  # jin logon ne password sahi diya hai

# ========== Helpers ==========
def safe_print(*a, **k):
    print(*a, **k, flush=True)


def is_authorized(message) -> bool:
    """
    Sirf un users ko allow karega jinhone password dekar unlock kiya hai.
    Agar unauthorized hai to usko reply de deta hai.
    """
    if not message.from_user:
        return False

    user_id = message.from_user.id
    if user_id in UNLOCKED_USERS:
        return True

    # Agar unlock nahi, to thoda hint de de:
    try:
        # Sirf private ya group me ek baar batayega
        message.reply_text("🔐 Pehle mujhe **DM me /start** karke password do, phir commands kaam karenge.")
    except:
        pass
    return False

# ========== Clients ==========
bot = Client(
    "bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

if SESSION_STRING:
    # Yahan Pyrogram ka session string hi hona chahiye, Telethon wala nahi
    user = Client(
        "user_session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING
    )
else:
    # Agar SESSION_STRING empty hai to ye local run ke time login maangega
    user = Client(
        "user_session",
        api_id=API_ID,
        api_hash=API_HASH
    )

call_py = PyTgCalls(user)

# ========== Audio processing ==========
async def convert_audio(input_file: str) -> str:
    """
    Voice ko deep + thoda attractive banata hai.
    FFmpeg filter:
    - pitch thoda kam (asetrate 0.85)
    - resample
    - low frequency pe halka bass boost
    """
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

# ========== AUTH / PASSWORD HANDLERS ==========

@bot.on_message(filters.command("start"))
async def start_handler(_, message):
    user = message.from_user
    if not user:
        return

    user_id = user.id

    # Agar already unlocked hai:
    if user_id in UNLOCKED_USERS:
        await message.reply_text(
            "**🎙 Voice Changer Bot Ready!**\n\n"
            "Commands:\n"
            "• `/vcon` – VC join karega\n"
            "• `/vcoff` – VC leave karega\n"
            "• Bot ke DM me voice note bhejo – deep + attractive voice me VC me play\n"
            "• `/vct <text>` – Text ko deep voice me VC par bolega\n"
            "• `/stopvc` – Current audio force stop\n"
        )
        return

    # New user ke liye password flow
    await message.reply_text(
        "🔐 **Password Required**\n\n"
        "Is bot ko use karne ke liye pehle password do.\n"
        "Command bhejo:\n\n"
        "`/login your_password`"
    )


@bot.on_message(filters.command("login"))
async def login_handler(_, message):
    user = message.from_user
    if not user:
        return

    user_id = user.id
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.reply_text("Usage: `/login your_password`", quote=True)
        return

    given = parts[1].strip()

    if given == BOT_PASSWORD:
        UNLOCKED_USERS.add(user_id)
        safe_print(f"User {user_id} unlocked successfully.")
        await message.reply_text(
            "✅ **Access Granted!**\n\n"
            "Ab tum saare commands use kar sakte ho:\n"
            "• `/vcon` – VC join\n"
            "• `/vcoff` – VC leave\n"
            "• DM me voice note bhejo\n"
            "• `/vct <text>` – text to deep voice\n"
            "• `/stopvc` – audio stop"
        )
    else:
        await message.reply_text("❌ Galat password. Dubara try karo.")

# ========== VC CONTROL COMMANDS ==========

@bot.on_message(filters.command("vcon"))
async def vc_on(_, message):
    if not is_authorized(message):
        return

    msg = await message.reply_text("🔌 VC join karne ki koshish kar raha hoon...")
    try:
        await call_py.play(
            TARGET_CHAT_ID,
            MediaStream("https://filesamples.com/samples/audio/mp3/sample3.mp3")
        )
        await msg.edit_text("✅ **Connected!** Ab mujhe DM me voice note bhejo.")
    except Exception as e:
        tb = traceback.format_exc()
        await msg.edit_text(f"❌ VC join error:\n`{e}`")
        safe_print("Error in vcon:", tb)


@bot.on_message(filters.command("vcoff"))
async def vc_off(_, message):
    if not is_authorized(message):
        return

    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 VC se disconnect ho gaya.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ VC leave error:\n`{e}`")
        safe_print("Error in vcoff:", tb)


@bot.on_message(filters.command("stopvc"))
async def stop_vc(_, message):
    if not is_authorized(message):
        return

    try:
        await call_py.stop(TARGET_CHAT_ID)
        await message.reply_text("⏹ Current audio stop kar diya.")
    except Exception as e:
        tb = traceback.format_exc()
        await message.reply_text(f"❌ Stop error:\n`{e}`")
        safe_print("Error in stop_vc:", tb)

# ========== VOICE NOTE (PRIVATE) HANDLER ==========

@bot.on_message(filters.private & filters.voice)
async def voice_handler(_, message):
    # Yahan bhi password check
    if not is_authorized(message):
        return

    status = await message.reply_text("🎤 Voice process kar raha hoon...")
    dl_file = None
    try:
        dl_file = await message.download()
        safe_print("Downloaded voice note to", dl_file)

        processed_file = await convert_audio(dl_file)
        safe_print("Processed file created:", processed_file)

        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Deep voice me VC pe bol raha hoon...**")

        await asyncio.sleep(5)
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error while processing:\n`{e}`")
        safe_print("Error in voice_handler:", tb)
    finally:
        if dl_file and os.path.exists(dl_file):
            try:
                os.remove(dl_file)
            except:
                pass
        if os.path.exists("final_output.mp3"):
            try:
                os.remove("final_output.mp3")
            except:
                pass

# ========== TEXT-TO-SPEECH HANDLER ==========

@bot.on_message(filters.command("vct"))
async def tts_handler(_, message):
    if not is_authorized(message):
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: `/vct Tumhara dialogue yahan`", quote=True)
        return

    text = message.text.split(None, 1)[1]
    status = await message.reply_text("🗣 TTS generate kar raha hoon...")
    raw_file = "tts_raw.mp3"

    try:
        tts = gTTS(text=text, lang="hi")
        tts.save(raw_file)
        safe_print("TTS saved to", raw_file)

        processed_file = await convert_audio(raw_file)
        safe_print("Processed TTS to", processed_file)

        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Text deep voice me VC par bol raha hoon...**")
    except Exception as e:
        tb = traceback.format_exc()
        await status.edit_text(f"❌ Error in TTS:\n`{e}`")
        safe_print("Error in tts_handler:", tb)
    finally:
        if os.path.exists(raw_file):
            try:
                os.remove(raw_file)
            except:
                pass
        if os.path.exists("final_output.mp3"):
            try:
                os.remove("final_output.mp3")
            except:
                pass

# ========== Runner ==========

async def main():
    safe_print("Starting bot + user clients...")
    await bot.start()
    safe_print("Bot client started.")

    await user.start()
    safe_print("User client started.")

    await call_py.start()
    safe_print("PyTgCalls started.")

    safe_print("🤖 Voice Changer BOT STARTED & WAITING FOR UPDATES!")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("Shutting down (keyboard).")
    except Exception:
        safe_print("Unhandled exception in main():")
        traceback.print_exc()
