from typing import Dict, Any
import math

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
            elif unit_id in self.P1_COLLECTORS_RANGE or unit_id in self.P1_COLLECTORS_RANGE:
                collectors += 1
        return attackers, collectors