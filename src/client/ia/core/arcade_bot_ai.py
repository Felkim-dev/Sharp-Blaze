from typing import Dict, Any
import time
import math
from utils.json import JSON_Manager
from .arcade_game_state_analyzer import ArcadeGameStateAnalyzer
from .arcade_decision_engine import ArcadeDecisionEngine

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
        return True

    def _generate_commands(self, decision, game_state, game_world):
        commands = []
        remaining_budget = 6

        for _ in range(decision.get("build_attackers", 0)):
            if remaining_budget <= 0:
                break
            cmd = JSON_Manager.get_unit_attacker()
            commands.append(cmd)
            remaining_budget -= 1

        for _ in range(decision.get("build_bombs", 0)):
            if remaining_budget <= 0:
                break
            cmd = JSON_Manager.get_unit_bomb()
            commands.append(cmd)
            remaining_budget -= 1

        priority = decision.get("priority", "attack")
        aggression = decision.get("aggression", 0.5)

        move_cmds = self._generate_movement_orders(priority, aggression, game_state, game_world)
        for cmd in move_cmds:
            if remaining_budget <= 0:
                break
            commands.append(cmd)
            remaining_budget -= 1

        attack_cmds = self._generate_attack_orders(priority, game_state, game_world)
        for cmd in attack_cmds:
            if remaining_budget <= 0:
                break
            commands.append(cmd)
            remaining_budget -= 1

        return commands

    def _generate_movement_orders(self, priority, aggression, game_state, game_world):
        commands = []
        my_attackers = []
        target_range = range(1000, 3000) if self.player_id == 1 else range(6000, 8000)
        for unit_id, unit in game_world.units.items():
            if unit_id in target_range and game_world.get_owner_from_id(unit_id) == self.player_id:
                my_attackers.append((unit_id, unit))

        if not my_attackers:
            return commands

        if priority == "escort":
            own_bombs = self._get_own_bombs(game_world)
            if own_bombs:
                bomb_x, bomb_y = own_bombs[0][1], own_bombs[0][2]
                for unit_id, _ in my_attackers[:3]:
                    commands.append(self._create_move_command(unit_id, bomb_x, bomb_y))
        elif priority == "intercept":
            enemy_bombs = self._get_enemy_bombs(game_world)
            if enemy_bombs:
                bomb_x, bomb_y = enemy_bombs[0][1], enemy_bombs[0][2]
                for unit_id, _ in my_attackers[:3]:
                    commands.append(self._create_move_command(unit_id, bomb_x, bomb_y))
            else:
                enemy_base = self.base_positions[self.enemy_id]
                for unit_id, _ in my_attackers[:3]:
                    commands.append(self._create_move_command(unit_id, enemy_base[0], enemy_base[1]))
        elif priority == "buy_bomb" or priority == "attack":
            if aggression > 0.4:
                enemy_base = self.base_positions[self.enemy_id]
                for unit_id, _ in my_attackers[:3]:
                    commands.append(self._create_move_command(unit_id, enemy_base[0], enemy_base[1]))
            else:
                my_base = self.base_positions[self.player_id]
                for unit_id, _ in my_attackers[:2]:
                    offset_x = (hash((unit_id, "x")) % 400) - 200
                    offset_y = (hash((unit_id, "y")) % 400) - 200
                    tx = max(0, min(5000, my_base[0] + offset_x))
                    ty = max(0, min(5000, my_base[1] + offset_y))
                    commands.append(self._create_move_command(unit_id, tx, ty))

        return commands

    def _generate_attack_orders(self, priority, game_state, game_world):
        commands = []
        my_attackers = []
        target_range = range(1000, 3000) if self.player_id == 1 else range(6000, 8000)
        for unit_id, unit in game_world.units.items():
            if unit_id in target_range and game_world.get_owner_from_id(unit_id) == self.player_id:
                my_attackers.append((unit_id, unit))

        if not my_attackers:
            return commands

        enemy_units = []
        for unit_id, unit in game_world.units.items():
            if game_world.get_owner_from_id(unit_id) == self.enemy_id:
                enemy_units.append((unit_id, unit))

        if priority == "intercept":
            enemy_bombs = self._get_enemy_bombs(game_world)
            if enemy_bombs:
                target_id = enemy_bombs[0][0]
                for attacker_id, _ in my_attackers[:2]:
                    commands.append(JSON_Manager.attack(target_id, attacker_id))
                return commands

        if enemy_units:
            for i, (attacker_id, _) in enumerate(my_attackers[:2]):
                target = enemy_units[i % len(enemy_units)]
                commands.append(JSON_Manager.attack(target[0], attacker_id))
        else:
            enemy_base_id = self._get_enemy_base_id(game_world)
            if enemy_base_id is not None:
                for attacker_id, _ in my_attackers[:2]:
                    commands.append(JSON_Manager.attack(enemy_base_id, attacker_id))

        return commands

    def _get_own_bombs(self, game_world):
        bomb_range = range(12000, 13000) if self.player_id == 1 else range(13000, 14000)
        bombs = []
        for unit_id, unit in game_world.units.items():
            if unit_id in bomb_range:
                bombs.append((unit_id, unit.x, unit.y))
        return bombs

    def _get_enemy_bombs(self, game_world):
        bomb_range = range(13000, 14000) if self.player_id == 1 else range(12000, 13000)
        bombs = []
        for unit_id, unit in game_world.units.items():
            if unit_id in bomb_range:
                bombs.append((unit_id, unit.x, unit.y))
        return bombs

    def _get_enemy_base_id(self, game_world):
        enemy_range = range(5000, 6000) if self.enemy_id == 2 else range(0, 1000)
        for struct_id in game_world.structures:
            if struct_id in enemy_range:
                return struct_id
        return None

    def _create_move_command(self, unit_id, target_x, target_y):
        cell_size = 50
        grid_x = max(0, min(99, int(target_x // cell_size)))
        grid_y = max(0, min(99, int(target_y // cell_size)))
        return JSON_Manager.get_moveorder(unit_id, grid_x, grid_y)

    def _send_commands(self, commands):
        if not commands:
            return
        for cmd in commands:
            try:
                self.network.send_json(cmd)
            except Exception as e:
                print(f"[ArcadeBotAI] Error sending command: {e}")

    def get_stats(self):
        return {
            "player_id": self.player_id,
            "difficulty": self.difficulty,
            "decision_count": self.decision_count,
            "decision_cycle_ms": self.decision_cycle_ms,
            "last_game_state": self.last_game_state,
            "last_decision": self.last_decision,
        }
