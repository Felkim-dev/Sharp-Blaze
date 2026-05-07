"""
ShopManager — Manages shop proximity validation for unit purchases.

Responsibilities:
- Verify that at least one unit is within range of a shop before allowing purchases
- Track which units are near shops
- Provide shop-related utility methods
"""


class ShopManager:
    """
    Validates shop proximity before unit purchases.
    
    Ensures the bot respects the game mechanic:
    "At least one unit must be adjacent to a shop to purchase units."
    """

    def __init__(self, game_world):
        """
        Initialize ShopManager with a reference to the game world.
        
        Args:
            game_world: BotGameWorld instance (has shops dict and unit positions)
        """
        self.game_world = game_world

    def can_buy_unit(self, player_id: int) -> bool:
        """
        Check if player can buy a unit (has at least one unit near a shop).
        
        Args:
            player_id: 1 or 2, which player is buying
        
        Returns:
            True if at least one unit is within shop range, False otherwise
        """
        if not self.game_world.shops:
            # No shops registered yet (shouldn't happen after START_GAME)
            print("[ShopMgr] WARNING: No shops registered in game world")
            return False
        
        units_at_shop = self.game_world.has_unit_at_shop(player_id)
        
        if units_at_shop:
            return True
        else:
            return False

    def get_unit_at_shop(self, player_id: int) -> int:
        """
        Get a unit ID that is currently near a shop.
        
        Args:
            player_id: 1 or 2
        
        Returns:
            Unit ID if found near a shop, None otherwise
        """
        units_at_shop = self.game_world.get_units_at_shop(player_id)
        if units_at_shop:
            return units_at_shop[0][0]  # Return first unit ID
        return None

    def get_nearest_shop_for_unit(self, unit_id: int) -> int:
        """
        Find the nearest shop for a specific unit.
        
        Args:
            unit_id: Unit to find shop for
        
        Returns:
            Shop ID if any shop exists, None otherwise
        """
        if unit_id not in self.game_world.units:
            return None
        
        unit = self.game_world.units[unit_id]
        return self.game_world.get_nearby_shop(unit.x, unit.y, max_distance_cells=5)  # Larger search radius

    def get_closest_shop_to_position(self, x: float, y: float) -> int:
        """
        Find the closest shop to any position on the map.
        
        Args:
            x, y: Position in world pixels
        
        Returns:
            Shop ID, or None if no shops exist
        """
        if not self.game_world.shops:
            return None
        
        closest_shop_id = None
        closest_distance = float('inf')
        
        for shop_id, shop in self.game_world.shops.items():
            import math
            distance = math.sqrt((x - shop.x)**2 + (y - shop.y)**2)
            if distance < closest_distance:
                closest_distance = distance
                closest_shop_id = shop_id
        
        return closest_shop_id

    def get_all_shops(self) -> dict:
        """
        Get all registered shops.
        
        Returns:
            Dict of {shop_id: BotUnit}
        """
        return self.game_world.shops

    def debug_shop_status(self, player_id: int) -> str:
        """
        Generate debug info about current shop status.
        
        Returns:
            Formatted string with shop and unit info
        """
        shops_count = len(self.game_world.shops)
        units_at_shop = self.game_world.get_units_at_shop(player_id)
        
        status = f"[ShopMgr] Status for Player {player_id}: "
        status += f"{shops_count} shops available, "
        status += f"{len(units_at_shop)} units at shops"
        
        if units_at_shop:
            unit_ids = [str(u[0]) for u in units_at_shop]
            status += f" (unit IDs: {', '.join(unit_ids)})"
        
        return status
