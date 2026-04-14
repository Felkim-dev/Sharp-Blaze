from entities.units import Attacker,Recolectors
from entities.structures import GoldMine, Shop, Base

from utils.config import Config
from utils.json import JSON_Manager

class GameWorld:
    def __init__(self, network_manager):

        self.network = network_manager

        self.local_color = (0, 212, 255)
        self.enemy_color = (255, 0, 85)

        self.units = {}
        self.structures = {}

    def entity_team_changer(self,id):
        if  0 <= id <= 4999:
            if 0 <= id <= 999:
                self.structures[id].change_color(self.local_color)
            else:
                self.units[id].change_color(self.local_color)
        elif 5000 <= id <= 9999:
            if 5000 <= id <= 5999:
                self.structures[id].change_color(self.enemy_color)
            else:
                self.units[id].change_color(self.enemy_color)

    def return_entities_object(self,id,net_x,net_y):
        """
        Defines the global index allocation for all game entities, categorized by
        player ownership, entity type, and environmental objects.

        Player 1 (Indices: 0 - 4,999)
        Structures: 0 - 999
        Units: 1,000 - 4,999
            Attacker Units: 1,000 - 2,999
            Recolectors Units: 3,000 - 4,999

        Player 2 (Indices: 5,000 - 9,999)
        Structures: 5,000 - 5,999
        Units:6,000 - 9,999
            Attacker Units:* 6,000 - 7,999
            Recolectors Units:* 8,000 - 9,999

        Map Structures (Indices: 10,000+)
           Mines: 10,000 - 11,000
           Shops: 11,001 - 12,000

        ---
        Note: Ensure that any new instantiation logic checks these bounds to prevent
        index collisions between player-owned units and world objects.
        """
        if 0 <= id <= 999 or 5000 <= id <= 5999:
            return Base(id, net_x, net_y)
        elif 1000 <= id <= 2999 or 6000 <= id <= 7999:
            return Attacker(id, net_x, net_y)
        elif 3000 <= id <= 4999 or 8000 <= id <= 9999:
            return Recolectors(id, net_x, net_y)
        elif 10000 <= id <= 10999:
            return GoldMine(id, net_x, net_y)
        elif 11000 <= id <= 11999:
            return Shop(id, net_x, net_y)

    def build_initial_state(self,units, structures):

        for entity_id,(net_x, net_y) in units.items(): 
            entity_id2 =int(entity_id)

            # Entity Instation
            self.units[entity_id2] = self.return_entities_object(entity_id2,net_x,net_y)

            # Unity Recolorize
            self.entity_team_changer(entity_id2)

        for entity_id,(net_x, net_y) in structures.items():
            entity_id2 = int(entity_id)

            # Entity Instation
            self.structures[entity_id2] = self.return_entities_object(entity_id2,net_x,net_y)

            # Unity Recolorize
            if 0 <= entity_id2 <= 999 or 5000 <= entity_id2 <= 5999:
                self.entity_team_changer(entity_id2)

    def handle_right_click(self, target_world_x, target_world_y):
        """Finds selected units and sends a MOVE_ORDER to the server."""

        for unit in self.units.values():
            # getattr is a safe way to check if 'is_selected' exists
            # (in case bases/structures don't have this attribute yet)
            if getattr(unit, "is_selected", False):

                # 1. Format the command exactly as agreed for the C++ server

                command_payload = JSON_Manager.get_moveorder(int(unit.id), int(target_world_x), int(target_world_y))

                # 2. Send it securely via TCP
                self.network.send_json(command_payload)

                print(
                    f"[WORLD] Sent MOVE_ORDER: Unit {unit.id} -> X:{int(target_world_x)} Y:{int(target_world_y)}"
                )

    def update(self):

        network_data = self.network.get_latest_positions()

        for entity_id,(net_x, net_y) in network_data.items():

            entity_id2 = int(entity_id)
            
            if entity_id2 in self.units:
                self.units[entity_id2].update_target(net_x,net_y)

        for unit in self.units.values():
            unit.update_physics()

    def spawn_unit(self, ID, x, y):
        if ID not in self.units:
            self.units[ID] = self.return_entities_object(ID, x, y)
            self.entity_team_changer(ID)

    def draw(self,screen,camera):

        for unit in self.units.values():
            unit.draw(screen,camera.x,camera.y)

        for structure in self.structures.values():
            structure.draw(screen, camera.x, camera.y)

    def handle_left_click(self, world_x, world_y):
        """Processes a left click in world coordinates to select units."""
        # We will store the entity we clicked on to return it later
        clicked_entity = None

        # Iterate through both dictionaries (units and structures)
        for entity_dictionary in (self.units, self.structures):
            for entity in entity_dictionary.values():

                if hasattr(entity, "check_click"):
                    if entity.check_click(world_x, world_y):

                        entity.is_selected = True
                        clicked_entity = entity  # SAVE THE CLICKED ENTITY
                        print(
                            f"[WORLD] Selected own entity: {entity.id} ({entity.__class__.__name__})"
                        )

                    else:
                        # Deselect if click was outside this entity
                        entity.is_selected = False

        if not clicked_entity:
            print("[WORLD] Clicked empty ground.")

        # RETURN THE OBJECT TO THE GAME SCREEN
        return clicked_entity
