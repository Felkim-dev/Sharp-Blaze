from entities.units import Attacker,Recolectors
from entities.structures import GoldMine, Shop, Base

from utils.config import Config
from utils.json import JSON_Manager

class GameWorld:
    def __init__(self, network_manager):

        self.network = network_manager

        self.units = {}
        self.structures = {}

    def build_initial_state(self,units, structures):

        for entity_id,(net_x, net_y) in units.items(): 
            
            entity_id2 =int(entity_id)
            self.units[entity_id2] = Attacker(entity_id2, net_x, net_y)

        for entity_id,(net_x, net_y) in structures.items():
            if entity_id == '100':
                self.structures[entity_id] = Base(entity_id,net_x,net_y)
            elif entity_id == '101':
                self.structures[entity_id] = Base(entity_id,net_x,net_y)
            elif entity_id == '103':
                self.structures[entity_id] = Shop(entity_id,net_x,net_y)

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

        print(network_data)
        
        for entity_id,(net_x, net_y) in network_data.items():
            
            entity_id2 = int(entity_id)
            
            if entity_id2 not in self.units:
                self.units[entity_id2] = Recolectors(entity_id2,net_x,net_y)
            else:
                self.units[entity_id2].update_target(net_x,net_y)

        for unit in self.units.values():
            unit.update_physics()

    def draw(self,screen,camera):

        for unit in self.units.values():
            unit.draw(screen,camera.x,camera.y)

        for structure in self.structures.values():
            structure.draw(screen, camera.x, camera.y)

    def handle_left_click(self, world_x, world_y):
        """Processes a left click in world coordinates to select units."""
        unit_was_clicked = False

        for unit in self.units.values():
            # Check if this object has the check_click method (e.g., it's a Unit, not a Structure)
            if hasattr(unit, "check_click"):
                if unit.check_click(world_x, world_y):
                    unit.is_selected = True
                    unit_was_clicked = True
                    print(f"[WORLD] Unit {unit.id} selected.")
                else:
                    # If we clicked somewhere else, deselect this unit
                    unit.is_selected = False

        if not unit_was_clicked:
            print("[WORLD] Clicked empty ground. Deselected all units.")
