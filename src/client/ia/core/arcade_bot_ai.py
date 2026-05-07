from typing import Dict, Any, List, Tuple, Optional
import time
import math
from utils.json import JSON_Manager

ATTACK_RANGE = 400
ENGAGE_RANGE = 500

class ArcadeBotAI:
    def __init__(self, player_id: int, difficulty: str,
                 game_state_analyzer, decision_engine, network):
        self.player_id = player_id
        self.difficulty = difficulty
        self.analyzer = game_state_analyzer
        self.decision_engine = decision_engine
        self.network = network
        self.decision_cycle_ms = 500.0 if difficulty == "HARD" else 800.0
        self.last_decision_time = time.time() * 1000
        self.decision_count = 0
        self.last_game_state = None
        self.last_decision = None
        self.enemy_id = 2 if player_id == 1 else 1
        self.base_positions = {1: (300, 4700), 2: (4700, 300)}

        self._attacker_range = range(1000, 3000) if player_id == 1 else range(6000, 8000)
        self._own_bomb_range = range(12000, 13000) if player_id == 1 else range(13000, 14000)
        self._enemy_bomb_range = range(13000, 14000) if player_id == 1 else range(12000, 13000)

        self._patrol_phase = 0
        self._patrol_cycle_length = 4

    def update(self, game_world, game_screen) -> bool:
        current_time_ms = time.time() * 1000
        elapsed_ms = current_time_ms - self.last_decision_time
        if elapsed_ms < self.decision_cycle_ms:
            return False

        current_gold = getattr(game_screen, "player_gold", 0)
        game_state = self.analyzer.analyze(game_world, current_gold)
        self.last_game_state = game_state

        has_active_bomb = game_state.get("has_active_bomb", False)
        enemy_bomb_active = game_state.get("enemy_bomb_active", False)

        decision = self.decision_engine.decide(
            game_state, current_gold, has_active_bomb, enemy_bomb_active
        )
        self.last_decision = decision

        commands = self._generate_commands(decision, game_state, game_world)
        self._send_commands(commands)

        self.last_decision_time = current_time_ms
        self.decision_count += 1
        self._patrol_phase = (self._patrol_phase + 1) % self._patrol_cycle_length
        return True

    def _generate_commands(self, decision, game_state, game_world) -> List[Dict]:
        commands = []
        remaining_budget = 8

        priority = decision.get("priority", "attack")
        aggression = decision.get("aggression", 0.5)
        build_attackers = decision.get("build_attackers", 0)
        build_bombs = decision.get("build_bombs", 0)

        for _ in range(min(build_attackers, 3)):
            if remaining_budget <= 0:
                break
            commands.append(JSON_Manager.get_unit_attacker())
            remaining_budget -= 1

        for _ in range(build_bombs):
            if remaining_budget <= 0:
                break
            commands.append(JSON_Manager.get_unit_bomb())
            remaining_budget -= 1

        attack_cmds = self._generate_attack_orders(priority, game_state, game_world)
        for cmd in attack_cmds[:3]:
            if remaining_budget <= 0:
                break
            commands.append(cmd)
            remaining_budget -= 1

        move_cmds = self._generate_movement_orders(priority, aggression, game_state, game_world)
        for cmd in move_cmds[:3]:
            if remaining_budget <= 0:
                break
            commands.append(cmd)
            remaining_budget -= 1

        return commands

    def _generate_movement_orders(self, priority, aggression, game_state, game_world) -> List[Dict]:
        commands = []
        my_attackers = self._get_my_attackers(game_world)
        if not my_attackers:
            return commands

        enemy_units = game_state.get("enemy_units", [])
        nearest_shop_pos = game_state.get("nearest_shop_pos")
        nearest_enemy_pos = game_state.get("nearest_enemy_pos")

        if priority == "escort":
            own_bombs = self._get_own_bombs(game_world)
            if own_bombs:
                bomb_x, bomb_y = own_bombs[0][1], own_bombs[0][2]
                for unit_id, _ in my_attackers[:min(4, len(my_attackers))]:
                    commands.append(self._create_move_command(unit_id, bomb_x, bomb_y))
            return commands

        if priority == "intercept":
            enemy_bombs = self._get_enemy_bombs(game_world)
            if enemy_bombs:
                bomb_x, bomb_y = enemy_bombs[0][1], enemy_bombs[0][2]
                for unit_id, _ in my_attackers[:min(4, len(my_attackers))]:
                    commands.append(self._create_move_command(unit_id, bomb_x, bomb_y))
                return commands

        engaged_enemies = self._get_enemies_in_range(my_attackers, enemy_units, ENGAGE_RANGE)

        if engaged_enemies and nearest_enemy_pos:
            shop_pos = nearest_shop_pos if nearest_shop_pos else self.base_positions[self.player_id]
            count = len(my_attackers)
            for i, (unit_id, _) in enumerate(my_attackers):
                if count > 2 and i == 0:
                    commands.append(self._create_move_command(unit_id, shop_pos[0], shop_pos[1]))
                else:
                    target = engaged_enemies[i % len(engaged_enemies)]
                    commands.append(self._create_move_command(unit_id, target[1], target[2]))
            return commands

        patrol_points = self._get_patrol_points(nearest_shop_pos)
        for i, (unit_id, _) in enumerate(my_attackers[:min(3, len(my_attackers))]):
            point = patrol_points[i % len(patrol_points)]
            commands.append(self._create_move_command(unit_id, point[0], point[1]))

        return commands

    def _generate_attack_orders(self, priority, game_state, game_world) -> List[Dict]:
        commands = []
        my_attackers = self._get_my_attackers(game_world)
        if not my_attackers:
            return commands

        enemy_bombs = self._get_enemy_bombs(game_world)
        if enemy_bombs:
            count = 0
            for attacker_id, _ in my_attackers:
                if count >= 2:
                    break
                bomb = enemy_bombs[0]
                dist = math.sqrt(
                    (self._get_attacker_pos(my_attackers, attacker_id)[0] - bomb[1]) ** 2 +
                    (self._get_attacker_pos(my_attackers, attacker_id)[1] - bomb[2]) ** 2
                )
                if dist < ATTACK_RANGE + 50:
                    commands.append(JSON_Manager.attack(bomb[0], attacker_id))
                    count += 1
            if commands:
                return commands

        enemy_units = game_state.get("enemy_units", [])
        if not enemy_units:
            return commands

        engaged = []
        for eu_id, eu_x, eu_y in enemy_units:
            for _, unit in my_attackers:
                if math.sqrt((unit.x - eu_x) ** 2 + (unit.y - eu_y) ** 2) < ATTACK_RANGE:
                    engaged.append((eu_id, eu_x, eu_y))
                    break

        sorted_engaged = sorted(
            engaged,
            key=lambda eu: min(
                math.sqrt((u.x - eu[1]) ** 2 + (u.y - eu[2]) ** 2)
                for _, u in my_attackers
            )
        )

        used_attackers = set()
        for target in sorted_engaged:
            best_attacker = None
            best_dist = float('inf')
            for attacker_id, unit in my_attackers:
                if attacker_id in used_attackers:
                    continue
                dist = math.sqrt((unit.x - target[1]) ** 2 + (unit.y - target[2]) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best_attacker = attacker_id
            if best_attacker is not None:
                commands.append(JSON_Manager.attack(target[0], best_attacker))
                used_attackers.add(best_attacker)

        return commands

    def _get_attacker_pos(self, my_attackers, attacker_id):
        for aid, unit in my_attackers:
            if aid == attacker_id:
                return (unit.x, unit.y)
        return (0, 0)

    def _get_enemies_in_range(self, my_attackers, enemy_units, max_dist):
        result = []
        for eu_id, eu_x, eu_y in enemy_units:
            for _, unit in my_attackers:
                if math.sqrt((unit.x - eu_x) ** 2 + (unit.y - eu_y) ** 2) < max_dist:
                    result.append((eu_id, eu_x, eu_y))
                    break
        return result

    def _get_my_attackers(self, game_world) -> List[Tuple[int, any]]:
        attackers = []
        for unit_id, unit in game_world.units.items():
            if unit_id in self._attacker_range and game_world.get_owner_from_id(unit_id) == self.player_id:
                attackers.append((unit_id, unit))
        return attackers

    def _get_own_bombs(self, game_world) -> List[Tuple[int, float, float]]:
        bombs = []
        for unit_id, unit in game_world.units.items():
            if unit_id in self._own_bomb_range:
                bombs.append((unit_id, unit.x, unit.y))
        return bombs

    def _get_enemy_bombs(self, game_world) -> List[Tuple[int, float, float]]:
        bombs = []
        for unit_id, unit in game_world.units.items():
            if unit_id in self._enemy_bomb_range:
                bombs.append((unit_id, unit.x, unit.y))
        return bombs

    def _get_patrol_points(self, nearest_shop_pos) -> List[Tuple[float, float]]:
        shop = nearest_shop_pos if nearest_shop_pos else (2500.0, 2500.0)
        my_base = self.base_positions[self.player_id]

        mid_x = (shop[0] + my_base[0]) / 2
        mid_y = (shop[1] + my_base[1]) / 2

        forward_x = shop[0] + (shop[0] - my_base[0]) * 0.3
        forward_y = shop[1] + (shop[1] - my_base[1]) * 0.3
        forward_x = max(100, min(4900, forward_x))
        forward_y = max(100, min(4900, forward_y))

        points = [shop, (mid_x, mid_y)]

        if self._patrol_phase == 0:
            points.append(shop)
        elif self._patrol_phase == 1:
            points.append((mid_x, mid_y))
        elif self._patrol_phase == 2:
            points.append((forward_x, forward_y))
        else:
            points.append(shop)

        return points

    def _create_move_command(self, unit_id: int, target_x: float, target_y: float) -> Dict:
        cell_size = 50
        grid_x = max(0, min(99, int(target_x // cell_size)))
        grid_y = max(0, min(99, int(target_y // cell_size)))
        return JSON_Manager.get_moveorder(unit_id, grid_x, grid_y)

    def _send_commands(self, commands: List[Dict]) -> None:
        if not commands:
            return
        for cmd in commands:
            try:
                self.network.send_json(cmd)
            except Exception as e:
                print(f"[ArcadeBotAI] Error sending command: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "difficulty": self.difficulty,
            "decision_count": self.decision_count,
            "decision_cycle_ms": self.decision_cycle_ms,
            "last_game_state": self.last_game_state,
            "last_decision": self.last_decision,
        }
