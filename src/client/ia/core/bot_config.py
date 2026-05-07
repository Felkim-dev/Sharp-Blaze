import json
import os
from typing import Dict, Any, Optional

class BotConfig:
    """
    Loads and manages AI bot configuration from bot_ai_config.json
    Provides difficulty-specific parameters for decision making
    """

    def __init__(self):
        """Initialize by loading configuration from JSON file"""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..","..",
            "config",
            "bot_ai_config.json"
        )

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Bot config not found at: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def get_difficulty(self, difficulty: str) -> Optional[Dict[str, Any]]:
        """Get configuration parameters for a specific difficulty level"""
        return self.config.get('difficulties', {}).get(difficulty)

    def get_constraints(self) -> Dict[str, Any]:
        """Get Simplex constraints (max_units_per_player, etc)"""
        return self.config.get('simplex_constraints', {})

    def get_max_units_per_player(self) -> int:
        """Get maximum units constraint - used in Simplex"""
        return self.config.get('simplex_constraints', {}).get('max_units_per_player', 50)
