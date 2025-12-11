import os
import sys
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import aiofiles

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from database import db
from userbot_manager import userbot
from voice_processor import voice_processor
from utils.helpers import Timer, format_time, create_progress_bar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(Config.LOGS_DIR, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=Config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# States
class UserStates(StatesGroup):
    waiting_for_group_link = State()
    waiting_for_filter_selection = State()

# ========== COMMAND HANDLERS ==========

@dp.message_handler(commands=['start', 'help'], chat_type=types.ChatType.PRIVATE)
async def start_command(message: types.Message):
    """Start command handler"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Add user to database
    user_data = await db.create_user(user_id, username, first_name)
    
    welcome_text = f"""
    🎤 **InstaVoice Pro Bot** 🎤

    🔊 *Transform Your Voice Like Instagram/TikTok Trends!*

    **✨ Features:**
    • 🔥 Instagram style deep voice effects
    • 🎛️ Multiple viral filters (Deep, Robot, Radio, Echo, Bass)
    • 🎧 Auto-join voice chats
    • ⚡ Fast processing
    • 💾 Voice history tracking

    **📱 Available Commands:**
    /on - Start bot & join voice chat
    /off - Stop bot completely
    /stop - Leave voice chat only
    /setgroup - Set your group chat
    /filter - Change voice effect
    /status - Check bot status
    /stats - Your usage statistics

    **⚡ Quick Setup:**
    1. Add me to your group as admin
    2. Use /setgroup with group link
    3. Use /on to activate
    4. Send voice notes in DM!

    📍 **Note:** Send voice notes in this DM only
    """
    
    # Create keyboard
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📢 Support", url="https://t.me/your_support"),
        InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/your_username")
    )
    
    await message.reply(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.message_handler(commands=['on'], chat_type=types.ChatType.PRIVATE)
async def on_command(message: types.Message):
    """Activate bot and join voice chat"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if not user_data:
        await message.reply("❌ Please use /start first!")
        return
    
    if user_data.get('is_banned'):
        await message.reply("🚫 Your account has been banned from using this bot.")
        return
    
    # Check if group is set
    if not user_data.get('group_id'):
        await message.reply(
            "❌ **No group configured!**\n\n"
            "Please set up your group first:\n"
            "1. Add me to your group\n"
            "2. Make me admin\n"
            "3. Use /setgroup with group link"
        )
        return
    
    # Check if already active
    if user_data.get('is_active'):
        await message.reply("✅ Bot is already active and in voice chat!")
        return
    
    # Start userbot if not started
    if not userbot.is_connected:
        start_msg = await message.reply("🚀 Starting UserBot...")
        success = await userbot.start()
        
        if not success:
            await start_msg.edit_text("❌ Failed to start UserBot. Check logs.")
            return
        
        await start_msg.edit_text("✅ UserBot started!")
        await asyncio.sleep(1)
    
    # Join voice chat
    joining_msg = await message.reply("🎧 Joining voice chat...")
    
    group_id = user_data['group_id']
    success = await userbot.join_voice_chat(user_id, group_id)
    
    if success:
        await db.set_user_active
