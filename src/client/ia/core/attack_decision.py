"""
AttackDecisionEngine — Intelligent attack target selection.

Responsibilities:
- Decide whether to attack base, troops, or not attack at all
- Consider army balance, threat level, and game phase
- Prioritize targets strategically based on game state
"""

from typing import Dict, Any, Optional


class AttackDecisionEngine:
    """
    Makes intelligent attack decisions based on game state.
    
    Prevents senseless attacks and ensures the bot fights strategically.
    """

    def __init__(self):
        """Initialize attack decision engine."""
        # Threshold: below this army_balance, do NOT attack
        self.economic_threshold = -0.5
        
        # Threshold: above this, consider attacking base
        self.offensive_threshold = 0.1

    def decide_attack_target(self, game_state: Dict[str, Any]) -> str:
        """
        Decide what the bot should attack based on game state.
        
        Args:
            game_state: Output from GameStateAnalyzer.analyze()
                Must contain: threat_level, army_balance, game_phase,
                              bot_attackers, enemy_attackers
        
        Returns:
            String: "attack_base", "attack_troops", or "no_attack"
        """
        # Extract metrics
        threat_level = game_state.get("threat_level", 0.5)
        army_balance = game_state.get("army_balance", 0.0)
        game_phase = game_state.get("game_phase", "mid")
        
        enemy_attackers = game_state.get("enemy_attackers", 0)
        enemy_collectors = game_state.get("enemy_collectors", 0)
        
        # ====================================
        # STEP 1: If massively behind, don't attack
        # ====================================
        if army_balance < self.economic_threshold:
            # Enemy is significantly stronger → focus on economy
            return "no_attack"
        
        # ====================================
        # STEP 2: If no enemy units exist, can attack base
        # ====================================
        total_enemy_units = enemy_attackers + enemy_collectors
        
        if total_enemy_units == 0:
            # Base is undefended
            if army_balance > self.offensive_threshold:
                return "attack_base"
            else:
                # Even if base is undefended, don't attack if not sure we win
                return "no_attack"
        
        # ====================================
        # STEP 3: If heavily threatened, defend by attacking troops
        # ====================================
        if threat_level > 0.6 and army_balance < -0.1:
            # Enemy is dangerous and we're slightly behind → eliminate threat
            return "attack_troops"
        
        # ====================================
        # STEP 4: Late game + advantage = push for base
        # ====================================
        if game_phase == "late" and army_balance > 0.2:
            return "attack_base"
        
        # ====================================
        # STEP 5: Mid game + advantage = pressure base
        # ====================================
        if game_phase == "mid" and army_balance > self.offensive_threshold:
            return "attack_base"
        
        # ====================================
        # STEP 6: Default: attack troops (safest option)
        # ====================================
        return "attack_troops"

    def should_attack_collector_first(self, threat_level: float, army_balance: float) -> bool:
        """
        Determine if should prioritize killing collectors over attackers.
        
        Collectors are good targets because:
        - Reduce enemy economy
        - Are usually undefended
        
        But only if we're not in immediate danger.
        
        Args:
            threat_level: Current threat from enemy
            army_balance: Current army balance
        
        Returns:
            True if collectors are priority, False if attackers are priority
        """
        # If threat is high, eliminate attackers first
        if threat_level > 0.7:
            return False
        
        # If we're significantly ahead, attack economy (collectors)
        if army_balance > 0.3:
            return True
        
        # Default: target attackers (threat reduction)
        return False

    def estimate_attack_cost(self, target_count: int) -> int:
        """
        Estimate how many of our units will be lost attacking N targets.
        
        Rough heuristic for deciding if attack is worth it.
        
        Args:
            target_count: Number of enemy units
        
        Returns:
            Estimated friendly casualties
        """
        # Very rough: expect 1:1 casualty ratio
        # In reality varies, but this is a reasonable default
        return max(1, target_count // 2)

    def is_attack_worth_it(self, our_attackers: int, 
                          enemy_units: int,
                          army_balance: float) -> bool:
        """
        Determine if we should commit to an attack.
        
        Args:
            our_attackers: Number of our attacker units
            enemy_units: Total enemy units
            army_balance: Current balance metric
        
        Returns:
            True if attack has reasonable chance of success
        """
        # If significantly outnumbered, don't attack
        if army_balance < -0.4:
            return False
        
        # If we have significant advantage, attack
        if army_balance > 0.2:
            return True
        
        # If roughly balanced, only attack if we have units
        if our_attackers > 0 and enemy_units > 0:
            return True
        
        return False

    def get_attack_decision_details(self, decision: str, game_state: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation of attack decision.
        
        Args:
            decision: Result from decide_attack_target()
            game_state: Game state dict
        
        Returns:
            Formatted string explaining the decision
        """
        threat_level = game_state.get("threat_level", 0.5)
        army_balance = game_state.get("army_balance", 0.0)
        game_phase = game_state.get("game_phase", "mid")
        enemy_attackers = game_state.get("enemy_attackers", 0)
        
        reason = f"[AttackDecision] {decision.upper()}: "
        
        if decision == "no_attack":
            if army_balance < self.economic_threshold:
                reason += f"Economy mode (balance={army_balance:.2f} < {self.economic_threshold})"
            elif enemy_attackers == 0 and army_balance <= self.offensive_threshold:
                reason += f"Base undefended but weak position (balance={army_balance:.2f})"
            else:
                reason += "Too risky"
        
        elif decision == "attack_troops":
            if threat_level > 0.6:
                reason += f"High threat ({threat_level:.2f}), eliminate enemy army"
            else:
                reason += "Safe default: attack enemy troops"
        
        elif decision == "attack_base":
            if enemy_attackers == 0:
                reason += "Base undefended, no enemy troops"
            elif game_phase == "late":
                reason += f"Late game advantage (balance={army_balance:.2f})"
            else:
                reason += f"Mid game advantage (balance={army_balance:.2f})"
        
        return reason
