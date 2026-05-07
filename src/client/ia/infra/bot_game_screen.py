"""
BotGameScreen — A headless game state tracker for player resources.
Tracks gold and handles logic related to resources based on TCP messages.
"""

class BotGameScreen:
    def __init__(self):
        self.player_gold = 500
        self.player_id = None

    def process_tcp_message(self, data: dict, bot_game_world):
        """
        Process TCP messages that affect the state (resources, spawns, deaths).
        """
        msg_type = data.get("type")
        payload = data.get("payload", {})
        
        if msg_type == "START_GAME":
            self.player_gold = payload.get("gold", 500)
            self.player_id = payload.get("player_id")
            
        elif msg_type == "RESOURCES":
            self.player_gold = payload.get("gold", self.player_gold)
            
        elif msg_type == "BUY_UNIT_RESULT" and data.get("status") == "accepted":
            self.player_gold = payload.get("new_balance", self.player_gold)
            unit_id = payload.get("unit_id")
            spawn_x = payload.get("spawn_x", 0)
            spawn_y = payload.get("spawn_y", 0)
            if unit_id is not None:
                bot_game_world.add_unit(unit_id, spawn_x, spawn_y)
            
        elif msg_type == "UNIT_SPAWNED":
            unit_id = payload.get("unit_id")
            if unit_id is not None and unit_id not in bot_game_world.units:
                bot_game_world.add_unit(unit_id, 0, 0) # Position will be corrected by UDP
            
        elif msg_type == "ENTITY_DESTROYED":
            # Some server versions send "entity_id", others might send "target_entity_id"
            target_id = payload.get("entity_id", payload.get("target_entity_id"))
            if target_id is not None:
                bot_game_world.remove_entity(target_id)