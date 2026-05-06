"""
Unit tests for ShopManager module.
"""

import unittest
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ia.infra.bot_game_world import BotGameWorld
from ia.core.shop_manager import ShopManager


class TestShopManager(unittest.TestCase):
    """Test suite for ShopManager class"""

    def setUp(self):
        """Set up test fixtures"""
        self.world = BotGameWorld()
        self.shop_mgr = ShopManager(self.world)
        
        # Register test shops
        self.world.register_shops({
            11000: (1250, 1250),  # Shop 1
            11001: (3750, 3750),  # Shop 2
        })

    def test_shop_proximity_positive(self):
        """Test: Unit within shop range can buy"""
        self.world.add_unit(1001, 1250, 1250)  # Attacker at shop 1
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertTrue(can_buy, "Should allow purchase with unit at shop")

    def test_shop_proximity_negative(self):
        """Test: Unit far from shop cannot buy"""
        self.world.add_unit(1001, 100, 100)  # Far from any shop
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertFalse(can_buy, "Should block purchase with unit away from shop")

    def test_multiple_shops(self):
        """Test: Bot can use any shop if any unit is nearby"""
        self.world.add_unit(1001, 3750, 3750)  # Near shop 2
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertTrue(can_buy, "Should detect unit near second shop")

    def test_get_unit_at_shop(self):
        """Test: Retrieve unit ID that is at shop"""
        self.world.add_unit(1001, 1250, 1250)
        unit_id = self.shop_mgr.get_unit_at_shop(player_id=1)
        self.assertEqual(unit_id, 1001, "Should return correct unit ID")

    def test_get_unit_at_shop_none(self):
        """Test: Return None when no unit at shop"""
        self.world.add_unit(1001, 100, 100)  # Far from shop
        unit_id = self.shop_mgr.get_unit_at_shop(player_id=1)
        self.assertIsNone(unit_id, "Should return None when no unit at shop")

    def test_get_nearest_shop_for_unit(self):
        """Test: Find nearest shop for a unit"""
        self.world.add_unit(1001, 1200, 1200)  # Very close to shop 1 at (1250, 1250)
        nearest_shop = self.shop_mgr.get_nearest_shop_for_unit(unit_id=1001)
        self.assertEqual(nearest_shop, 11000, "Should find nearest shop")

    def test_get_nearest_shop_far_away(self):
        """Test: Return None if all shops too far"""
        self.world.add_unit(1001, 0, 0)  # Far from any shop
        nearest_shop = self.shop_mgr.get_nearest_shop_for_unit(unit_id=1001)
        self.assertIsNone(nearest_shop, "Should return None if shops too far")

    def test_no_shops_registered(self):
        """Test: Behavior when no shops registered"""
        world_empty = BotGameWorld()
        shop_mgr_empty = ShopManager(world_empty)
        world_empty.add_unit(1001, 1000, 1000)
        can_buy = shop_mgr_empty.can_buy_unit(player_id=1)
        self.assertFalse(can_buy, "Should block purchase when no shops exist")

    def test_multiple_units_at_shop(self):
        """Test: Multiple units at same shop"""
        self.world.add_unit(1001, 1250, 1250)  # Unit 1 at shop
        self.world.add_unit(1002, 1260, 1260)  # Unit 2 near unit 1 (still at shop)
        units_at_shop = self.world.get_units_at_shop(player_id=1)
        self.assertEqual(len(units_at_shop), 2, "Should find both units at shop")

    def test_collector_at_shop(self):
        """Test: Collectors can also buy from shops"""
        self.world.add_unit(3001, 1250, 1250)  # Collector at shop
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertTrue(can_buy, "Collectors should be able to buy")

    def test_wrong_player_units(self):
        """Test: Player 1 units don't help Player 2 buy"""
        self.world.add_unit(1001, 1250, 1250)  # Player 1 unit at shop
        can_buy = self.shop_mgr.can_buy_unit(player_id=2)
        self.assertFalse(can_buy, "Player 2 should not benefit from Player 1 units")

    def test_debug_status_message(self):
        """Test: Debug status message generation"""
        self.world.add_unit(1001, 1250, 1250)
        status = self.shop_mgr.debug_shop_status(player_id=1)
        self.assertIn("2 shops available", status, "Status should mention shop count")
        self.assertIn("1 units at shops", status, "Status should mention unit count")


if __name__ == '__main__':
    unittest.main()
