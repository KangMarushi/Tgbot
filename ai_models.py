import logging
from typing import Dict, Optional
from config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

class AIModelManager:
    def __init__(self):
        # Define AI models for different tiers
        self.models = {
            "free": {
                "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                "name": "Venice",
                "description": "Good quality responses for free characters",
                "max_tokens": 2000,
                "temperature": 0.7
            },
            "premium": {
                "model": "mistralai/mistral-nemo:free",
                "name": "Mistral",
                "description": "High-quality responses for premium characters",
                "max_tokens": 3000,
                "temperature": 0.8
            },
            "ultra_premium": {
                "model": "gryphe/mythomax-l2-13b",
                "name": "Mythomax",
                "description": "Ultra-high quality responses for top-tier characters",
                "max_tokens": 5000,
                "temperature": 0.9
            }
        }
        
        # Character tier mapping based on price
        self.character_tiers = {
            "free": [0],  # Free characters
            "premium": [70, 80, 85, 90, 100, 110],  # Mid-tier premium
            "ultra_premium": [120, 150]  # Top-tier premium
        }
    
    def get_model_for_character(self, character_price: int) -> Dict:
        """Get AI model configuration based on character price"""
        for tier, prices in self.character_tiers.items():
            if character_price in prices:
                return self.models[tier]
        
        # Default to premium if price not found
        logger.warning(f"Character price {character_price} not found in tiers, defaulting to premium")
        return self.models["premium"]
    
    def get_model_info(self, character_price: int) -> Dict:
        """Get model information for display purposes"""
        model_config = self.get_model_for_character(character_price)
        return {
            "name": model_config["name"],
            "description": model_config["description"],
            "tier": self._get_tier_name(character_price)
        }
    
    def _get_tier_name(self, character_price: int) -> str:
        """Get tier name for a character price"""
        for tier, prices in self.character_tiers.items():
            if character_price in prices:
                return tier.replace("_", " ").title()
        return "Premium"
    
    def get_character_tier_benefits(self, character_price: int) -> str:
        """Get benefits description for character tier"""
        tier = self._get_tier_name(character_price)
        model_config = self.get_model_for_character(character_price)
        
        benefits = {
            "Free": "🆓 Basic AI responses",
            "Premium": "💫 Enhanced AI with better understanding",
            "Ultra Premium": "🌟 Ultra-high quality AI with advanced capabilities"
        }
        
        return f"{tier} Tier: {benefits.get(tier, 'Enhanced AI')}"

# Global AI model manager instance
ai_model_manager = AIModelManager()
