import json
import sqlite3
import logging
from typing import List, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from ai_models import ai_model_manager

logger = logging.getLogger(__name__)

class CharacterManager:
    def __init__(self, db_path: str = "sextbot.db"):
        self.db_path = db_path
        self.characters = self.load_characters()
        self.init_database()
    
    def load_characters(self) -> List[Dict]:
        """Load characters from JSON file"""
        try:
            with open("characters.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("characters.json not found")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing characters.json: {e}")
            return []
    
    def init_database(self):
        """Initialize database tables for character unlocks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for user character unlocks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_unlocks (
                user_id INTEGER,
                character_id TEXT,
                unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, character_id)
            )
        """)
        
        # Table for user's active character
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_active_character (
                user_id INTEGER PRIMARY KEY,
                character_id TEXT,
                set_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table for Telegram Stars transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stars_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                character_id TEXT,
                stars_amount INTEGER,
                telegram_payment_charge_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_character_by_id(self, character_id: str) -> Optional[Dict]:
        """Get character by ID"""
        for char in self.characters:
            if char["id"] == character_id:
                return char
        return None
    
    def is_character_unlocked(self, user_id: int, character_id: str) -> bool:
        """Check if user has unlocked a character"""
        char = self.get_character_by_id(character_id)
        if not char:
            return False
        
        # Free characters are always unlocked
        if not char["is_locked"]:
            return True
        
        # Check database for paid unlocks
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM character_unlocks WHERE user_id = ? AND character_id = ?",
            (user_id, character_id)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def unlock_character(self, user_id: int, character_id: str) -> bool:
        """Unlock a character for a user"""
        char = self.get_character_by_id(character_id)
        if not char:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO character_unlocks (user_id, character_id) VALUES (?, ?)",
                (user_id, character_id)
            )
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            logger.error(f"Error unlocking character: {e}")
            conn.close()
            return False
    
    def set_active_character(self, user_id: int, character_id: str) -> bool:
        """Set user's active character"""
        if not self.is_character_unlocked(user_id, character_id):
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO user_active_character (user_id, character_id) VALUES (?, ?)",
                (user_id, character_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error setting active character: {e}")
            conn.close()
            return False
    
    def get_active_character(self, user_id: int) -> Optional[Dict]:
        """Get user's active character"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT character_id FROM user_active_character WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return self.get_character_by_id(result[0])
        return None
    
    def get_character_prompt(self, user_id: int) -> str:
        """Get the prompt for user's active character"""
        active_char = self.get_active_character(user_id)
        if active_char:
            return active_char["prompt"]
        return "You are a friendly AI assistant."
    
    def create_characters_keyboard(self, user_id: int, page: int = 0) -> InlineKeyboardMarkup:
        """Create keyboard for character selection"""
        chars_per_page = 3
        start_idx = page * chars_per_page
        end_idx = start_idx + chars_per_page
        current_chars = self.characters[start_idx:end_idx]
        
        keyboard = []
        
        for char in current_chars:
            is_unlocked = self.is_character_unlocked(user_id, char["id"])
            active_char = self.get_active_character(user_id)
            is_active = active_char and active_char["id"] == char["id"]
            
            # Create button text
            status_emoji = "✅" if is_unlocked else "🔒"
            active_emoji = "👑" if is_active else ""
            button_text = f"{status_emoji} {char['name']} ({char['role']}) {active_emoji}"
            
            if is_unlocked:
                # Character is unlocked - show select button
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"select_char:{char['id']}"
                    )
                ])
            else:
                # Character is locked - show unlock button
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"unlock_char:{char['id']}"
                    )
                ])
        
        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data=f"char_page:{page-1}")
            )
        if end_idx < len(self.characters):
            nav_buttons.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"char_page:{page+1}")
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Close button
        keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close_characters")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_character_message(self, user_id: int, page: int = 0) -> str:
        """Create message for character selection"""
        chars_per_page = 3
        start_idx = page * chars_per_page
        end_idx = start_idx + chars_per_page
        current_chars = self.characters[start_idx:end_idx]
        
        message = "🌟 **Choose Your AI Girlfriend** 🌟\n\n"
        message += f"Page {page + 1} of {(len(self.characters) + chars_per_page - 1) // chars_per_page}\n\n"
        
        for char in current_chars:
            is_unlocked = self.is_character_unlocked(user_id, char["id"])
            active_char = self.get_active_character(user_id)
            is_active = active_char and active_char["id"] == char["id"]
            
            status_emoji = "✅" if is_unlocked else "🔒"
            active_emoji = "👑" if is_active else ""
            price_text = f"💫 {char['price_stars']} Stars" if char['is_locked'] else "🆓 Free"
            
            # Get AI model tier benefits
            ai_benefits = ai_model_manager.get_character_tier_benefits(char['price_stars'])
            
            message += f"{status_emoji} **{char['name']}** ({char['age']})\n"
            message += f"🎭 {char['role']}\n"
            message += f"📍 {char['region']}\n"
            message += f"💬 {char['language']}\n"
            message += f"💰 {price_text} {active_emoji}\n"
            message += f"🤖 {ai_benefits}\n"
            message += f"📝 {char['description']}\n\n"
        
        return message

# Global character manager instance
character_manager = CharacterManager()
