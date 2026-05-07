"""
Unit tests for ShopManager module.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ia.infra.bot_game_world import BotGameWorld
from ia.core.shop_manager import ShopManager


class TestShopManager(unittest.TestCase):
    def setUp(self):
        self.world = BotGameWorld()
        self.shop_mgr = ShopManager(self.world)
        
        self.world.register_shops({
            11000: (1250, 1250),
            11001: (3750, 3750),
        })

    def test_shop_proximity_positive(self):
        self.world.add_unit(1001, 1250, 1250)
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertTrue(can_buy, "Should allow purchase with unit at shop")

    def test_shop_proximity_negative(self):
        self.world.add_unit(1001, 100, 100)
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertFalse(can_buy, "Should block purchase with unit away from shop")

    def test_multiple_shops(self):
        self.world.add_unit(1001, 3750, 3750)
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertTrue(can_buy, "Should detect unit near second shop")

    def test_get_unit_at_shop(self):
        self.world.add_unit(1001, 1250, 1250)
        unit_id = self.shop_mgr.get_unit_at_shop(player_id=1)
        self.assertEqual(unit_id, 1001, "Should return correct unit ID")

    def test_get_unit_at_shop_none(self):
        self.world.add_unit(1001, 100, 100)
        unit_id = self.shop_mgr.get_unit_at_shop(player_id=1)
        self.assertIsNone(unit_id, "Should return None when no unit at shop")

    def test_no_shops_registered(self):
        world_empty = BotGameWorld()
        shop_mgr_empty = ShopManager(world_empty)
        world_empty.add_unit(1001, 1000, 1000)
        can_buy = shop_mgr_empty.can_buy_unit(player_id=1)
        self.assertFalse(can_buy, "Should block purchase when no shops exist")

    def test_multiple_units_at_shop(self):
        self.world.add_unit(1001, 1250, 1250)
        self.world.add_unit(1002, 1260, 1260)
        units_at_shop = self.world.get_units_at_shop(player_id=1)
        self.assertEqual(len(units_at_shop), 2, "Should find both units at shop")

    def test_collector_at_shop(self):
        self.world.add_unit(3001, 1250, 1250)
        can_buy = self.shop_mgr.can_buy_unit(player_id=1)
        self.assertTrue(can_buy, "Collectors should be able to buy")

    def test_wrong_player_units(self):
        self.world.add_unit(1001, 1250, 1250)
        can_buy = self.shop_mgr.can_buy_unit(player_id=2)
        self.assertFalse(can_buy, "Player 2 should not benefit from Player 1 units")

    def test_debug_status_message(self):
        self.world.add_unit(1001, 1250, 1250)
        status = self.shop_mgr.debug_shop_status(player_id=1)
        self.assertIn("2 shops available", status)
        self.assertIn("1 units at shops", status)


if __name__ == '__main__':
    unittest.main()
