from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from config import Config

logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(Config.MONGO_URI)
            self.db = self.client[Config.DB_NAME]
            
            # Create indexes
            await self.db.users.create_index("user_id", unique=True)
            await self.db.groups.create_index("chat_id", unique=True)
            await self.db.voice_stats.create_index([("user_id", 1), ("date", 1)])
            
            logger.info("✅ Connected to MongoDB")
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("MongoDB disconnected")
    
    # ========== USER MANAGEMENT ==========
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        return await self.db.users.find_one({"user_id": user_id})
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Create new user"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "is_active": False,
            "is_banned": False,
            "voice_filter": "deep",
            "volume": 100,
            "group_id": None,
            "group_link": None,
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "total_voices": 0
        }
        
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": user_data},
            upsert=True
        )
        
        return user_data
    
    async def update_user_group(self, user_id: int, group_id: int, group_link: str):
        """Update user's group information"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "group_id": group_id,
                "group_link": group_link,
                "last_active": datetime.now()
            }}
        )
    
    async def set_user_active(self, user_id: int, active: bool):
        """Set user active/inactive"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "is_active": active,
                "last_active": datetime.now()
            }}
        )
    
    async def update_voice_filter(self, user_id: int, filter_name: str):
        """Update user's voice filter"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"voice_filter": filter_name}}
        )
    
    async def increment_voice_count(self, user_id: int):
        """Increment user's voice count"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"total_voices": 1}}
        )
    
    # ========== GROUP MANAGEMENT ==========
    async def add_group(self, chat_id: int, title: str, username: str = None):
        """Add or update group"""
        group_data = {
            "chat_id": chat_id,
            "title": title,
            "username": username,
            "member_count": 0,
            "is_active": True,
            "created_at": datetime.now(),
            "last_used": datetime.now()
        }
        
        await self.db.groups.update_one(
            {"chat_id": chat_id},
            {"$set": group_data},
            upsert=True
        )
    
    # ========== STATISTICS ==========
    async def add_voice_stat(self, user_id: int, duration: int, filter_used: str):
        """Add voice processing statistic"""
        stat_data = {
            "user_id": user_id,
            "date": datetime.now().date(),
            "duration": duration,
            "filter_used": filter_used,
            "timestamp": datetime.now()
        }
        
        await self.db.voice_stats.insert_one(stat_data)
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$user_id",
                "total_voices": {"$sum": 1},
                "total_duration": {"$sum": "$duration"},
                "filters_used": {"$addToSet": "$filter_used"}
            }}
        ]
        
        cursor = self.db.voice_stats.aggregate(pipeline)
        stats = await cursor.to_list(length=1)
        
        return stats[0] if stats else {
            "total_voices": 0,
            "total_duration": 0,
            "filters_used": []
        }
    
    # ========== ADMIN FUNCTIONS ==========
    async def get_all_users(self, skip: int = 0, limit: int = 100):
        """Get all users (admin only)"""
        cursor = self.db.users.find().sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=None)
    
    async def get_active_users_count(self) -> int:
        """Count active users"""
        return await self.db.users.count_documents({"is_active": True})
    
    async def get_total_voices_processed(self) -> int:
        """Get total voices processed"""
        pipeline = [
            {"$group": {
                "_id": None,
                "total": {"$sum": "$total_voices"}
            }}
        ]
        
        cursor = self.db.users.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        return result[0]["total"] if result else 0

# Global database instance
db = MongoDB()
