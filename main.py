import os
import asyncio

from pyrogram import Client, filters
import pyrogram.errors as pyro_errors

# ========= COMPATIBILITY PATCH FOR PYTGCALLS =========
# PyTgCalls purani Pyrogram error: GroupcallForbidden ko use karta hai
# Pyrogram 2.x me ye class nahi hai, isliye yahan fake class bana ke inject kar rahe hain
if not hasattr(pyro_errors, "GroupcallForbidden"):
    class GroupcallForbidden(pyro_errors.RPCError):
        """Compatibility shim for old PyTgCalls code."""
        pass

    pyro_errors.GroupcallForbidden = GroupcallForbidden

# ========= REST OF IMPORTS =========
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ================= CONFIGURATION =================
# Railway ke environment variables se data lega
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

ADMIN_ID = int(os.getenv("ADMIN_ID", "12345"))         # Sirf tum command use kar sako
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))  # VC wala group/channel ID

# ================= INITIALIZATION =================
bot = Client(
    "bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user = Client(
    "user_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Userbot client ko PyTgCalls ke andar use karenge
call_py = PyTgCalls(user)

# ================= COMMAND HANDLERS =================

@bot.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(_, message):
    await message.reply_text(
        "**🎙 Voice Changer Bot Active!**\n\n"
        "• `/vcon` – Userbot VC join karega\n"
        "• `/vcoff` – Userbot VC chhod dega\n"
        "• Private me **voice note bhejo** – Deep + Attractive voice me VC par play hoga\n"
        "• `/vct <text>` – Text ko deep voice me VC par bolega\n"
        "• `/stopvc` – Current audio ko force stop karega"
    )

@bot.on_message(filters.command("vcon") & filters.user(ADMIN_ID))
async def vc_on(_, message):
    msg = await message.reply_text("🔌 Joining VC...")
    try:
        # Dummy stream play karte hi VC join ho jata hai
        await call_py.play(
            TARGET_CHAT_ID,
            MediaStream(
                "https://filesamples.com/samples/audio/mp3/sample3.mp3"  # koi bhi short sample
            )
        )
        await msg.edit_text("✅ **Connected!** Ab mujhe DM me voice note bhejo.")
    except Exception as e:
        await msg.edit_text(f"❌ Error while joining VC:\n`{e}`")

@bot.on_message(filters.command("vcoff") & filters.user(ADMIN_ID))
async def vc_off(_, message):
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 VC se disconnect ho gaya.")
    except Exception as e:
        await message.reply_text(f"❌ Error while leaving VC:\n`{e}`")

@bot.on_message(filters.command("stopvc") & filters.user(ADMIN_ID))
async def stop_vc(_, message):
    """
    Current media ko stop karta hai, VC me reh sakta hai (agar lib allow kare).
    """
    try:
        await call_py.stop(TARGET_CHAT_ID)
        await message.reply_text("⏹ Current audio stop kar diya.")
    except Exception as e:
        await message.reply_text(f"❌ Error while stopping audio:\n`{e}`")

# ================= AUDIO PROCESSING =================

async def convert_audio(input_file: str) -> str:
    """
    Voice ko deep + attractive banane ke liye FFmpeg filter.
    Output: final_output.mp3
    """
    output_file = "final_output.mp3"
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,'
        f'equalizer=f=80:width_type=o:width=2:g=8" '
        f'"{output_file}"'
    )
    os.system(cmd)
    return output_file

# ========== VOICE NOTE HANDLER (DM) ==========

@bot.on_message(filters.voice & filters.private & filters.user(ADMIN_ID))
async def voice_handler(_, message):
    status = await message.reply_text("🎤 Processing voice note...")
    dl_file = None
    try:
        # 1) Download original voice
        dl_file = await message.download()

        # 2) Filter laga ke deep voice banaye
        processed_file = await convert_audio(dl_file)

        # 3) VC me play karo
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Speaking in VC...**")

        # 4) Thodi der wait (optional)
        await asyncio.sleep(10)

    except Exception as e:
        await status.edit_text(f"❌ Error while processing:\n`{e}`")
    finally:
        # 5) Temp files cleanup
        if dl_file and os.path.exists(dl_file):
            os.remove(dl_file)
        if os.path.exists("final_output.mp3"):
            os.remove("final_output.mp3")

# ========== TEXT-TO-SPEECH HANDLER ==========

@bot.on_message(filters.command("vct") & filters.user(ADMIN_ID))
async def tts_handler(_, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/vct Tumhara dialogue yahan`", quote=True)
        return

    text = message.text.split(None, 1)[1]
    status = await message.reply_text("🗣 Generating TTS...")

    raw_file = "tts_raw.mp3"
    try:
        # 1) gTTS se basic Hindi voice
        tts = gTTS(text=text, lang="hi")
        tts.save(raw_file)

        # 2) Usko deep voice me convert
        processed_file = await convert_audio(raw_file)

        # 3) VC me play
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Speaking text in VC...**")

    except Exception as e:
        await status.edit_text(f"❌ Error in TTS:\n`{e}`")
    finally:
        if os.path.exists(raw_file):
            os.remove(raw_file)
        if os.path.exists("final_output.mp3"):
            os.remove("final_output.mp3")

# ================= RUNNER =================

async def main():
    # Dono clients + PyTgCalls start karo
    await bot.start()
    await user.start()
    await call_py.start()

    print("🤖 Voice Changer BOT STARTED on Railway!")
    # Forever wait
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
