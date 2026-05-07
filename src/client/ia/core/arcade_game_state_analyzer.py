from typing import Dict, Any, List, Tuple, Optional
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

    def _attacker_range(self, player_id: int) -> range:
        return self.P1_ATTACKERS_RANGE if player_id == 1 else self.P2_ATTACKERS_RANGE

    def _bomb_range(self, player_id: int) -> range:
        return self.P1_BOMB_RANGE if player_id == 1 else self.P2_BOMB_RANGE

    def _distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def _count_attackers(self, game_world, player_id: int) -> int:
        count = 0
        target_range = self._attacker_range(player_id)
        for unit_id in game_world.units:
            if unit_id in target_range and game_world.get_owner_from_id(unit_id) == player_id:
                count += 1
        return count

    def _get_bomb_positions(self, game_world, player_id: int):
        target_range = self._bomb_range(player_id)
        bombs = []
        for unit_id, unit in game_world.units.items():
            if unit_id in target_range:
                bombs.append((unit_id, unit.x, unit.y))
        return bombs

    def _get_enemy_units(self, game_world) -> List[Tuple[int, float, float]]:
        """Return all enemy units (attackers + bombs) with positions."""
        enemy_units = []
        for unit_id, unit in game_world.units.items():
            if game_world.get_owner_from_id(unit_id) == self.enemy_id:
                enemy_units.append((unit_id, unit.x, unit.y))
        return enemy_units

    def _get_nearest_shop_pos(self, game_world) -> Optional[Tuple[float, float]]:
        """Find the shop nearest to any of our attacker units."""
        if not game_world.shops:
            return None

        attacker_range = self._attacker_range(self.player_id)
        best_dist = float('inf')
        best_shop = None

        for shop_id, shop in game_world.shops.items():
            for unit_id, unit in game_world.units.items():
                if unit_id in attacker_range and game_world.get_owner_from_id(unit_id) == self.player_id:
                    dist = self._distance(unit.x, unit.y, shop.x, shop.y)
                    if dist < best_dist:
                        best_dist = dist
                        best_shop = (shop.x, shop.y)

        if best_shop is None and game_world.shops:
            first_shop = next(iter(game_world.shops.values()))
            return (first_shop.x, first_shop.y)

        return best_shop

    def _count_units_near_shop(self, game_world) -> int:
        """Count how many of our attackers are within 100 pixels of any shop."""
        attacker_range = self._attacker_range(self.player_id)
        count = 0
        for unit_id, unit in game_world.units.items():
            if unit_id in attacker_range and game_world.get_owner_from_id(unit_id) == self.player_id:
                nearby = game_world.get_nearby_shop(unit.x, unit.y, max_distance_cells=2)
                if nearby is not None:
                    count += 1
        return count

    def _find_nearest_enemy_pos(self, game_world) -> Optional[Tuple[float, float]]:
        """Find the enemy unit closest to our base."""
        base_x, base_y = self.BASE_POSITIONS[self.player_id]
        best_dist = float('inf')
        best_pos = None

        for unit_id, unit in game_world.units.items():
            if game_world.get_owner_from_id(unit_id) == self.enemy_id:
                dist = self._distance(unit.x, unit.y, base_x, base_y)
                if dist < best_dist:
                    best_dist = dist
                    best_pos = (unit.x, unit.y)

        return best_pos

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
            attacker_range = self._attacker_range(self.player_id)
            for unit_id, unit in game_world.units.items():
                if unit_id in attacker_range:
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

        units_near_shop = self._count_units_near_shop(game_world)
        nearest_shop_pos = self._get_nearest_shop_pos(game_world)
        nearest_enemy_pos = self._find_nearest_enemy_pos(game_world)
        enemy_units = self._get_enemy_units(game_world)

        return {
            "bot_attackers": bot_attackers,
            "enemy_attackers": enemy_attackers,
            "has_active_bomb": has_active_bomb,
            "enemy_bomb_active": enemy_bomb_active,
            "escort_strength": escort_strength,
            "bomb_threat": bomb_threat,
            "current_gold": current_gold,
            "available_slots": available_slots,
            "units_near_shop": units_near_shop,
            "nearest_shop_pos": nearest_shop_pos,
            "nearest_enemy_pos": nearest_enemy_pos,
            "enemy_units": enemy_units,
        }
