"""
Unit tests for AttackDecisionEngine module.
"""

import unittest
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ia.core.attack_decision import AttackDecisionEngine


class TestAttackDecisionEngine(unittest.TestCase):
    """Test suite for AttackDecisionEngine class"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = AttackDecisionEngine()

    # ====================================
    # TEST GROUP 1: Economic Threshold
    # ====================================

    def test_no_attack_when_far_behind(self):
        """Test: No attack when army_balance < -0.5"""
        game_state = {
            "threat_level": 0.3,
            "army_balance": -0.6,
            "game_phase": "mid",
            "bot_attackers": 1,
            "enemy_attackers": 5,
            "enemy_collectors": 3,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertEqual(decision, "no_attack", "Should not attack when far behind")

    def test_can_attack_at_threshold(self):
        """Test: Can attack when army_balance >= -0.5"""
        game_state = {
            "threat_level": 0.5,
            "army_balance": -0.45,
            "game_phase": "mid",
            "bot_attackers": 3,
            "enemy_attackers": 4,
            "enemy_collectors": 2,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertNotEqual(decision, "no_attack", "Should allow attack at threshold")

    # ====================================
    # TEST GROUP 2: Undefended Base
    # ====================================

    def test_attack_undefended_base_with_advantage(self):
        """Test: Attack undefended base when we have advantage"""
        game_state = {
            "threat_level": 0.0,
            "army_balance": 0.3,
            "game_phase": "mid",
            "bot_attackers": 5,
            "enemy_attackers": 0,
            "enemy_collectors": 0,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertEqual(decision, "attack_base", "Should attack undefended base with advantage")

    def test_no_attack_undefended_base_without_advantage(self):
        """Test: Don't attack undefended base without advantage"""
        game_state = {
            "threat_level": 0.0,
            "army_balance": -0.1,
            "game_phase": "mid",
            "bot_attackers": 2,
            "enemy_attackers": 0,
            "enemy_collectors": 0,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertEqual(decision, "no_attack", "Should not attack undefended base without advantage")

    # ====================================
    # TEST GROUP 3: Threat Response
    # ====================================

    def test_attack_troops_when_threatened(self):
        """Test: Attack troops when under threat"""
        game_state = {
            "threat_level": 0.7,
            "army_balance": -0.1,
            "game_phase": "mid",
            "bot_attackers": 3,
            "enemy_attackers": 5,
            "enemy_collectors": 2,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertEqual(decision, "attack_troops", "Should attack troops under high threat")

    # ====================================
    # TEST GROUP 4: Game Phase Logic
    # ====================================

    def test_attack_base_late_game_with_advantage(self):
        """Test: Late game with advantage should attack base"""
        game_state = {
            "threat_level": 0.3,
            "army_balance": 0.4,
            "game_phase": "late",
            "bot_attackers": 12,
            "enemy_attackers": 8,
            "enemy_collectors": 5,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertEqual(decision, "attack_base", "Should attack base in late game with advantage")

    def test_defend_late_game_with_disadvantage(self):
        """Test: Late game with disadvantage should not attack"""
        game_state = {
            "threat_level": 0.8,
            "army_balance": -0.3,
            "game_phase": "late",
            "bot_attackers": 5,
            "enemy_attackers": 10,
            "enemy_collectors": 6,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertNotEqual(decision, "attack_base", "Should not attack base when outnumbered")

    def test_attack_base_mid_game_with_advantage(self):
        """Test: Mid game with advantage can attack base"""
        game_state = {
            "threat_level": 0.4,
            "army_balance": 0.2,
            "game_phase": "mid",
            "bot_attackers": 8,
            "enemy_attackers": 5,
            "enemy_collectors": 4,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertEqual(decision, "attack_base", "Should attack base in mid game with advantage")

    # ====================================
    # TEST GROUP 5: Default Behavior
    # ====================================

    def test_default_attack_troops(self):
        """Test: Default is to attack troops when uncertain"""
        game_state = {
            "threat_level": 0.5,
            "army_balance": 0.05,
            "game_phase": "mid",
            "bot_attackers": 5,
            "enemy_attackers": 5,
            "enemy_collectors": 4,
        }
        decision = self.engine.decide_attack_target(game_state)
        self.assertEqual(decision, "attack_troops", "Default should be attack_troops")

    # ====================================
    # TEST GROUP 6: Collector Priority
    # ====================================

    def test_attack_collectors_when_ahead(self):
        """Test: Attack collectors when significantly ahead"""
        should_attack = self.engine.should_attack_collector_first(
            threat_level=0.2,
            army_balance=0.5
        )
        self.assertTrue(should_attack, "Should attack collectors when ahead")

    def test_attack_attackers_under_threat(self):
        """Test: Attack attackers when threatened"""
        should_attack = self.engine.should_attack_collector_first(
            threat_level=0.8,
            army_balance=0.0
        )
        self.assertFalse(should_attack, "Should attack attackers when threatened")

    # ====================================
    # TEST GROUP 7: Attack Cost Estimate
    # ====================================

    def test_attack_cost_estimate(self):
        """Test: Estimate casualties from attacking N units"""
        cost = self.engine.estimate_attack_cost(target_count=10)
        self.assertGreater(cost, 0, "Should estimate some casualties")
        self.assertLess(cost, 10, "Casualties should be less than targets")

    def test_attack_cost_minimum(self):
        """Test: Minimum casualty estimate is 1"""
        cost = self.engine.estimate_attack_cost(target_count=0)
        self.assertEqual(cost, 1, "Should have minimum cost of 1")

    # ====================================
    # TEST GROUP 8: Attack Worthiness
    # ====================================

    def test_attack_worth_it_with_advantage(self):
        """Test: Attack is worth it with advantage"""
        is_worth = self.engine.is_attack_worth_it(
            our_attackers=10,
            enemy_units=6,
            army_balance=0.4
        )
        self.assertTrue(is_worth, "Should attack with advantage")

    def test_attack_not_worth_it_massively_behind(self):
        """Test: Attack not worth it when massively behind"""
        is_worth = self.engine.is_attack_worth_it(
            our_attackers=2,
            enemy_units=10,
            army_balance=-0.5
        )
        self.assertFalse(is_worth, "Should not attack when massively behind")

    # ====================================
    # TEST GROUP 9: Decision Details
    # ====================================

    def test_decision_details_message_generated(self):
        """Test: Generate human-readable decision explanation"""
        game_state = {
            "threat_level": 0.2,
            "army_balance": 0.4,
            "game_phase": "late",
            "enemy_attackers": 5,
        }
        details = self.engine.get_attack_decision_details("attack_base", game_state)
        self.assertIn("ATTACK_BASE", details, "Should mention decision type")
        self.assertIn("Late game", details, "Should explain game phase reasoning")

    def test_decision_no_attack_explanation(self):
        """Test: Explain no_attack decision"""
        game_state = {
            "threat_level": 0.5,
            "army_balance": -0.6,
            "game_phase": "mid",
            "enemy_attackers": 8,
        }
        details = self.engine.get_attack_decision_details("no_attack", game_state)
        self.assertIn("NO_ATTACK", details, "Should mention no_attack decision")
        self.assertIn("Economy mode", details, "Should explain economy reasoning")


if __name__ == '__main__':
    unittest.main()
