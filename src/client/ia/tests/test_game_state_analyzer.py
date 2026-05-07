import unittest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.game_state_analyzer import GameStateAnalyzer


class MockUnit:
    def __init__(self, unit_id: int, x: float, y: float):
        self.id = unit_id
        self.x = x
        self.y = y


class MockGameWorld:
    def __init__(self):
        self.units: Dict[int, MockUnit] = {}
    
    def add_unit(self, unit_id: int, x: float, y: float):
        self.units[unit_id] = MockUnit(unit_id, x, y)
    
    def get_owner_from_id(self, unit_id: int) -> int:
        if 0 <= unit_id < 5000:
            return 1
        elif 5000 <= unit_id < 10000:
            return 2
        return None


class TestGameStateAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = GameStateAnalyzer(player_id=2)
        self.world = MockGameWorld()

    def test_count_units_by_type_empty_world(self):
        attackers, collectors = self.analyzer._count_units_by_type(self.world, self.analyzer.player_id)
        self.assertEqual(attackers, 0)
        self.assertEqual(collectors, 0)

    def test_count_units_by_type_only_player1(self):
        self.world.add_unit(1500, 100, 100)
        self.world.add_unit(3500, 200, 200)
        
        p1_a, p1_c = self.analyzer._count_units_by_type(self.world, 1)
        p2_a, p2_c = self.analyzer._count_units_by_type(self.world, 2)
        
        self.assertEqual((p1_a, p1_c), (1, 1))
        self.assertEqual((p2_a, p2_c), (0, 0))

    def test_count_units_by_type_player2_only(self):
        self.world.add_unit(6500, 100, 100)
        self.world.add_unit(8500, 200, 200)
        self.world.add_unit(7000, 300, 300)
        
        p2_a, p2_c = self.analyzer._count_units_by_type(self.world, 2)
        p1_a, p1_c = self.analyzer._count_units_by_type(self.world, 1)
        
        self.assertEqual((p2_a, p2_c), (2, 1))
        self.assertEqual((p1_a, p1_c), (0, 0))

    def test_count_units_mixed_players(self):
        self.world.add_unit(1500, 100, 100)
        self.world.add_unit(2000, 150, 150)
        self.world.add_unit(3000, 200, 200)
        self.world.add_unit(3500, 250, 250)
        self.world.add_unit(4500, 300, 300)
        self.world.add_unit(6500, 400, 400)
        self.world.add_unit(8000, 450, 450)
        self.world.add_unit(8500, 500, 500)
        
        p1_a, p1_c = self.analyzer._count_units_by_type(self.world, 1)
        p2_a, p2_c = self.analyzer._count_units_by_type(self.world, 2)
        
        self.assertEqual((p1_a, p1_c), (2, 3))
        self.assertEqual((p2_a, p2_c), (1, 2))

    def test_threat_level_no_units(self):
        self.world.add_unit(1500, 100, 100)
        threat = self.analyzer.calculate_threat_level(self.world)
        self.assertEqual(threat, 1.0)

    def test_threat_level_zero_threat(self):
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        self.world.add_unit(7500, 250, 250)
        self.world.add_unit(7999, 300, 300)
        threat = self.analyzer.calculate_threat_level(self.world)
        self.assertEqual(threat, 0.0)

    def test_threat_level_range(self):
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        self.world.add_unit(8000, 250, 250)
        self.world.add_unit(8500, 300, 300)
        self.world.add_unit(1000, 400, 400)
        self.world.add_unit(1500, 450, 450)
        self.world.add_unit(2000, 500, 500)
        self.world.add_unit(2500, 550, 550)
        self.world.add_unit(2999, 600, 600)
        
        threat = self.analyzer.calculate_threat_level(self.world)
        self.assertGreaterEqual(threat, 0.0)
        self.assertLessEqual(threat, 1.0)

    def test_resource_efficiency_no_collectors(self):
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        efficiency = self.analyzer.calculate_resource_efficiency(self.world, current_gold=100)
        self.assertAlmostEqual(efficiency, 0.1, places=5)

    def test_resource_efficiency_optimal(self):
        for i in range(10):
            self.world.add_unit(8000 + i, 100 + i*10, 100 + i*10)
        efficiency = self.analyzer.calculate_resource_efficiency(self.world, current_gold=500)
        self.assertEqual(efficiency, 1.0)

    def test_resource_efficiency_range(self):
        self.world.add_unit(8000, 100, 100)
        self.world.add_unit(8500, 150, 150)
        efficiency = self.analyzer.calculate_resource_efficiency(self.world, current_gold=250)
        self.assertGreaterEqual(efficiency, 0.0)
        self.assertLessEqual(efficiency, 1.0)

    def test_positional_advantage_no_attackers(self):
        self.world.add_unit(8000, 100, 100)
        self.world.add_unit(8500, 150, 150)
        advantage = self.analyzer.calculate_positional_advantage(self.world)
        self.assertEqual(advantage, -1.0)

    def test_positional_advantage_range(self):
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(8000, 200, 200)
        advantage = self.analyzer.calculate_positional_advantage(self.world)
        self.assertGreaterEqual(advantage, -1.0)
        self.assertLessEqual(advantage, 1.0)

    def test_analyze_returns_dict(self):
        result = self.analyzer.analyze(self.world, current_gold=300)
        self.assertIsInstance(result, dict)

    def test_analyze_contains_required_keys(self):
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(8000, 200, 200)
        result = self.analyzer.analyze(self.world, current_gold=300)
        
        required_keys = [
            "threat_level", "resource_efficiency", "positional_advantage",
            "army_balance", "bot_attackers", "bot_collectors",
            "enemy_attackers", "enemy_collectors", "current_gold",
            "total_bot_units", "total_enemy_units", "game_phase",
            "elapsed_seconds", "opponent_play_style"
        ]
        
        for key in required_keys:
            self.assertIn(key, result)

    def test_analyze_metrics_in_valid_ranges(self):
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
        self.assertGreaterEqual(result["army_balance"], -1.0)
        self.assertLessEqual(result["army_balance"], 1.0)

    def test_analyze_unit_counts_match(self):
        self.world.add_unit(6000, 100, 100)
        self.world.add_unit(6500, 150, 150)
        self.world.add_unit(7000, 200, 200)
        self.world.add_unit(8000, 250, 250)
        self.world.add_unit(8500, 300, 300)
        
        result = self.analyzer.analyze(self.world, current_gold=300)
        self.assertEqual(result["bot_attackers"], 3)
        self.assertEqual(result["bot_collectors"], 2)
        self.assertEqual(result["total_bot_units"], 5)

    def test_game_phase_early_by_time(self):
        phase = self.analyzer._calculate_game_phase(
            elapsed_seconds=10, total_units=15,
            initial_gold=500, current_gold=300
        )
        self.assertEqual(phase, "early")

    def test_game_phase_early_by_unit_count(self):
        phase = self.analyzer._calculate_game_phase(
            elapsed_seconds=50, total_units=5,
            initial_gold=500, current_gold=200
        )
        self.assertEqual(phase, "early")

    def test_game_phase_mid(self):
        phase = self.analyzer._calculate_game_phase(
            elapsed_seconds=45, total_units=12,
            initial_gold=500, current_gold=200
        )
        self.assertEqual(phase, "mid")

    def test_game_phase_late_by_time(self):
        phase = self.analyzer._calculate_game_phase(
            elapsed_seconds=100, total_units=10,
            initial_gold=500, current_gold=100
        )
        self.assertEqual(phase, "late")

    def test_game_phase_late_by_unit_count(self):
        phase = self.analyzer._calculate_game_phase(
            elapsed_seconds=50, total_units=22,
            initial_gold=500, current_gold=100
        )
        self.assertEqual(phase, "late")

    def test_opponent_style_rush(self):
        style = self.analyzer._detect_opponent_play_style(enemy_attackers=7, enemy_collectors=3)
        self.assertEqual(style, "rush")

    def test_opponent_style_eco(self):
        style = self.analyzer._detect_opponent_play_style(enemy_attackers=2, enemy_collectors=8)
        self.assertEqual(style, "eco")

    def test_opponent_style_mixed(self):
        style = self.analyzer._detect_opponent_play_style(enemy_attackers=5, enemy_collectors=5)
        self.assertEqual(style, "mixed")

    def test_opponent_style_empty(self):
        style = self.analyzer._detect_opponent_play_style(enemy_attackers=0, enemy_collectors=0)
        self.assertEqual(style, "mixed")


if __name__ == '__main__':
    unittest.main()
