from typing import Dict, Any
import math
import time
from .game_config_loader import GameConfigLoader

class GameStateAnalyzer:
    """
    Analyzes game world state and computes strategic metrics for Simplex optimization.
    
    Metrics computed:
    - threat_level: Enemy offensive capability vs bot defensive capability
    - resource_efficiency: Gold generation rate based on collector count
    - positional_advantage: Strategic positioning (scouts, defenses, proximity to resources)
    """

    P1_STRUCTURES_RANGE = range(0, 1000)
    P1_ATTACKERS_RANGE = range(1000, 3000)
    P1_COLLECTORS_RANGE = range(3000, 5000)

    P2_STRUCTURES_RANGE = range(5000, 6000)
    P2_ATTACKERS_RANGE = range(6000, 8000)
    P2_COLLECTORS_RANGE = range(8000, 10000)

    MAP_SIZE = 5000

    def __init__(self, player_id: int):
        """
        Initialize analyzer for a specific player
        
        Args:
            player_id: 1 or 2, identifying which player this bot controls
        """
        self.player_id = player_id
        self.enemy_id = 2 if player_id == 1 else 1

        # Load game constants from configuration files (single source of truth)
        self.config = GameConfigLoader()
        self.ATTACKER_DAMAGE = self.config.get_attacker_damage()
        self.UNIT_HP = self.config.get_unit_hp("attacker")
        self.COLLECTOR_HP = self.config.get_unit_hp("collector")
        self.MAX_COLLECTORS = self.config.get_max_collectors_per_decision()
        self.MAX_GOLD = 500  # Initial gold per player (not in combat_stats, game balance constant)
        
        # Game start tracking (set on first analyze() call)
        self.game_start_time = None
        self.initial_gold_per_player = 500

    

    def _count_units_by_type(self, game_world, player_id: int) -> tuple:
        """
        Count attacker and collector units for a player
        
        Returns:
            (attacker_count, collector_count)
        """
        attackers = 0
        collectors = 0

        for unit_id in game_world.units:
            owner = game_world.get_owner_from_id(unit_id)

            if owner != player_id:
                continue

            if unit_id in self.P1_ATTACKERS_RANGE or unit_id in self.P2_ATTACKERS_RANGE:
                attackers += 1
            elif unit_id in self.P1_COLLECTORS_RANGE or unit_id in self.P2_COLLECTORS_RANGE:
                collectors += 1
        return attackers, collectors

    def _calculate_average_position(self, game_world, player_id: int) -> tuple:
            """
            Calculate center of mass for all player units
            
            Returns:
                (center_x, center_y) or (None, None) if no units
            """
            total_x = 0
            total_y = 0
            count = 0

            for unit_id, unit in game_world.units.items():
                owner = game_world.get_owner_from_id(unit_id)
                
                if owner != player_id:
                    continue

                total_x += unit.x
                total_y += unit.y
                count += 1

            if count == 0:
                return None, None

            return total_x / count, total_y / count
    
    def _distance_to_enemy_base(self, game_world, player_id: int) -> float:
            """
            Calculate average distance from player's units to enemy base
            
            Assumes:
            - Player 1 base at (300, 4700)
            - Player 2 base at (4700, 300)
            
            Lower distance = more aggressive positioning
            """
            player_center_x, player_center_y = self._calculate_average_position(game_world, player_id)

            if player_center_x is None:
                return float('inf')  # No units = infinite distance

            # Enemy base positions
            if self.enemy_id == 1:
                enemy_base_x, enemy_base_y = 300, 4700
            else:
                enemy_base_x, enemy_base_y = 4700, 300

            # Euclidean distance
            distance = math.sqrt(
                (player_center_x - enemy_base_x) ** 2 +
                (player_center_y - enemy_base_y) ** 2
            )

            return distance
    
    def calculate_threat_level(self, game_world) -> float:
            """
            Calculate threat level: enemy offensive vs bot defensive capability
            
            Formula: threat = (enemy_attackers * attack_damage) / (bot_attackers + bot_hp_buffer)
            
            Returns:
                Float in range [0, 1] where:
                - 0 = No threat (bot can defend easily)
                - 1 = Maximum threat (bot in danger of losing)
            """
            bot_attackers, bot_collectors = self._count_units_by_type(
                game_world, 
                self.player_id
            )

            enemy_attackers, enemy_collectors = self._count_units_by_type(
                game_world,
                self.enemy_id
            )

            # Threat calculation
            enemy_threat = enemy_attackers * self.ATTACKER_DAMAGE
            bot_defense = (bot_attackers * self.UNIT_HP) + (bot_collectors * self.UNIT_HP * 0.5)

            if bot_defense == 0:
                return 1.0  # Maximum threat if no defense

            threat = min(1.0, enemy_threat / bot_defense)
            return threat
    
    def calculate_resource_efficiency(self, game_world, current_gold: int) -> float:
            """
            Calculate resource generation efficiency
            
            Based on:
            - Number of active collectors
            - Current gold reserves
            
            Returns:
                Float in range [0, 1] where:
                - 0 = No resource generation (no collectors)
                - 1 = Optimal efficiency (many collectors with good gold)
            """
            bot_attackers, bot_collectors = self._count_units_by_type(
                game_world,
                self.player_id
            )

            collector_efficiency = min(1.0, bot_collectors / self.MAX_COLLECTORS)

            gold_efficiency = min(1.0, current_gold / self.MAX_GOLD)

            # Combined: average of both factors
            efficiency = (collector_efficiency + gold_efficiency) / 2

            return efficiency
    
    def calculate_positional_advantage(self, game_world) -> float:
            """
            Calculate positional advantage through strategic positioning
            
            Strategy:
            1. Proximity to enemy base (scouts/invasion)
            2. Unit concentration vs dispersion
            3. Unit superiority (attackers ratio)
            
            Returns:
                Float in range [-1, 1] where:
                - -1 = Complete disadvantage (units scattered, far from enemy)
                - 0 = Neutral positioning
                - 1 = Strong advantage (units concentrated, close to enemy)
            """
            bot_attackers, bot_collectors = self._count_units_by_type(
                game_world,
                self.player_id
            )

            enemy_attackers, enemy_collectors = self._count_units_by_type(
                game_world,
                self.enemy_id
            )

            if bot_attackers == 0:
                return -1.0  # No attackers = disadvantage

            # Calculate distance to enemy base
            distance_to_enemy = self._distance_to_enemy_base(game_world, self.player_id)

            # Normalize distance: 0 to 5000 pixels max
            normalized_distance = min(1.0, distance_to_enemy / self.MAP_SIZE)

            # Closer to enemy = higher advantage (inverted: 1 - normalized_distance)
            proximity_advantage = 1.0 - normalized_distance

            # Unit superiority: more attackers = advantage
            unit_ratio = min(1.0, bot_attackers / max(1, enemy_attackers))

            # Combined advantage: 70% proximity, 30% unit ratio
            advantage = (0.7 * proximity_advantage) + (0.3 * unit_ratio)

            # Scale to [-1, 1]
            positional_advantage = (2 * advantage) - 1.0

            return positional_advantage
    
    def _calculate_game_phase(self, elapsed_seconds: float, total_units: int, initial_gold: int, current_gold: int) -> str:
        """
        Determine game phase based on elapsed time, unit count, and resource spent
        
        Phases:
        - "early": First 0-30 seconds, <8 units total
          Strategy: Build economy, avoid fights, focus on collectors
        - "mid": 30-90 seconds, 8-20 units total
          Strategy: Balanced offense/defense, start skirmishing
        - "late": 90+ seconds, 20+ units total
          Strategy: Full army deployment, base pressure, decide winner
        
        Args:
            elapsed_seconds: Time since game start
            total_units: Total bot + enemy units currently alive
            initial_gold: Starting gold (500)
            current_gold: Current gold remaining
        
        Returns:
            Phase string: "early", "mid", or "late"
        """
        gold_spent = initial_gold - current_gold
        
        # Early phase: first 30 seconds OR fewer than 8 units
        if elapsed_seconds < 30 or total_units < 8:
            return "early"
        
        # Late phase: 90+ seconds OR 20+ units
        if elapsed_seconds > 90 or total_units >= 20:
            return "late"
        
        # Mid phase: everything in between
        return "mid"
    
    def _detect_opponent_play_style(self, enemy_attackers: int, enemy_collectors: int) -> str:
        """
        Detect opponent's economic vs aggressive strategy
        
        Strategies:
        - "rush": Many attackers (>60% of total), few collectors
          Counter: Build defensive units early, focus on resource accumulation
        - "eco": Many collectors (>60% of total), few attackers
          Counter: Build army and attack before they become overwhelming
        - "mixed": Balanced army and economy
          Counter: Adapt dynamically
        
        Args:
            enemy_attackers: Number of enemy attacking units
            enemy_collectors: Number of enemy collecting units
        
        Returns:
            Style string: "rush", "eco", or "mixed"
        """
        total = enemy_attackers + enemy_collectors
        
        if total == 0:
            return "mixed"  # No units yet
        
        attacker_ratio = enemy_attackers / total
        
        if attacker_ratio > 0.6:
            return "rush"  # Opponent is aggressive
        elif attacker_ratio < 0.4:  # Collectors are >60%
            return "eco"    # Opponent is economic
        else:
            return "mixed"  # Balanced

    def analyze(self, game_world, current_gold: int, elapsed_time_ms: float = None) -> Dict[str, Any]:
        """
        Comprehensive game state analysis
        
        Args:
            game_world: GameWorld instance
            current_gold: Current gold amount (from GameScreen.player_gold)
            elapsed_time_ms: Time in milliseconds since game start (optional, for testing)
        
        Returns:
            Dictionary with all strategic metrics for Simplex optimizer
        """
        # Initialize game start time on first call
        if self.game_start_time is None:
            self.game_start_time = time.time() * 1000  # Convert to milliseconds
        
        # Calculate elapsed time
        if elapsed_time_ms is None:
            elapsed_time_ms = (time.time() * 1000) - self.game_start_time
        elapsed_seconds = elapsed_time_ms / 1000.0
        
        threat = self.calculate_threat_level(game_world)
        resource = self.calculate_resource_efficiency(game_world, current_gold)
        position = self.calculate_positional_advantage(game_world)

        # Unit counts
        bot_attackers, bot_collectors = self._count_units_by_type(
            game_world,
            self.player_id
        )

        enemy_attackers, enemy_collectors = self._count_units_by_type(
            game_world,
            self.enemy_id
        )

        bot_power = bot_attackers + (0.5 * bot_collectors)
        enemy_power = enemy_attackers + (0.5 * enemy_collectors)
        if bot_power == 0 and enemy_power == 0:
            army_balance = 0.0
        else:
            army_balance = (bot_power - enemy_power) / max(bot_power, enemy_power)
            army_balance = max(-1.0, min(1.0, army_balance))
        
        # Calculate game phase
        total_units = (bot_attackers + bot_collectors) + (enemy_attackers + enemy_collectors)
        game_phase = self._calculate_game_phase(
            elapsed_seconds, 
            total_units, 
            self.initial_gold_per_player, 
            current_gold
        )
        
        # Detect opponent play style
        opponent_style = self._detect_opponent_play_style(enemy_attackers, enemy_collectors)

        state = {
            # Metrics for Simplex objective function
            "threat_level": threat,
            "resource_efficiency": resource,
            "positional_advantage": position,
            "army_balance": army_balance,

            # Unit counts
            "bot_attackers": bot_attackers,
            "bot_collectors": bot_collectors,
            "enemy_attackers": enemy_attackers,
            "enemy_collectors": enemy_collectors,

            # Resources
            "current_gold": current_gold,

            # Raw data for advanced decisions
            "total_bot_units": bot_attackers + bot_collectors,
            "total_enemy_units": enemy_attackers + enemy_collectors,
            
            # Game phase and opponent modeling
            "game_phase": game_phase,
            "elapsed_seconds": elapsed_seconds,
            "opponent_play_style": opponent_style,
        }

        return state