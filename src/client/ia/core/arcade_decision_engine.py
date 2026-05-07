import numpy as np
from scipy.optimize import linprog
from utils.config import Config

class ArcadeDecisionEngine:
    def __init__(self):
        self.attacker_cost = Config.ARCADE_ATTACKER_COST
        self.bomb_cost = Config.ARCADE_BOMB_COST
        self.max_units = 50
        self.min_escorts_for_bomb = 2

    def decide(self, game_state, gold, has_active_bomb, enemy_bomb_active):
        bomb_threat = game_state.get("bomb_threat", 0.0)
        escort_strength = game_state.get("escort_strength", 0)
        available_slots = game_state.get("available_slots", 0)
        bot_attackers = game_state.get("bot_attackers", 0)
        enemy_attackers = game_state.get("enemy_attackers", 0)

        max_attackers_buildable = min(available_slots, gold // self.attacker_cost)
        max_bombs_buildable = 1 if gold >= self.bomb_cost and not has_active_bomb else 0

        bounds = [
            (0, max_attackers_buildable),
            (0, max_bombs_buildable),
            (0, 1),
        ]

        threat_bias = bomb_threat if enemy_bomb_active else 0.0
        c_a = -1.0 * (0.4 + threat_bias + (0.1 * max(0, enemy_attackers - bot_attackers)))
        c_b = -1.0 * (0.8 if not has_active_bomb else -0.5)
        c_agg = -1.0 * (0.3 + (0.2 * escort_strength))
        c = np.array([c_a, c_b, c_agg])

        A_ub = []
        b_ub = []

        A_ub.append([self.attacker_cost, self.bomb_cost, 0])
        b_ub.append(gold)

        A_ub.append([1, 1, 0])
        b_ub.append(available_slots)

        if has_active_bomb and escort_strength < self.min_escorts_for_bomb:
            A_ub.append([-1, 0, 0])
            b_ub.append(-self.min_escorts_for_bomb)

        A_ub = np.array(A_ub) if A_ub else np.empty((0, 3))
        b_ub = np.array(b_ub) if b_ub else np.array([])

        if len(A_ub) > 0:
            result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
        else:
            result = linprog(c, bounds=bounds, method="highs")

        if result.success:
            attackers_to_build = int(np.floor(result.x[0]))
            bombs_to_build = int(np.floor(result.x[1]))
            aggression = float(np.clip(result.x[2], 0.0, 1.0))
        else:
            attackers_to_build = 1 if gold >= self.attacker_cost else 0
            bombs_to_build = 1 if max_bombs_buildable > 0 and gold >= self.bomb_cost else 0
            aggression = 0.5

        if has_active_bomb and escort_strength < self.min_escorts_for_bomb:
            priority = "escort"
        elif enemy_bomb_active:
            priority = "intercept"
        elif not has_active_bomb and gold >= self.bomb_cost:
            priority = "buy_bomb"
        else:
            priority = "attack"

        return {
            "build_attackers": attackers_to_build,
            "build_bombs": bombs_to_build,
            "aggression": aggression,
            "priority": priority,
            "optimization_status": "success" if result.success else "fallback",
        }
