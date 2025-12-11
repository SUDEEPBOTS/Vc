from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.phone import JoinGroupCallRequest, LeaveGroupCallRequest
import asyncio
import logging
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class UserBotManager:
    """
    ✅ Telethon UserBot Manager
    Uses Telethon session string from .env
    """
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.is_connected: bool = False
        self.active_chats: Dict[int, int] = {}  # user_id: chat_id
        self.user_clients: Dict[int, TelegramClient] = {}
        
    async def start(self) -> bool:
        """Start the main userbot using session string from .env"""
        try:
            if not Config.SESSION_STRING:
                logger.error("❌ No session string in .env")
                return False
            
            logger.info("🚀 Starting Telethon UserBot...")
            
            # ✅ Create Telethon client with StringSession
            self.client = TelegramClient(
                StringSession(Config.SESSION_STRING),
                Config.API_ID,
                Config.API_HASH
            )
            
            # Set up event handlers
            self.client.add_event_handler(self._on_message, events.NewMessage)
            
            # Connect
            await self.client.start()
            
            # Get bot info
            me = await self.client.get_me()
            logger.info(f"✅ UserBot started as @{me.username} (ID: {me.id})")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start UserBot: {e}")
            return False
    
    async def _on_message(self, event: events.NewMessage.Event):
        """Handle incoming messages"""
        try:
            if event.is_private:
                logger.debug(f"DM from {event.sender_id}: {event.message.text}")
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
    
    async def join_voice_chat(self, user_id: int, chat_id: int) -> bool:
        """Join voice chat in a group"""
        try:
            if not self.client or not self.is_connected:
                logger.error("UserBot not connected")
                return False
            
            # Get the chat entity
            try:
                chat = await self.client.get_entity(chat_id)
            except Exception as e:
                logger.error(f"Could not get chat entity: {e}")
                return False
            
            # Try to join voice chat
            try:
                # Method 1: Using Telethon's phone functions
                call = await self.client(functions.phone.JoinGroupCallRequest(
                    peer=chat,
                    muted=False,
                    video_stopped=False
                ))
                
                logger.info(f"✅ Joined voice chat in {chat_id}")
                self.active_chats[user_id] = chat_id
                return True
                
            except Exception as e:
                logger.warning(f"Method 1 failed: {e}")
                
                # Method 2: Try alternative method
                try:
                    await self.client.send_message(chat, "!join")
                    await asyncio.sleep(2)
                    
                    logger.info(f"✅ Joined voice chat (method 2) in {chat_id}")
                    self.active_chats[user_id] = chat_id
                    return True
                    
                except Exception as e2:
                    logger.error(f"All methods failed: {e2}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error joining voice chat: {e}")
            return False
    
    async def leave_voice_chat(self, user_id: int) -> bool:
        """Leave voice chat"""
        try:
            if user_id not in self.active_chats:
                return True
            
            chat_id = self.active_chats[user_id]
            
            if self.client and self.is_connected:
                try:
                    chat = await self.client.get_entity(chat_id)
                    
                    # Try to leave
                    try:
                        await self.client(functions.phone.LeaveGroupCallRequest(
                            call=await self._get_active_call(chat_id),
                            source=0
                        ))
                    except:
                        await self.client.send_message(chat, "!leave")
                    
                    logger.info(f"✅ Left voice chat {chat_id}")
                    
                except Exception as e:
                    logger.error(f"Error leaving VC: {e}")
            
            # Remove from active chats
            if user_id in self.active_chats:
                del self.active_chats[user_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Error in leave_voice_chat: {e}")
            return False
    
    async def _get_active_call(self, chat_id: int):
        """Get active call in chat"""
        try:
            result = await self.client(functions.phone.GetGroupCallRequest(
                call=chat_id
            ))
            return result.call
        except:
            return None
    
    async def send_voice(self, chat_id: int, voice_path: str, caption: str = "") -> bool:
        """Send voice message to chat"""
        try:
            if not self.client or not self.is_connected:
                return False
            
            chat = await self.client.get_entity(chat_id)
            
            # Send voice as voice note
            await self.client.send_file(
                chat,
                voice_path,
                voice_note=True,
                caption=caption[:200] if caption else "",
                supports_streaming=True
            )
            
            logger.info(f"✅ Voice sent to {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending voice: {e}")
            return False
    
    async def stop(self):
        """Stop the userbot"""
        try:
            # Leave all voice chats
            for user_id in list(self.active_chats.keys()):
                await self.leave_voice_chat(user_id)
            
            # Disconnect client
            if self.client and self.is_connected:
                await self.client.disconnect()
                self.is_connected = False
            
            logger.info("✅ UserBot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping UserBot: {e}")

# Global userbot manager instance
userbot = UserBotManager()
