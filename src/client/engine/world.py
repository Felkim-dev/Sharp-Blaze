import pygame

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

        self.cell_size = 50
        self.grid_cols = 100
        self.grid_rows = 100

        self.projectiles = []

    def world_to_grid(self, world_x, world_y):
        """Convert the pixels to grid indexes."""
        grid_x = int(world_x // self.cell_size)
        grid_y = int(world_y // self.cell_size)

        # Evitar que los clics fuera del mapa rompan el servidor
        grid_x = max(0, min(grid_x, self.grid_cols - 1))
        grid_y = max(0, min(grid_y, self.grid_rows - 1))
        return grid_x, grid_y

    def grid_to_world(self, grid_x, grid_y):
        """Convert the indexes the grid to world."""
        world_x = (grid_x * self.cell_size) + (self.cell_size // 2)
        world_y = (grid_y * self.cell_size) + (self.cell_size // 2)
        return world_x, world_y

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

    def get_owner_from_id(self, entity_id: int) -> int:
        """
        Determines the owner based on the hardcoded ID ranges.
        Returns 1 for Player 1, 2 for Player 2, and 0 for Neutral (Map structures).
        """
        if 0 <= entity_id <= 4999:
            return 1  # Belongs to Player 1

        elif 5000 <= entity_id <= 9999:
            return 2  # Belongs to Player 2

        elif entity_id >= 10000:
            return 0  # Neutral map entity (Mines, Shops)

        return -1  # Fallback for invalid IDs        

    def build_initial_state(self,units, structures,local_player_ID):

        self.local_player_id = local_player_ID

        for entity_id,(indexes_x, indexes_y) in units.items(): 
            entity_id2 =int(entity_id)

            pixel_x,pixel_y = self.grid_to_world(indexes_x,indexes_y)

            # Entity Instation
            self.units[entity_id2] = self.return_entities_object(entity_id2,pixel_x,pixel_y)

            # Unity Recolorize
            self.entity_team_changer(entity_id2)

        for entity_id,(indexes_x, indexes_y) in structures.items():
            entity_id2 = int(entity_id)

            pixel_x, pixel_y = self.grid_to_world(indexes_x, indexes_y)
            # Entity Instation
            self.structures[entity_id2] = self.return_entities_object(entity_id2,pixel_x,pixel_y)

            # Unity Recolorize
            if 0 <= entity_id2 <= 999 or 5000 <= entity_id2 <= 5999:
                self.entity_team_changer(entity_id2)

    def handle_box_selection(self, start_x, start_y, end_x, end_y):
        """
        Creates a selection box and selects all own units inside it.
        """
        # 1. Normalize the rectangle (Pygame Rect needs top-left, width, and height)
        left = min(start_x, end_x)
        top = min(start_y, end_y)
        width = abs(start_x - end_x)
        height = abs(start_y - end_y)

        # 2. Distinguish between a single click and a drag
        # If the box is extremely small (e.g., less than 5 pixels), treat it as a single click
        if width < 5 and height < 5:
            return self.handle_left_click(end_x, end_y)

        selection_rect = pygame.Rect(left, top, width, height)

        # 3. Clean up previous selections
        for unit in self.units.values():
            if hasattr(unit, "is_selected"):
                unit.is_selected = False

        # 4. Box Collision Logic
        selected_count = 0
        for u_id, unit in self.units.items():
            owner = self.get_owner_from_id(u_id)

            # Only select our own units (Player 1 or 2, depending on local_id)
            if owner == self.local_player_id:
                # Assuming your unit has 'x' and 'y' center coordinates
                if selection_rect.collidepoint(unit.x, unit.y):
                    unit.is_selected = True
                    selected_count += 1

        print(f"[WORLD] Box selection captured {selected_count} units.")

    def handle_right_click(self, target_world_x, target_world_y):
        """
        Processes right clicks.
        Returns a dictionary with the action ('MOVE' or 'ATTACK') and coordinates/target.
        """

        clicked_enemy_id = None
        clicked_enemy_entity = None

        # 1. CLEANUP: Remove the red circle from any previously targeted enemy
        for entity_dict in (self.units, self.structures):
            for entity in entity_dict.values():
                if hasattr(entity, "is_targeted"):
                    entity.is_targeted = False

        selected_unit_ids = []
        for u_id, unit in self.units.items():
            if getattr(unit, "is_selected", False):
                selected_unit_ids.append(u_id)

        if not selected_unit_ids:
            return

        # 2. CHECK COLLISIONS: Did we right-click on an entity?
        for entity_dict in (self.units, self.structures):
            for e_id,entity in entity_dict.items():
                if hasattr(entity, "check_click") and entity.check_click(target_world_x, target_world_y):

                    owner = self.get_owner_from_id(e_id)

                    # 3. LOGIC: Is it an enemy? (Belongs to a player, but not us)
                    if owner != 0 and owner != self.local_player_id:
                        clicked_enemy_id = e_id
                        clicked_enemy_entity = entity
                        break  # Stop searching, we found the target

        # 4. ACTION ROUTING
        if clicked_enemy_entity:
            # We clicked an enemy! Mark it red and return ATTACK command
            clicked_enemy_entity.is_targeted = True

            for unit_id in selected_unit_ids:
                command_payload = JSON_Manager.attack(int(clicked_enemy_id),unit_id)
                self.network.send_json(command_payload)

        else:
            # We clicked empty ground (or our own unit/neutral structure).
            # Treat it as a standard move command.

            target_grid_x, target_grid_y = self.world_to_grid(target_world_x, target_world_y)

            for unit_id in selected_unit_ids:

                command_payload = JSON_Manager.get_moveorder(int(unit_id), int(target_grid_x), int(target_grid_y))
                self.network.send_json(command_payload)

    def update(self):

        network_data = self.network.get_latest_positions()

        for entity_id,(net_x, net_y) in network_data.items():

            entity_id2 = int(entity_id)

            if entity_id2 in self.units:
                self.units[entity_id2].update_target(net_x,net_y)

        for unit in self.units.values():
            unit.update_physics()

        for bullet in self.projectiles[:]:
            bullet.update()

            if bullet.is_dead:
                self.projectiles.remove(bullet)

    def get_entity(self,id):
        return self.units[id]

    def detect_death_units(self):
        for unit in self.units.values():
            if unit.hp <= 0:
                print(f"BORRAR UNIDAD {unit.id}")
                return unit.id

    def spawn_unit(self, ID, x, y):
        if ID not in self.units:
            self.units[ID] = self.return_entities_object(ID, x, y)
            self.entity_team_changer(ID)

    def draw(self,screen,camera):

        for unit in self.units.values():
            unit.draw(screen,camera.x,camera.y)

        for structure in self.structures.values():
            structure.draw(screen, camera.x, camera.y)

        for bullet in self.projectiles:
            bullet.draw(screen, camera)

    def handle_left_click(self, world_x, world_y):
        """Processes a left click in world coordinates to select units."""
        # We will store the entity we clicked on to return it later
        clicked_entity = None

        # Iterate through both dictionaries (units and structures)
        for entity_dictionary in (self.units, self.structures):
            for entity in entity_dictionary.values():

                if hasattr(entity, "check_click"):
                    if entity.check_click(world_x, world_y):

                        # 1. MATHEMATICAL OWNERSHIP CHECK
                        entity_owner = self.get_owner_from_id(entity.id)

                        # 2. SELECTION LOGIC
                        # You can only select it if the owner matches your local player ID
                        if entity_owner == self.local_player_id:
                            entity.is_selected = True
                            clicked_entity = entity
                            print(f"[WORLD] Selected own entity: ID {entity.id}")

                        # Optional: Allow selecting neutral shops/mines to see their stats
                        elif entity_owner == 0:
                            entity.is_selected = True
                            clicked_entity = entity
                            print(f"[WORLD] Selected neutral structure: ID {entity.id}")

                        else:
                            # It's an enemy unit! Don't select it.
                            entity.is_selected = False
                            print(
                                f"[WORLD] Ignored click: Entity {entity.id} belongs to Player {entity_owner}"
                            )
                    else:
                        # Click was outside this entity's bounds
                        entity.is_selected = False

        return clicked_entity
