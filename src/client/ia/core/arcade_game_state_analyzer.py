from typing import Dict, Any
import math

class ArcadeGameStateAnalyzer:

    P1_ATTACKERS_RANGE = range(1000, 3000)
    P2_ATTACKERS_RANGE = range(6000, 8000)

    P1_BOMB_RANGE = range(12000, 13000)
    P2_BOMB_RANGE = range(13000, 14000)

    BASE_POSITIONS = {
        1: (300, 4700),
        2: (4700, 300),
    }

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.enemy_id = 2 if player_id == 1 else 1

    def _count_attackers(self, game_world, player_id: int) -> int:
        count = 0
        target_range = self.P1_ATTACKERS_RANGE if player_id == 1 else self.P2_ATTACKERS_RANGE
        for unit_id in game_world.units:
            if unit_id in target_range and game_world.get_owner_from_id(unit_id) == player_id:
                count += 1
        return count

    def _get_bomb_positions(self, game_world, player_id: int):
        target_range = self.P1_BOMB_RANGE if player_id == 1 else self.P2_BOMB_RANGE
        bombs = []
        for unit_id, unit in game_world.units.items():
            if unit_id in target_range:
                bombs.append((unit_id, unit.x, unit.y))
        return bombs

    def _distance(self, x1, y1, x2, y2) -> float:
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def analyze(self, game_world, current_gold: int) -> Dict[str, Any]:
        bot_attackers = self._count_attackers(game_world, self.player_id)
        enemy_attackers = self._count_attackers(game_world, self.enemy_id)

        own_bombs = self._get_bomb_positions(game_world, self.player_id)
        enemy_bombs = self._get_bomb_positions(game_world, self.enemy_id)

        has_active_bomb = len(own_bombs) > 0
        enemy_bomb_active = len(enemy_bombs) > 0

        escort_strength = 0
        if has_active_bomb:
            bomb_x, bomb_y = own_bombs[0][1], own_bombs[0][2]
            target_range = self.P1_ATTACKERS_RANGE if self.player_id == 1 else self.P2_ATTACKERS_RANGE
            for unit_id, unit in game_world.units.items():
                if unit_id in target_range:
                    if self._distance(unit.x, unit.y, bomb_x, bomb_y) < 400:
                        escort_strength += 1

        bomb_threat = 0.0
        if enemy_bomb_active:
            base_x, base_y = self.BASE_POSITIONS[self.player_id]
            nearest_enemy_bomb_dist = min(
                self._distance(bx, by, base_x, base_y) for _, bx, by in enemy_bombs
            )
            max_threat_dist = 2000.0
            bomb_threat = max(0.0, 1.0 - (nearest_enemy_bomb_dist / max_threat_dist))

        total_bot_units = len(game_world.units)
        max_units = getattr(game_world, "max_units", 50)
        available_slots = max(0, max_units - total_bot_units)

        return {
            "bot_attackers": bot_attackers,
            "enemy_attackers": enemy_attackers,
            "has_active_bomb": has_active_bomb,
            "enemy_bomb_active": enemy_bomb_active,
            "escort_strength": escort_strength,
            "bomb_threat": bomb_threat,
            "current_gold": current_gold,
            "available_slots": available_slots,
        }
