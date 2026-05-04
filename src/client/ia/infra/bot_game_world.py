"""
BotGameWorld — A headless, lightweight game world tracker for the Bot AI.
Tracks unit positions and ownership based on server UDP/TCP updates.
No Pygame dependency.
"""

class BotUnit:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class BotGameWorld:
    def __init__(self):
        self.units = {}
        self.structures = {}

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
