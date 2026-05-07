"""Simplex optimizer for bot decision making using linear programming"""

import numpy as np
from scipy.optimize import linprog
from typing import Tuple, Optional


class SimplexOptimizer:
    """Uses Simplex method (via scipy linprog) to optimize unit purchasing decisions"""

    # Unit stats
    COLLECTOR_COST = 100
    COLLECTOR_INCOME_RATE = 10  # Gold per second when harvesting
    
    ATTACKER_COST = 200
    ATTACKER_DAMAGE = 20
    ATTACKER_RANGE = 1000
    
    # Strategy parameters
    MIN_COLLECTORS_EARLY_GAME = 3
    MIN_ATTACKERS_MID_GAME = 2

    def __init__(self, difficulty: str = "normal"):
        """Initialize optimizer
        
        Args:
            difficulty (str): "easy", "normal", or "hard" (future expansion)
        """
        self.difficulty = difficulty
        self.last_decision_time = 0
        self.decision_cooldown_ms = 1000  # Min time between decisions
        self.game_start_time = None

    def compute_optimal_purchase(
        self,
        available_gold: int,
        num_own_collectors: int,
        num_own_attackers: int,
        num_enemy_units: int,
        game_time_seconds: float
    ) -> Optional[str]:
        """Compute optimal unit to purchase using Simplex
        
        Args:
            available_gold (int): Gold available for purchase
            num_own_collectors (int): Current number of collector units
            num_own_attackers (int): Current number of attacker units
            num_enemy_units (int): Estimated number of enemy units
            game_time_seconds (float): Seconds since game start
            
        Returns:
            str: "Collector", "Attacker", or None (wait)
        """
        
        # Early game: prioritize collectors
        if game_time_seconds < 15 and num_own_collectors < self.MIN_COLLECTORS_EARLY_GAME:
            if available_gold >= self.COLLECTOR_COST:
                return "Collector"
            else:
                return None
        
        # Mid game: balance based on enemy pressure
        if 15 <= game_time_seconds < 60:
            if num_enemy_units > 0 and num_own_attackers < max(2, num_enemy_units // 2):
                if available_gold >= self.ATTACKER_COST:
                    return "Attacker"
            
            # Still buy collectors if gold allows and we're below threshold
            if num_own_collectors < num_own_attackers + 2:
                if available_gold >= self.COLLECTOR_COST:
                    return "Collector"
            
            return None
        
        # Late game: aggressive purchasing
        ratio = num_own_collectors / max(1, num_own_attackers)
        
        # If we have more collectors than attackers, buy attackers
        if ratio > 2.0 and available_gold >= self.ATTACKER_COST:
            return "Attacker"
        
        # If we have more attackers, buy collectors for economy
        if ratio < 1.0 and available_gold >= self.COLLECTOR_COST:
            return "Collector"
        
        # Balanced: buy based on gold efficiency and time
        # Collectors for steady income, Attackers for immediate threat
        if num_enemy_units > num_own_attackers:
            if available_gold >= self.ATTACKER_COST:
                return "Attacker"
        else:
            if available_gold >= self.COLLECTOR_COST:
                return "Collector"
        
        return None

    def compute_optimal_with_simplex(
        self,
        available_gold: int,
        num_own_collectors: int,
        num_own_attackers: int,
        num_enemy_units: int,
        game_time_seconds: float
    ) -> Optional[Tuple[str, float]]:
        """Advanced Simplex-based optimization (can be called for detailed analysis)
        
        Variables: x1 = collectors to buy, x2 = attackers to buy
        
        Objective: Maximize total_value = 10*x1 + 20*x2 (weighted by need)
        Constraints: 
            - 100*x1 + 200*x2 <= available_gold
            - x1, x2 >= 0
            - x1, x2 <= max_units (to prevent overflow)
        
        Args:
            available_gold (int): Gold available
            num_own_collectors (int): Current collectors
            num_own_attackers (int): Current attackers
            num_enemy_units (int): Enemy unit count
            game_time_seconds (float): Game time
            
        Returns:
            Tuple[str, float]: (unit_type, confidence_score) or None
        """
        
        # Coefficients for objective function (we minimize negative value)
        # Weighting: early game favor collectors, late game favor attackers
        if game_time_seconds < 30:
            c = [-10, -15]  # Collectors more valuable early (income)
        else:
            c = [-8, -20]   # Attackers more valuable late (defense)
        
        # Inequality constraints: A_ub @ x <= b_ub
        # Gold constraint: 100*x1 + 200*x2 <= available_gold
        A_ub = [[self.COLLECTOR_COST, self.ATTACKER_COST]]
        b_ub = [available_gold]
        
        # Bounds for variables
        max_collectors = min(10, (available_gold // self.COLLECTOR_COST) + 1)
        max_attackers = min(10, (available_gold // self.ATTACKER_COST) + 1)
        
        bounds = [(0, max_collectors), (0, max_attackers)]
        
        # Solve
        try:
            result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
            
            if not result.success or result.x is None:
                return None
            
            x1_collectors, x2_attackers = result.x
            
            # Determine which to buy (prefer integer results)
            if x1_collectors > 0.5 and available_gold >= self.COLLECTOR_COST:
                return ("Collector", min(1.0, x1_collectors))
            elif x2_attackers > 0.5 and available_gold >= self.ATTACKER_COST:
                return ("Attacker", min(1.0, x2_attackers))
            
            return None
            
        except Exception as e:
            print(f"[SIMPLEX] Error in optimization: {e}")
            return None

    def should_make_decision(self, current_time_ms: float) -> bool:
        """Check if enough time has passed since last decision
        
        Args:
            current_time_ms (float): Current time in milliseconds
            
        Returns:
            bool: True if cooldown expired
        """
        if current_time_ms - self.last_decision_time >= self.decision_cooldown_ms:
            self.last_decision_time = current_time_ms
            return True
        return False

    def get_strategy_info(self, game_time_seconds: float) -> str:
        """Get current strategy phase name
        
        Args:
            game_time_seconds (float): Game time
            
        Returns:
            str: "Early", "Mid", or "Late" game phase
        """
        if game_time_seconds < 30:
            return "Early Game - Economy Focus"
        elif game_time_seconds < 120:
            return "Mid Game - Balance"
        else:
            return "Late Game - Aggression"
