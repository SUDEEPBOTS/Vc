import os
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ================= CONFIGURATION =================
# Railway env vars se data lega (Dashboard > Variables)
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Sirf tu use kar sake isliye ADMIN_ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "12345"))

# VC jo group/ channel me join karega uska ID (e.g. -1001234567890)
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100"))

# ================= BASIC CHECK ===================

missing = []
if not API_HASH:
    missing.append("API_HASH")
if not BOT_TOKEN:
    missing.append("BOT_TOKEN")
if not SESSION_STRING:
    missing.append("SESSION_STRING")

if missing:
    print(f"[ERROR] Missing env vars: {', '.join(missing)}")
    print("Railway me jaake ye sab add kar:")
    print("API_ID, API_HASH, BOT_TOKEN, SESSION_STRING, ADMIN_ID, TARGET_CHAT_ID")
    # Crash karo taaki tu turant samajh jaaye
    raise SystemExit(1)

# ================= INITIALIZATION =================
bot = Client(
    "bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

user = Client(
    "user_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

# VC engine
call_py = PyTgCalls(user)


# ================= HANDLERS =================

@bot.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start_cmd(_, message):
    await message.reply_text(
        "**🎙 Voice Changer Bot Online!**\n\n"
        "Commands:\n"
        "• `/vcon` – Userbot voice chat **join** karega\n"
        "• `/vcoff` – Voice chat **leave** karega\n"
        "• `/vct <text>` – Text ko deep voice me VC pe bolega\n"
        "• Sirf DM me **voice note bhejo** → deep & attractive ban kar VC me play hoga\n"
        "• `/stopvc` – Force stop / clear stream\n"
    )


@bot.on_message(filters.command("vcon") & filters.user(ADMIN_ID))
async def vc_on(_, message):
    msg = await message.reply_text("🔌 Voice chat join ho raha hai...")
    try:
        # Yahan ek dummy stream se join kara rahe hain.
        # Chahe toh tu apna khud ka mp3 URL laga sakta hai.
        await call_py.play(
            TARGET_CHAT_ID,
            MediaStream(
                "http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4"
            ),
        )
        await msg.edit_text("✅ **VC me connect ho gaya!**\nAb DM me voice note bhej.")
    except Exception as e:
        await msg.edit_text(f"❌ VC join error:\n`{e}`")


@bot.on_message(filters.command(["vcoff", "leavevc"]) & filters.user(ADMIN_ID))
async def vc_off(_, message):
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("👋 VC se disconnect ho gaya.")
    except Exception as e:
        await message.reply_text(f"❌ VC leave error:\n`{e}`")


@bot.on_message(filters.command("stopvc") & filters.user(ADMIN_ID))
async def stop_vc(_, message):
    """
    Force stop current stream (agar library support kare to).
    Yahan hum simple leave+rejoin ka pattern use kar sakte hain agar
    future me zarurat ho.
    """
    try:
        await call_py.leave_call(TARGET_CHAT_ID)
        await message.reply_text("⏹ Stream force stop kar diya (VC se bhi nikal gaya).")
    except Exception as e:
        await message.reply_text(f"❌ Stop error:\n`{e}`")


# ==== AUDIO PROCESSING (Deep Voice) ====

async def convert_audio(input_file: str) -> str:
    """
    FFmpeg magic – pitch kam karke deep / attractive voice banata hai.
    """
    output_file = "final_output.mp3"
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,'
        f'equalizer=f=60:width_type=o:width=2:g=15" '
        f'"{output_file}"'
    )
    os.system(cmd)
    return output_file


@bot.on_message(filters.voice & filters.private & filters.user(ADMIN_ID))
async def voice_handler(_, message):
    """
    Tu bot ke DM me voice note bhejega:
    1) Download
    2) Deep voice me convert
    3) VC me play
    """
    status = await message.reply_text("🎤 Voice process ho raha hai, ruk zara...")
    try:
        # 1) Download original voice
        dl_file = await message.download()

        # 2) Deep voice conversion
        processed_file = await convert_audio(dl_file)

        # 3) VC me play
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **VC me deep voice baj raha hai...**")

        # 4) Thoda wait, phir temp file hata sakte
        await asyncio.sleep(15)

        if os.path.exists(dl_file):
            os.remove(dl_file)
        if os.path.exists(processed_file):
            os.remove(processed_file)

    except Exception as e:
        await status.edit_text(f"❌ Voice error:\n`{e}`")


@bot.on_message(filters.command("vct") & filters.user(ADMIN_ID))
async def tts_handler(_, message):
    """
    /vct <text>
    → text ko Hindi TTS + deep filter karke VC me play karega
    """
    if len(message.command) < 2:
        await message.reply_text("Usage: `/vct Hello world`", quote=True)
        return

    text = message.text.split(None, 1)[1]
    status = await message.reply_text("🗣 Text se audio bana raha hoon...")

    raw_file = "tts_raw.mp3"

    try:
        # 1) Text to speech
        tts = gTTS(text=text, lang='hi')
        tts.save(raw_file)

        # 2) Deep voice filter
        processed_file = await convert_audio(raw_file)

        # 3) VC me play
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Text VC me bol diya!**")

        # 4) Clean-up
        if os.path.exists(raw_file):
            os.remove(raw_file)
        if os.path.exists(processed_file):
            os.remove(processed_file)

    except Exception as e:
        await status.edit_text(f"❌ TTS error:\n`{e}`")


# ================= RUNNER =================

async def main():
    # Dono clients + VC engine start
    await bot.start()
    await user.start()
    await call_py.start()

    print("🤖 Voice Changer Bot Railway pe successfully start ho gaya!")
    # Process ko zinda rakhne ke liye infinite wait
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
