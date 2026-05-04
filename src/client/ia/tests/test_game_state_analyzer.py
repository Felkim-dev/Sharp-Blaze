import unittest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game_state_analyzer import GameStateAnalyzer


class MockUnit:
    """Mock Unit object for testing"""
    def __init__(self, unit_id: int, x: float, y: float):
        self.id = unit_id
        self.x = x
        self.y = y


class MockGameWorld:
    """Mock GameWorld object for testing"""
    def __init__(self):
        self.units: Dict[int, MockUnit] = {}
    
    def add_unit(self, unit_id: int, x: float, y: float):
        """Helper to add a unit to the mock world"""
        self.units[unit_id] = MockUnit(unit_id, x, y)
    
    def get_owner_from_id(self, unit_id: int) -> int:
        """
        Mock owner determination based on unit_id ranges
        
        Ranges:
        - P1_STRUCTURES: 0-999 (player 1)
        - P1_ATTACKERS: 1000-2999 (player 1)
        - P1_COLLECTORS: 3000-4999 (player 1)
        - P2_STRUCTURES: 5000-5999 (player 2)
        - P2_ATTACKERS: 6000-7999 (player 2)
        - P2_COLLECTORS: 8000-9999 (player 2)
        """
        if 0 <= unit_id < 5000:
            return 1
        elif 5000 <= unit_id < 10000:
            return 2
        return None


