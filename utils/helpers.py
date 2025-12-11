import time
import asyncio
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Timer:
    """Simple timer for performance measurement"""
    
    def __init__(self):
        self.start_time = None
        
    def start(self):
        self.start_time = time.time()
        
    def stop(self):
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.start_time = None
            return elapsed
        return 0

def format_time(seconds: float) -> str:
    """Format seconds to human readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def validate_telegram_link(link: str) -> Optional[str]:
    """Validate and extract username from Telegram link"""
    link = link.strip()
    
    # Remove https://
    if link.startswith("https://"):
        link = link[8:]
    
    # Remove t.me/
    if link.startswith("t.me/"):
        link = link[5:]
    
    # Remove @
    if link.startswith("@"):
        link = link[1:]
    
    # Validate username
    if not link or len(link) > 32:
        return None
    
    # Check for invalid characters
    if not all(c.isalnum() or c == '_' for c in link):
        return None
    
    return link

async def rate_limit(wait_time: float = 1.0):
    """Simple rate limiting"""
    await asyncio.sleep(wait_time)

def create_progress_bar(percentage: float, width: int = 20) -> str:
    """Create a text progress bar"""
    filled = int(width * percentage / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {percentage:.1f}%"
