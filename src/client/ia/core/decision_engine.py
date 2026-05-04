from typing import Dict, Any, List, Tuple
from scipy.optimize import linprog
import numpy as np
from .game_config_loader import GameConfigLoader

class DecisionEngine:
    """
    Optimizes bot decisions using Linear Programming (Simplex algorithm).
    
    Converts game state metrics into an objective function:
    - Maximize: resource_generation + threat_mitigation + positional_advantage
    - Subject to: budget constraints, unit limits, strategic goals
    
    Decision variables:
    - x[0] = number of attackers to build
    - x[1] = number of collectors to build
    - x[2] = aggression factor (0-1, how aggressive to be)
    """

    def __init__(self, difficulty: str):
        """
        Initialize decision engine for a specific difficulty level
        
        Args:
            difficulty: "EASY", "MEDIUM", or "HARD"
            config: Configuration dict from BotConfig containing:
                - weights: threat_weight, resource_weight, position_weight
                - constraints: max_units_per_player, max_gold_spend, etc
        """
        self.difficulty = difficulty
        # Load all configuration from JSON files
        self.config_loader = GameConfigLoader()

        difficulty_params = self.config_loader.get_difficulty_params(difficulty)
        if not difficulty_params:
            raise ValueError(f"Difficulty '{difficulty}' not found in bot_ai_config.json")
        
        self.difficulty_params = difficulty_params
        
        # Extract weights directly from difficulty configuration (no "weights" wrapper needed)
        self.threat_weight = difficulty_params.get("threat_weight", 0.3)
        self.resource_weight = difficulty_params.get("resource_weight", 0.4)
        self.position_weight = difficulty_params.get("position_weight", 0.3)
        
        # Load constraints from bot_ai_config.json
        self.max_units = self.config_loader.get_max_units_per_player()
        self.max_attackers_per_decision = self.config_loader.get_max_attackers_per_decision()
        self.max_collectors_per_decision = self.config_loader.get_max_collectors_per_decision()
        
        # Unit costs (from combat_stats.json)
        self.ATTACKER_COST = 100
        self.COLLECTOR_COST = 50

        # Calculate max gold spend based on difficulty's gold_spend_ratio
        # Assumes initial gold = 500 per player
        INITIAL_GOLD = 500
        self.gold_spend_ratio = difficulty_params.get("gold_spend_ratio", 0.5)
        self.max_gold_spend = int(INITIAL_GOLD * self.gold_spend_ratio)

    def decide(self, game_state: Dict[str, Any], current_gold: int) -> Dict[str, Any]:
        """
        Make strategic decision based on game state
        
        Args:
            game_state: Output from GameStateAnalyzer.analyze()
            current_gold: Current gold amount
        
        Returns:
            Decision dict with:
            - "build_attackers": number of attackers to build
            - "build_collectors": number of collectors to build
            - "aggression": float [0, 1] indicating how aggressive to be
            - "priority": "attack", "defend", or "expand"
        """
        
        # Extract metrics from game state
        threat_level = game_state.get("threat_level", 0.5)
        resource_efficiency = game_state.get("resource_efficiency", 0.5)
        positional_advantage = game_state.get("positional_advantage", 0.0)
        
        bot_attackers = game_state.get("bot_attackers", 0)
        bot_collectors = game_state.get("bot_collectors", 0)
        total_bot_units = game_state.get("total_bot_units", 0)
        
        enemy_attackers = game_state.get("enemy_attackers", 0)
        
        # ====================================
        # STEP 1: Define decision variables bounds
        # ====================================
        # x[0] = attackers to build [0, max_possible]
        # x[1] = collectors to build [0, max_possible]
        # x[2] = aggression factor [0, 1]
        
        max_attackers_buildable = (current_gold // self.ATTACKER_COST)
        max_collectors_buildable = (current_gold // self.COLLECTOR_COST)
        max_attackers_buildable = min(max_attackers_buildable, self.max_units - total_bot_units)
        max_collectors_buildable = min(max_collectors_buildable, self.max_units - total_bot_units)
        
        bounds = [
            (0, max_attackers_buildable),    # Attackers
            (0, max_collectors_buildable),   # Collectors
            (0, 1)                           # Aggression
        ]
        
        # ====================================
        # STEP 2: Define objective function
        # ====================================
        # We want to MINIMIZE -1 * (objective), since linprog minimizes
        # Objective = threat_mitigation + resource_expansion + positional_push
        
        # Coefficients for linear objective: c = [c_a, c_c, c_agg]
        # c_a: coefficient for attackers (threat mitigation)
        # c_c: coefficient for collectors (resource expansion)
        # c_agg: coefficient for aggression (positional advantage)
        
        # More threat → want more attackers → reduce cost of attackers
        c_a = -1.0 * self.threat_weight * (threat_level + 0.5)  # Negate for minimization
        
        # Lower resource efficiency → want more collectors → reduce cost of collectors
        c_c = -1.0 * self.resource_weight * (1.0 - resource_efficiency)
        
        # Positive positional advantage → be more aggressive
        c_agg = -1.0 * self.position_weight * max(0, positional_advantage)
        
        c = np.array([c_a, c_c, c_agg])
        
        # ====================================
        # STEP 3: Define constraints (A_ub, b_ub for <=)
        # ====================================
        
        A_ub = []
        b_ub = []
        
        # Constraint 1: Total units built <= remaining unit slots
        # 1*attackers + 1*collectors + 0*aggression <= available_slots
        remaining_slots = self.max_units - total_bot_units
        A_ub.append([1, 1, 0])
        b_ub.append(max(1, remaining_slots))
        
        # Constraint 2: Total gold spent <= available gold
        # 100*attackers + 50*collectors + 0*aggression <= current_gold
        A_ub.append([self.ATTACKER_COST, self.COLLECTOR_COST, 0])
        b_ub.append(min(current_gold, self.max_gold_spend))
        
        # Constraint 3: If threat_level is high, must build minimum attackers
        if threat_level > 0.7:
            min_attackers_needed = max(1, int(enemy_attackers * 0.8))
            A_ub.append([-1, 0, 0])  # -attackers <= -min_needed
            b_ub.append(-min(min_attackers_needed, max_attackers_buildable))
        
        A_ub = np.array(A_ub) if A_ub else np.empty((0, 3))
        b_ub = np.array(b_ub) if b_ub else np.array([])
        
        # ====================================
        # STEP 4: Run Simplex optimization
        # ====================================
        
        if len(A_ub) > 0:
            result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
        else:
            # No constraints (shouldn't happen), just use bounds
            result = linprog(c, bounds=bounds, method='highs')
        
        # ====================================
        # STEP 5: Extract and round results
        # ====================================
        
        if result.success:
            attackers_to_build = int(np.floor(result.x[0]))
            collectors_to_build = int(np.floor(result.x[1]))
            aggression = float(np.clip(result.x[2], 0.0, 1.0))
        else:
            # Fallback: safe conservative decision
            attackers_to_build = 0
            collectors_to_build = 1 if current_gold >= self.COLLECTOR_COST else 0
            aggression = 0.0
        
        # ====================================
        # STEP 6: Determine priority
        # ====================================
        
        if threat_level > 0.6:
            priority = "defend"
        elif resource_efficiency < 0.4:
            priority = "expand"
        elif positional_advantage > 0.3:
            priority = "attack"
        else:
            priority = "expand" if collectors_to_build > attackers_to_build else "attack"
        
        # ====================================
        # Return decision
        # ====================================
        
        decision = {
            "build_attackers": attackers_to_build,
            "build_collectors": collectors_to_build,
            "aggression": aggression,
            "priority": priority,
            "optimization_status": "success" if result.success else "fallback"
        }
        
        return decision