class TestGameStateAnalyzer(unittest.TestCase):
    """Test suite for GameStateAnalyzer class"""

    def setUp(self):
        """
        Called before each test method.
        Initialize test fixtures here.
        """
        self.analyzer = GameStateAnalyzer(player_id=2)
        self.world = MockGameWorld()

    # ==============================
    # TEST 1: _count_units_by_type
    # ==============================
    
    def test_count_units_by_type_empty_world(self):
        """
        TEST 1.1: Count units in empty game world
        
        Expected:
        - Should return (0, 0) for both attackers and collectors
        """
        attackers, collectors = self.analyzer._count_units_by_type(self.world, self.analyzer.player_id)
        self.assertEqual(attackers, 0)
        self.assertEqual(collectors, 0)

    def test_count_units_by_type_only_player1(self):
        """
        TEST 1.2: Count units when only Player 1 has units
        """
        self.world.add_unit(1500, 100, 100)  # P1 attacker
        self.world.add_unit(3500, 200, 200)  # P1 collector
        
        p1_attackers, p1_collectors = self.analyzer._count_units_by_type(self.world, 1)
        p2_attackers, p2_collectors = self.analyzer._count_units_by_type(self.world, 2)
        
        self.assertEqual((p1_attackers, p1_collectors), (1, 1))
        self.assertEqual((p2_attackers, p2_collectors), (0, 0))

    def test_count_units_by_type_player2_only(self):
        """
        TEST 1.3: Count units when only Player 2 has units
        """
        self.world.add_unit(6500, 100, 100)
        self.world.add_unit(8500, 200, 200)
        self.world.add_unit(7000, 300, 300)
        
        p2_attackers, p2_collectors = self.analyzer._count_units_by_type(self.world, 2)
        p1_attackers, p1_collectors = self.analyzer._count_units_by_type(self.world, 1)
        
        self.assertEqual((p2_attackers, p2_collectors), (2, 1))
        self.assertEqual((p1_attackers, p1_collectors), (0, 0))

    def test_count_units_by_type_mixed_players(self):
        """
        TEST 1.4: Count units with both players present
        """
        # P1: 2 attackers, 3 collectors
        self.world.add_unit(1500, 100, 100)
        self.world.add_unit(2000, 150, 150)
        self.world.add_unit(3000, 200, 200)
        self.world.add_unit(3500, 250, 250)
        self.world.add_unit(4500, 300, 300)
        
        # P2: 1 attacker, 2 collectors
        self.world.add_unit(6500, 400, 400)
        self.world.add_unit(8000, 450, 450)
        self.world.add_unit(8500, 500, 500)
        
        p1_attackers, p1_collectors = self.analyzer._count_units_by_type(self.world, 1)
        p2_attackers, p2_collectors = self.analyzer._count_units_by_type(self.world, 2)
        
        self.assertEqual((p1_attackers, p1_collectors), (2, 3))
        self.assertEqual((p2_attackers, p2_collectors), (1, 2))

    # ==============================
    # TEST 2: calculate_threat_level
    # ==============================
    
    def test_threat_level_no_units(self):
        """
        TEST 2.1: Threat level when bot has no units
        """
        self.world.add_unit(1500, 100, 100)
        threat = self.analyzer.calculate_threat_level(self.world)
        self.assertEqual(threat, 1.0)

    def test_threat_level_zero_threat(self):
        """
        TEST 2.2: Threat level when bot is safe
        """
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        self.world.add_unit(7500, 250, 250)
        self.world.add_unit(7999, 300, 300)
        
        threat = self.analyzer.calculate_threat_level(self.world)
        self.assertEqual(threat, 0.0)

    def test_threat_level_range(self):
        """
        TEST 2.3: Threat level is always in [0, 1] range
        """
        # Bot P2: 3 attackers, 2 collectors
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        self.world.add_unit(8000, 250, 250)
        self.world.add_unit(8500, 300, 300)
        
        # Enemy P1: 5 attackers
        self.world.add_unit(1000, 400, 400)
        self.world.add_unit(1500, 450, 450)
        self.world.add_unit(2000, 500, 500)
        self.world.add_unit(2500, 550, 550)
        self.world.add_unit(2999, 600, 600)
        
        threat = self.analyzer.calculate_threat_level(self.world)
        self.assertGreaterEqual(threat, 0.0)
        self.assertLessEqual(threat, 1.0)

    # ==============================
    # TEST 3: calculate_resource_efficiency
    # ==============================
    
    def test_resource_efficiency_no_collectors(self):
        """
        TEST 3.1: Resource efficiency with no collectors
        """
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        
        efficiency = self.analyzer.calculate_resource_efficiency(self.world, current_gold=100)
        self.assertAlmostEqual(efficiency, 0.1, places=5)

    def test_resource_efficiency_optimal(self):
        """
        TEST 3.2: Resource efficiency at maximum
        """
        for i in range(10):
            self.world.add_unit(8000 + i, 100 + i*10, 100 + i*10)
        
        efficiency = self.analyzer.calculate_resource_efficiency(self.world, current_gold=500)
        self.assertEqual(efficiency, 1.0)

    def test_resource_efficiency_range(self):
        """
        TEST 3.3: Resource efficiency is always in [0, 1] range
        """
        self.world.add_unit(8000, 100, 100)
        self.world.add_unit(8500, 150, 150)
        
        efficiency = self.analyzer.calculate_resource_efficiency(self.world, current_gold=250)
        self.assertGreaterEqual(efficiency, 0.0)
        self.assertLessEqual(efficiency, 1.0)

    # ==============================
    # TEST 4: calculate_positional_advantage
    # ==============================
    
    def test_positional_advantage_no_attackers(self):
        """
        TEST 4.1: Positional advantage with no attackers
        """
        self.world.add_unit(8000, 100, 100)
        self.world.add_unit(8500, 150, 150)
        
        advantage = self.analyzer.calculate_positional_advantage(self.world)
        self.assertEqual(advantage, -1.0)

    def test_positional_advantage_range(self):
        """
        TEST 4.2: Positional advantage is always in [-1, 1] range
        """
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(8000, 200, 200)
        
        advantage = self.analyzer.calculate_positional_advantage(self.world)
        self.assertGreaterEqual(advantage, -1.0)
        self.assertLessEqual(advantage, 1.0)

    # ==============================
    # TEST 5: analyze (comprehensive)
    # ==============================
    
    def test_analyze_returns_dict(self):
        """
        TEST 5.1: analyze() returns a dictionary
        """
        result = self.analyzer.analyze(self.world, current_gold=300)
        self.assertIsInstance(result, dict)

    def test_analyze_contains_required_keys(self):
        """
        TEST 5.2: analyze() contains all required keys
        """
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(8000, 200, 200)
        
        result = self.analyzer.analyze(self.world, current_gold=300)
        
        required_keys = [
            "threat_level",
            "resource_efficiency",
            "positional_advantage",
            "bot_attackers",
            "bot_collectors",
            "enemy_attackers",
            "enemy_collectors",
            "current_gold",
            "total_bot_units",
            "total_enemy_units"
        ]
        
        for key in required_keys:
            self.assertIn(key, result)

    def test_analyze_metrics_in_valid_ranges(self):
        """
        TEST 5.3: All metrics in analyze() are in valid ranges
        """
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(8000, 200, 200)
        self.world.add_unit(1000, 300, 300)
        
        result = self.analyzer.analyze(self.world, current_gold=400)
        
        self.assertGreaterEqual(result["threat_level"], 0.0)
        self.assertLessEqual(result["threat_level"], 1.0)
        
        self.assertGreaterEqual(result["resource_efficiency"], 0.0)
        self.assertLessEqual(result["resource_efficiency"], 1.0)
        
        self.assertGreaterEqual(result["positional_advantage"], -1.0)
        self.assertLessEqual(result["positional_advantage"], 1.0)
        
        self.assertGreaterEqual(result["bot_attackers"], 0)
        self.assertGreaterEqual(result["bot_collectors"], 0)
        self.assertGreaterEqual(result["enemy_attackers"], 0)
        self.assertGreaterEqual(result["enemy_collectors"], 0)
        self.assertGreaterEqual(result["current_gold"], 0)

    def test_analyze_unit_counts_match(self):
        """
        TEST 5.4: Unit counts in analyze() match actual units
        """
        # Bot P2: 3 attackers, 2 collectors
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        self.world.add_unit(8000, 250, 250)
        self.world.add_unit(8500, 300, 300)
        
        result = self.analyzer.analyze(self.world, current_gold=300)
        
        self.assertEqual(result["bot_attackers"], 3)
        self.assertEqual(result["bot_collectors"], 2)
        self.assertEqual(result["total_bot_units"], 5)


if __name__ == '__main__':
    unittest.main()
