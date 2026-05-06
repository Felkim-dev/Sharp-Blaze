"""
BotGameWorld — A headless, lightweight game world tracker for the Bot AI.
Tracks unit positions and ownership based on server UDP/TCP updates.
No Pygame dependency.
"""

import math

class BotUnit:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class BotGameWorld:
    def __init__(self):
        self.units = {}
        self.structures = {}
        self.shops = {}  # Shop structures (neutral, IDs 11000-11999)
        self.mines = {}  # Mine structures (neutral, IDs 10000-10999)

    def get_owner_from_id(self, unit_id: int) -> int:
        """
        Determine owner based on unit ID ranges.
        Player 1: 0-4999
        Player 2: 5000-9999
        Neutral: 10000+
        """
        if 0 <= unit_id < 5000:
            return 1
        elif 5000 <= unit_id < 10000:
            return 2
        else:
            return 0  # Neutral

    def load_initial_state(self, units: dict, structures: dict):
        """
        Load units and structures from START_GAME message.
        """
        for u_id, pos in units.items():
            self.add_unit(int(u_id), pos[0], pos[1])
            
        for s_id, pos in structures.items():
            self.structures[int(s_id)] = BotUnit(pos[0], pos[1])

    def update_positions(self, udp_positions: dict):
        """
        Update unit positions from UDP packets.
        udp_positions: {entity_id: [(x1, y1), ...]}
        """
        for entity_id, positions in udp_positions.items():
            if positions:
                # Get latest position in the list
                latest_x, latest_y = positions[-1]
                if entity_id in self.units:
                    self.units[entity_id].x = latest_x
                    self.units[entity_id].y = latest_y
                elif entity_id in self.structures:
                    self.structures[entity_id].x = latest_x
                    self.structures[entity_id].y = latest_y
                else:
                    self.add_unit(entity_id, latest_x, latest_y)

    def add_unit(self, unit_id: int, x: float, y: float):
        self.units[unit_id] = BotUnit(x, y)

    def remove_entity(self, entity_id: int):
        if entity_id in self.units:
            del self.units[entity_id]
        if entity_id in self.structures:
            del self.structures[entity_id]

    # ====================================
    # SHOPS & MINES MANAGEMENT
    # ====================================

    def register_shops(self, shop_dict: dict):
        """
        Register shop structures from game state.
        
        Args:
            shop_dict: Dict mapping shop_id -> (grid_x, grid_y) or [world_x, world_y]
        """
        for shop_id, pos in shop_dict.items():
            shop_id = int(shop_id)
            self.shops[shop_id] = BotUnit(pos[0], pos[1])
            print(f"[BotWorld] Shop registered: ID {shop_id} at ({pos[0]}, {pos[1]})")

    def register_mines(self, mine_dict: dict):
        """
        Register mine structures from game state.
        
        Args:
            mine_dict: Dict mapping mine_id -> (grid_x, grid_y) or [world_x, world_y]
        """
        for mine_id, pos in mine_dict.items():
            mine_id = int(mine_id)
            self.mines[mine_id] = BotUnit(pos[0], pos[1])
            print(f"[BotWorld] Mine registered: ID {mine_id} at ({pos[0]}, {pos[1]})")

    def get_nearby_shop(self, unit_x: float, unit_y: float, max_distance_cells: int = 2) -> int:
        """
        Find nearest shop within max_distance_cells grid cells.
        
        Args:
            unit_x, unit_y: Unit position (in world pixels)
            max_distance_cells: Max distance in grid cells (default: 2 cells = 100 pixels)
        
        Returns:
            Shop ID if found within range, None otherwise
        """
        cell_size = 50  # World pixels per grid cell
        max_distance_pixels = max_distance_cells * cell_size
        
        nearest_shop_id = None
        nearest_distance = float('inf')
        
        for shop_id, shop in self.shops.items():
            distance = math.sqrt((unit_x - shop.x)**2 + (unit_y - shop.y)**2)
            if distance < nearest_distance and distance <= max_distance_pixels:
                nearest_distance = distance
                nearest_shop_id = shop_id
        
        return nearest_shop_id

    def get_nearby_mine(self, unit_x: float, unit_y: float, max_distance_cells: int = 2) -> int:
        """
        Find nearest mine within max_distance_cells grid cells.
        
        Args:
            unit_x, unit_y: Unit position (in world pixels)
            max_distance_cells: Max distance in grid cells
        
        Returns:
            Mine ID if found within range, None otherwise
        """
        cell_size = 50
        max_distance_pixels = max_distance_cells * cell_size
        
        nearest_mine_id = None
        nearest_distance = float('inf')
        
        for mine_id, mine in self.mines.items():
            distance = math.sqrt((unit_x - mine.x)**2 + (unit_y - mine.y)**2)
            if distance < nearest_distance and distance <= max_distance_pixels:
                nearest_distance = distance
                nearest_mine_id = mine_id
        
        return nearest_mine_id

    def has_unit_at_shop(self, player_id: int) -> bool:
        """
        Check if any unit of player_id is within range of any shop.
        
        Args:
            player_id: 1 or 2
        
        Returns:
            True if at least 1 unit is near a shop, False otherwise
        """
        for unit_id, unit in self.units.items():
            owner = self.get_owner_from_id(unit_id)
            if owner == player_id:
                nearby_shop = self.get_nearby_shop(unit.x, unit.y, max_distance_cells=2)
                if nearby_shop is not None:
                    return True
        return False

    def get_units_at_shop(self, player_id: int) -> list:
        """
        Get all units of player_id that are near any shop.
        
        Returns:
            List of (unit_id, shop_id) tuples
        """
        units_at_shop = []
        for unit_id, unit in self.units.items():
            owner = self.get_owner_from_id(unit_id)
            if owner == player_id:
                nearby_shop = self.get_nearby_shop(unit.x, unit.y, max_distance_cells=2)
                if nearby_shop is not None:
                    units_at_shop.append((unit_id, nearby_shop))
        return units_at_shop
