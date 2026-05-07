import json
import os
from typing import Dict, Any, Optional

class GameConfigLoader:
    """
    Unified loader for game configuration files:
    - combat_stats.json: Game mechanics (unit stats, damage, HP, etc)
    - bot_ai_config.json: Bot behavior (constraints, decision intervals, weights)
    
    Ensures single source of truth for game constants.
    Usage: 
        config = GameConfigLoader()
        attacker_damage = config.get_attacker_damage()
        unit_hp = config.get_unit_hp("attacker")
        max_collectors = config.get_bot_constraint("max_collectors_per_decision")
    """

    def __init__(self):
        """Initialize by loading all configuration files"""
        self.combat_stats = self._load_json("combat_stats.json")
        self.bot_config = self._load_json("bot_ai_config.json", is_bot_config=True)
        self.arcade_config = self._load_json("arcade_config.json")

    def _load_json(self, filename: str, is_bot_config: bool = False) -> Dict[str, Any]:
            """
            Load JSON configuration file
            
            Args:
                filename: Name of the JSON file to load
                is_bot_config: If True, looks in config/ folder; else also checks current folder
            
            Returns:
                Dictionary with JSON contents
            
            Raises:
                FileNotFoundError: If file doesn't exist
                json.JSONDecodeError: If JSON is malformed
            """
            # Path resolution: look in src/config/ folder
            config_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..",
                "config",
                filename
            )

            if not os.path.exists(config_path):
                raise FileNotFoundError(
                    f"Config file '{filename}' not found at: {config_path}\n"
                    f"Expected location: src/config/{filename}"
                )

            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Malformed JSON in {filename}: {e.msg}",
                    e.doc,
                    e.pos
                )
    
  # ===== COMBAT STATS ACCESSORS =====
    
    def get_unit_hp(self, unit_type: str) -> int:
        """
        Get unit health points from combat_stats.json
        
        Args:
            unit_type: "attacker", "collector", or "base"
        
        Returns:
            HP value (typically 100 for units, 1500 for base)
        """
        return self.combat_stats["units"][unit_type]["hp"]

    def get_attacker_damage(self) -> int:
        """Get attacker weapon damage from combat_stats.json"""
        return self.combat_stats["units"]["attacker"]["atack"]  # Note: typo in JSON is "atack"

    def get_unit_stat(self, unit_type: str, stat_name: str) -> Any:
        """
        Generic accessor for any unit stat from combat_stats.json
        
        Args:
            unit_type: "attacker", "collector", or "base"
            stat_name: "hp", "attack", "defense", "range", "speed", etc
        
        Returns:
            The stat value
        """
        try:
            return self.combat_stats["units"][unit_type][stat_name]
        except KeyError as e:
            raise KeyError(
                f"Stat '{stat_name}' not found for unit type '{unit_type}'. "
                f"Available: {list(self.combat_stats['units'][unit_type].keys())}"
            )
    
    # ===== BOT CONFIG ACCESSORS =====

    def get_bot_constraint(self, constraint_name: str) -> Any:
        """
        Get Simplex constraint from bot_ai_config.json
        
        Args:
            constraint_name: "max_units_per_player", "max_attackers_per_decision", etc
        
        Returns:
            The constraint value
        """
        try:
            return self.bot_config["simplex_constraints"][constraint_name]
        except KeyError:
            available = list(self.bot_config["simplex_constraints"].keys())
            raise KeyError(
                f"Constraint '{constraint_name}' not found. Available: {available}"
            )

    def get_max_units_per_player(self) -> int:
        """Convenience: Get max units constraint (typically 50)"""
        return self.get_bot_constraint("max_units_per_player")

    def get_max_collectors_per_decision(self) -> int:
        """Convenience: Get max collectors to buy per decision (typically 10)"""
        return self.get_bot_constraint("max_collectors_per_decision")

    def get_max_attackers_per_decision(self) -> int:
        """Convenience: Get max attackers to buy per decision (typically 10)"""
        return self.get_bot_constraint("max_attackers_per_decision")

    # ===== ARCADE CONFIG ACCESSORS =====

    def get_arcade_param(self, param_name: str) -> Any:
        """
        Get any arcade mode parameter from arcade_config.json

        Args:
            param_name: Key under "arcade_mode" (e.g. "starting_gold", "bomb_cost")

        Returns:
            The parameter value
        """
        try:
            return self.arcade_config["arcade_mode"][param_name]
        except KeyError as e:
            available = list(self.arcade_config.get("arcade_mode", {}).keys())
            raise KeyError(
                f"Arcade param '{param_name}' not found. Available: {available}"
            )

    def get_starting_gold(self) -> int:
        """Get starting gold for arcade mode"""
        return self.get_arcade_param("starting_gold")

    def get_bomb_cost(self) -> int:
        """Get bomb purchase cost in arcade mode"""
        return self.get_arcade_param("bomb_cost")

    def get_arcade_attacker_cost(self) -> int:
        """Get attacker purchase cost in arcade mode"""
        return self.get_arcade_param("attacker_cost")

    def get_bomb_hp(self) -> int:
        """Get bomb hit points in arcade mode"""
        return self.get_arcade_param("bomb_hp")

    def get_kill_gold_unit(self) -> int:
        """Get gold rewarded for killing an enemy unit"""
        return self.get_arcade_param("kill_gold_per_unit")

    def get_kill_gold_bomb(self) -> int:
        """Get gold rewarded for destroying an enemy bomb"""
        return self.get_arcade_param("kill_gold_per_bomb")

    def get_auto_spawn_interval_ms(self) -> int:
        """Get auto-spawn interval in milliseconds"""
        return self.get_arcade_param("auto_spawn_interval_ms")

    def get_initial_attackers(self) -> int:
        """Get number of attackers each player starts with"""
        return self.get_arcade_param("initial_attackers")

    def get_game_duration_seconds(self) -> int:
        """Get arcade mode game duration in seconds"""
        return self.get_arcade_param("game_duration_seconds")

    def get_explosion_radius(self) -> int:
        """Get bomb explosion radius in units"""
        return self.get_arcade_param("explosion_radius")

    def get_base_immunity_to_attackers(self) -> bool:
        """Check if bases are immune to attacker direct damage in arcade mode"""
        return self.get_arcade_param("base_immunity_to_attackers")

    def get_difficulty_params(self, difficulty: str) -> Dict[str, Any]:
        """
        Get all parameters for a specific difficulty level
        
        Args:
            difficulty: "EASY", "MEDIUM", or "HARD"
        
        Returns:
            Dictionary with all parameters for that difficulty
        """
        try:
            return self.bot_config["difficulties"][difficulty]
        except KeyError:
            available = list(self.bot_config["difficulties"].keys())
            raise KeyError(f"Difficulty '{difficulty}' not found. Available: {available}")
