import logging
import sqlite3
from typing import Optional, Dict
from telegram import LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class StarsPaymentManager:
    def __init__(self, db_path: str = "sextbot.db"):
        self.db_path = db_path
        # For digital goods, provider_token should be empty string according to Telegram docs
        self.payment_token = ""  # Empty string for digital goods
    
    def create_stars_invoice(self, user_id: int, character_id: str, character_name: str, stars_amount: int) -> Optional[Dict]:
        """Create a Telegram Stars invoice for character unlock (digital goods)"""
        try:
            title = f"Unlock {character_name}"
            description = f"Unlock {character_name} for unlimited chat access - Digital Service"
            
            # Create labeled price for Stars (amount in actual Stars)
            # For Telegram Stars (XTR), use the actual Stars amount
            prices = [LabeledPrice(f"{character_name} Unlock", stars_amount)]
            
            # Create invoice payload for tracking
            payload = f"unlock_character:{user_id}:{character_id}"
            
            # For digital goods, currency must be "XTR" (Telegram Stars)
            currency = "XTR"
            
            # For digital goods, provider_token should be empty string
            provider_token = ""
            
            return {
                "title": title,
                "description": description,
                "payload": payload,
                "provider_token": provider_token,  # Empty for digital goods
                "currency": currency,  # Must be "XTR" for Stars
                "prices": prices,
                "start_parameter": f"unlock_{character_id}",
                "need_name": False,
                "need_phone_number": False,
                "need_email": False,
                "need_shipping_address": False,
                "send_phone_number_to_provider": False,
                "send_email_to_provider": False,
                "is_flexible": False,
                "photo_url": None,  # Optional: Add character image URL here
                "photo_width": None,
                "photo_height": None,
                "photo_size": None
            }
        except Exception as e:
            logger.error(f"Error creating Stars invoice: {e}")
            return None
    
    def record_transaction(self, user_id: int, character_id: str, stars_amount: int, 
                          telegram_payment_charge_id: str) -> bool:
        """Record a Stars transaction in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO stars_transactions 
                (user_id, character_id, stars_amount, telegram_payment_charge_id, status)
                VALUES (?, ?, ?, ?, 'completed')
            """, (user_id, character_id, stars_amount, telegram_payment_charge_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Transaction recorded: User {user_id} unlocked {character_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording transaction: {e}")
            conn.close()
            return False
    
    def get_transaction_status(self, telegram_payment_charge_id: str) -> Optional[str]:
        """Get transaction status by payment charge ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT status FROM stars_transactions WHERE telegram_payment_charge_id = ?",
            (telegram_payment_charge_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def create_unlock_keyboard(self, character_id: str, character_name: str, stars_amount: int) -> InlineKeyboardMarkup:
        """Create keyboard for character unlock"""
        keyboard = [
            [InlineKeyboardButton(
                f"💫 Unlock {character_name} ({stars_amount} Stars)",
                callback_data=f"pay_stars:{character_id}"
            )],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_unlock")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def validate_pre_checkout(self, pre_checkout_query) -> bool:
        """Validate pre-checkout query for digital goods"""
        try:
            # Check if the order can be processed
            # For digital goods, we can always process the order
            # Add any business logic validation here
            
            # Log the pre-checkout for debugging
            logger.info(f"Pre-checkout validation: User {pre_checkout_query.from_user.id}, "
                       f"Amount: {pre_checkout_query.total_amount}, "
                       f"Currency: {pre_checkout_query.currency}")
            
            # Validate currency is XTR (Telegram Stars)
            if pre_checkout_query.currency != "XTR":
                logger.error(f"Invalid currency: {pre_checkout_query.currency}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating pre-checkout: {e}")
            return False
    
    def process_successful_payment(self, successful_payment) -> Dict:
        """Process successful payment and extract relevant information"""
        try:
            # Parse payload to get character info
            payload_parts = successful_payment.invoice_payload.split(":")
            
            if len(payload_parts) == 3 and payload_parts[0] == "unlock_character":
                user_id = int(payload_parts[1])
                character_id = payload_parts[2]
                
                return {
                    "user_id": user_id,
                    "character_id": character_id,
                    "telegram_payment_charge_id": successful_payment.telegram_payment_charge_id,
                    "total_amount": successful_payment.total_amount,
                    "currency": successful_payment.currency,
                    "success": True
                }
            else:
                logger.error(f"Invalid payment payload: {successful_payment.invoice_payload}")
                return {"success": False, "error": "Invalid payload"}
                
        except Exception as e:
            logger.error(f"Error processing successful payment: {e}")
            return {"success": False, "error": str(e)}

# Global Stars payment manager instance
stars_payment_manager = StarsPaymentManager()
