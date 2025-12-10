import os
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from gtts import gTTS

# ================= CONFIGURATION (Variables from Railway) =================
# Ye values Railway ke Variables tab se uthayega
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

ADMIN_ID = int(os.getenv("ADMIN_ID", "12345")) # Teri ID
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-100")) # VC wali chat ID

# ================= INITIALIZATION =================
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
call_py = PyTgCalls(user)

# ================= LOGIC START =================

@bot.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(_, message):
    await message.reply_text(
        "**🎙 Voice Changer Bot Active!**\n\n"
        "1. `/vcon` - Userbot VC Join karega\n"
        "2. `/vcoff` - Userbot VC Leave karega\n"
        "3. **Send Voice Note** - Deep Voice me play hoga\n"
        "4. `/vct <text>` - Text bolega Deep Voice me"
    )

@bot.on_message(filters.command("vcon") & filters.user(ADMIN_ID))
async def vc_on(_, message):
    msg = await message.reply_text("🔌 Joining VC...")
    try:
        # Dummy stream to keep connection alive
        await call_py.join_group_call(
            TARGET_CHAT_ID,
            MediaStream("http://docs.google.com/uc?export=open&id=1V_p7e5X9_xM5c") 
        )
        await msg.edit_text("✅ **Connected!** Ab Voice Note bhejo.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

@bot.on_message(filters.command("vcoff") & filters.user(ADMIN_ID))
async def vc_off(_, message):
    try:
        await call_py.leave_group_call(TARGET_CHAT_ID)
        await message.reply_text("👋 Disconnected.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

async def convert_audio(input_file):
    output_file = "final_output.mp3"
    # FFmpeg Magic: Pitch Deep (0.85) + Bass Boost (Equalizer)
    cmd = (
        f'ffmpeg -y -i "{input_file}" '
        f'-af "asetrate=44100*0.85,aresample=44100,equalizer=f=60:width_type=o:width=2:g=15" '
        f'{output_file}'
    )
    os.system(cmd)
    return output_file

@bot.on_message(filters.voice & filters.private & filters.user(ADMIN_ID))
async def voice_handler(_, message):
    status = await message.reply_text("🎤 Processing Voice...")
    try:
        dl_file = await message.download()
        processed_file = await convert_audio(dl_file)
        
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Speaking in VC...**")
        
        # Thoda wait karke cleanup karenge
        await asyncio.sleep(10)
        if os.path.exists(dl_file): os.remove(dl_file)
        # Processed file delete nahi kar rahe turant taaki play ho sake
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")

@bot.on_message(filters.command("vct") & filters.user(ADMIN_ID))
async def tts_handler(_, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/vct Hello World`")
        return
    
    text = message.text.split(None, 1)[1]
    status = await message.reply_text("🗣 Generating Audio...")
    
    try:
        tts = gTTS(text=text, lang='hi')
        raw_file = "tts.mp3"
        tts.save(raw_file)
        
        processed_file = await convert_audio(raw_file)
        await call_py.play(TARGET_CHAT_ID, MediaStream(processed_file))
        await status.edit_text("🔊 **Speaking Text...**")
        
        if os.path.exists(raw_file): os.remove(raw_file)
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")

# ================= RUNNER =================
async def main():
    await bot.start()
    await user.start()
    await call_py.start()
    print("🤖 BOT STARTED ON RAILWAY!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
      
