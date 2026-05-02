import pygame
import os

from engine.world import GameWorld
from engine.camera import Camera
from ui.minimap import Minimap
from ui.telemetry import TelemetryPanel
from ui.component import InfoBox, TextBox, Button
from entities.projectile import RectangularProjectile
from ui.shop import Shop

from utils.json import JSON_Manager
from utils.config import Config
from utils.audio import AudioManager

class GameScreen:
    def __init__(self, screen_manager , screen):

        # MAIN SCREEN
        self.screen_manager = screen_manager
        self.screen  = screen

        # MAIN COLOR
        self.MAINDARK = (19, 23, 34)

        # WORLD
        self.world = GameWorld(self.screen_manager.network)

        # CAMERA
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        self.camera = Camera(screen_w, screen_h, map_width=5000, map_height=5000)

        # MINIMAP
        self.minimap = Minimap(screen_w,screen_h,map_width=5000, map_height=5000)

        # Instantiate the Telemetry Panel
        self.telemetry = TelemetryPanel(self.screen.get_width())

        # SHOP
        self.shop = Shop()
        self.is_shop_open = False
        self.shop_autorization = False

        # PLAYER PARAMETERS
        self.player_gold = 0
        self.player_attacker_units = 0
        self.player_recolector_units = 0

        # Player Parameters (String)
        self.player_gold_string = str(self.player_gold)
        self.player_attacker_units_string = str(self.player_attacker_units)
        self.player_recolector_units_string = str(self.player_recolector_units)

        # COLOR FOR BOXE
        gray = (84, 84, 84)
        white = (255, 255, 255)
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

        GOLD_PATH = os.path.join(CURRENT_DIR, "..","assets", "gold.png")
        HAT_PATH = os.path.join(CURRENT_DIR, "..", "assets", "hat.png")
        SWORD_PATH = os.path.join(CURRENT_DIR, "..", "assets", "sword.png")

        # Instantiate the Text Boxes of Gold, Collectors and Attackers
        self.infobox_gold = InfoBox((50,650),(175,40),gray,"GOLD",self.player_gold_string,white,15,GOLD_PATH)
        self.infobox_hat = InfoBox((250,650),(200,40),gray,"COLLECTORS",self.player_recolector_units_string,white,15,HAT_PATH)
        self.infobox_sword = InfoBox((470,650),(200,40),gray,"ATTACKERS",self.player_attacker_units_string,white,15,SWORD_PATH)

        # UI Drag State
        self.is_dragging = False
        self.drag_start_screen = None
        self.drag_current_screen = None

        # GAME STATE
        self.is_game_over = False
        self.winner_player_id = None
        self.winner_box = TextBox((240,180),(800,200),(0,159, 12),f"SHARP BLAZE\nVICTORY!",(255,255,255),72)
        self.game_over_button = Button((465,420),(350,70),(112,112,112),"RETURN TO MENU", (255,255,255),36)

    def reset_state(self):
        # Clear world objects
        self.world.units.clear()
        self.world.structures.clear()
        self.world.projectiles.clear()
        self.world.obstacles.clear()
        
        # Reset game states
        self.is_game_over = False
        self.winner_player_id = None
        self.is_shop_open = False
        self.is_dragging = False
        
        # Reset camera
        self.camera.x = 0
        self.camera.y = 0
        
        # Reset Network variables
        if hasattr(self.screen_manager.network, 'latest_positions'):
            self.screen_manager.network.latest_positions.clear()

    def load_initial_state(self, gold, units, structures, player_ID, obstacles, local_ID, enemy_ID):
        
        self.reset_state()

        self.player_gold = gold
        self.infobox_gold.update_text(str(self.player_gold)) 

        self.local_ID = local_ID
        self.enemy_ID = enemy_ID
        self.player_Id = player_ID
        
        # TODO:ADD UNIT UI
        self.world.build_initial_state(units,structures,player_ID,obstacles)
        self.update_unit_counts()

    def update_unit_counts(self):
        attackers = 0
        collectors = 0
        for u_id, unit in self.world.units.items():
            if self.world.get_owner_from_id(u_id) == self.player_Id:
                if unit.__class__.__name__ == "Attacker":
                    attackers += 1
                elif unit.__class__.__name__ == "Recolectors":
                    collectors += 1
                    
        self.player_attacker_units = attackers
        self.player_recolector_units = collectors
        
        self.infobox_sword.update_text(str(self.player_attacker_units))
        self.infobox_hat.update_text(str(self.player_recolector_units))

    def trigger_game_over(self, winner_name):
        self.is_game_over = True
        self.winner_player_id = winner_name

        # ¡Aquí es donde inyectas el nombre real para que se actualice en pantalla!
        nuevo_texto = f"SHARP BLAZE\n{self.winner_player_id} VICTORY!"
        self.winner_box.update_text(nuevo_texto)
        
    def trigger_disconnect(self):
        self.is_game_over = True
        nuevo_texto = f"GAME\nDISCONNECTED!"
        self.winner_box.update_text(nuevo_texto)

    def handle_events(self, events, keys):
        """Processes one-time events like mouse clicks."""
        for event in events:

            if self.is_game_over:
                # Si el juego terminó, SOLO escuchamos clics izquierdos para el botón
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = event.pos

                    # Tu lógica exacta de detección:
                    if self.game_over_button.button_rectangle.collidepoint(mouse_pos):
                        AudioManager().play_click()
                        print("[GAME SCREEN] Return to Menu clicked!")
                        self.screen_manager.network.disconnect()
                        self.is_game_over = False
                        self.winner_player_id = None
                        self.screen_manager.change_screen("MAIN")
                continue

            # Detect Mouse Button Press
            if event.type == pygame.MOUSEBUTTONDOWN:

                mouse_x, mouse_y = event.pos
                mouse_pos = event.pos

                # 1. UI PROTECTION: Check if click is on the Square Minimap first!
                # We simply ask Pygame if the mouse coordinates are inside the minimap's Rect
                if self.minimap.rect.collidepoint(mouse_x, mouse_y):
                    # Click was inside the minimap UI, ignore world selection
                    continue

                if self.is_shop_open:
                    shop_rect = pygame.Rect(self.shop.x, self.shop.y, self.shop.width, self.shop.height)
                    
                    if shop_rect.collidepoint(mouse_x, mouse_y):
                        action = self.shop.handle_click(event, event.pos)

                        if action == "CLOSE":
                            self.is_shop_open = False
                            for entity in self.world.structures.values():
                                if entity.__class__.__name__ == "Shop":
                                    entity.is_selected = False
                        elif action == "BUY_COLLECTOR":
                            print("[GAME] Sending TCP command to buy Collector...")
                            self.screen_manager.network.send_json(JSON_Manager.get_unit_recolectors())
                        elif action == "BUY_ATTACKER":
                            print("[GAME] Sending TCP command to buy Attacker...")
                            self.screen_manager.network.send_json(JSON_Manager.get_unit_attacker())
                        
                        # Consume the click if inside the shop UI, preventing it from selecting world units
                        continue
                    else:
                        # Clicked outside the shop. Close it and deselect the shop structure.
                        self.is_shop_open = False
                        for entity in self.world.structures.values():
                            if entity.__class__.__name__ == "Shop":
                                entity.is_selected = False

                # 2. TRANSLATE: Screen Coordinates -> World Coordinates
                world_x = mouse_x + self.camera.x
                world_y = mouse_y + self.camera.y

                # -------------------------------------------------------------
                # LEFT CLICK (Button 1) -> Select Units
                # -------------------------------------------------------------
                if event.button == 1:

                    self.is_dragging = True
                    self.drag_start_screen = mouse_pos
                    self.drag_current_screen = mouse_pos

                # -------------------------------------------------------------
                # RIGHT CLICK (Button 3) -> Issue Move Commands
                # -------------------------------------------------------------

                elif event.button == 3:
                    self.world.handle_right_click(world_x, world_y)

            # FASE 2: Movimiento (Actualizar el dibujo)
            elif event.type == pygame.MOUSEMOTION:
                if self.is_dragging:
                    self.drag_current_screen = event.pos

            # FASE 3: Soltar Click (Ejecutar la selección matemática)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.is_dragging:
                    self.is_dragging = False
                    end_screen = event.pos

                    if self.minimap.rect.collidepoint(end_screen[0], end_screen[1]):
                        continue

                    # Translate screen coordinates to world coordinates
                    start_world_x = self.drag_start_screen[0] + self.camera.x
                    start_world_y = self.drag_start_screen[1] + self.camera.y
                    end_world_x = end_screen[0] + self.camera.x
                    end_world_y = end_screen[1] + self.camera.y

                    # Send to the engine logic
                    selected_entity = self.world.handle_box_selection(start_world_x, start_world_y, end_world_x, end_world_y)

                    if selected_entity and selected_entity.__class__.__name__ == "Shop":
                        self.is_shop_open = True
                        print("[GAME SCREEN] Shop selected! Opening UI.")
                    else:
                        self.is_shop_open = False

    def handle_entity_death(self, entity_id: int):
        """Delete the entity whe it is death."""

        # Delete units
        if entity_id in self.world.units:
            del self.world.units[entity_id]
            print(f"[WORLD] Unit {entity_id} destroyed and removed.")

        # Delete Structures
        elif entity_id in self.world.structures:
            del self.world.structures[entity_id]
            print(f"[WORLD] Structure {entity_id} destroyed and removed.")
            
        self.update_unit_counts()

    def update(self):

        if self.is_game_over:
            return

        if not Config.OFFLINE_DEBUG_MODE:
            data = self.screen_manager.network.receive_json()

            if data:

                print(data)

                if data.get("type") == "SHOP_AUTORIZATION":
                    self.shop_autorization = ["payload"]["authorized"]

                elif data.get("type") == "BUY_UNIT_RESULT":
                    if data["status"] == "accepted":
                        self.new_unit_id = data["payload"]["unit_id"]
                        self.new_spawn_x = data["payload"]["spawn_x"]
                        self.new_spawn_y = data["payload"]["spawn_y"]
                        self.new_gold = data["payload"]["new_balance"]

                        self.world.spawn_unit(self.new_unit_id,self.new_spawn_x,self.new_spawn_y)
                        self.update_unit_counts()

                        # Play shop purchase sound on successful buy
                        AudioManager().play_shop()

                        self.player_gold = self.new_gold
                        self.infobox_gold.update_text(str(self.player_gold)) 

                elif data.get("type") == "UNIT_SPAWNED":
                    self.new_unit_id = data["payload"]["unit_id"]

                    # TODO: Implementar la parte de Hardcoding
                    if 5000<=self.new_unit_id <= 9999: 
                        self.world.units[self.new_unit_id] = self.world.return_entities_object(self.new_unit_id,4700, 300)
                    elif 0 <= self.new_unit_id <= 4999:
                        self.world.units[self.new_unit_id] = self.world.return_entities_object(self.new_unit_id,300, 4700)

                    self.world.entity_team_changer(self.new_unit_id)
                    self.update_unit_counts()

                elif data.get("type") == "RESOURCES":

                    self.new_gold = data["payload"]["new_balance"]

                    self.player_gold = self.new_gold
                    self.infobox_gold.update_text(str(self.player_gold))

                elif data.get("type") == "UNIT_DAMAGED":

                    # INFORMACION SOBRE EL OBJETIVO
                    self.target_entity_id = data["payload"]["target_entity_id"]
                    self.attacker_entity_id = data["payload"]["attacker_entity_id"]
                    self.target_current_hp = data["payload"]["current_hp"]

                    # Informacion sobre el ATACANTE
                    self.attacker_entity_id = data["payload"]["attacker_entity_id"]

                    attacker = self.world.get_entity(self.attacker_entity_id)
                    target = self.world.get_entity(self.target_entity_id)

                    new_bullet = RectangularProjectile(
                        start_x=attacker.x,
                        start_y=attacker.y,
                        target_entity=target,
                        hp=self.target_current_hp, 
                    )

                    self.world.projectiles.append(new_bullet)

                    # Audio: attacker fires and target receives the shot
                    AudioManager().play_shoot()
                    AudioManager().play_receive_shot()

                    if 1000 <= self.target_entity_id <= 4999 or 6000 <= self.target_entity_id <= 9999:
                        self.world.units[self.target_entity_id].reduce_health(self.target_current_hp)

                    elif 0 <= self.target_entity_id <= 999 or 5000 <= self.target_entity_id <= 5999:
                        self.world.structures[self.target_entity_id].reduce_health(self.target_current_hp)

                elif data.get("type") == "GAME_OVER":
                    self.winner_player_id = data["payload"]["winner_player_id"]
                    
                    text = ""
                    
                    if self.player_Id == self.winner_player_id:
                        text = self.local_ID
                    else:
                        text = self.enemy_ID
                        
                    self.trigger_game_over(text)

                elif data.get("type") == "ENTITY_DESTROYED":

                    id = self.world.detect_death_units()

                    # Play death sound when an entity is destroyed
                    AudioManager().play_dead()

                    self.handle_entity_death(id)
                    self.screen_manager.network.latest_positions.pop(id,None)
                    
                elif data.get("type") == "DISCONNECTED":
                    self.trigger_disconnect()

        else:
            # DEBUG MODE
            if self.player_gold > 100:
                self.shop_autorization = True

        keys = pygame.key.get_pressed()

        # Mover Izquierda / Derecha
        if keys[pygame.K_a]:
            self.camera.move(-self.camera.speed, 0)
        elif keys[pygame.K_d]:
            self.camera.move(self.camera.speed, 0)

        # Mover Arriba / Abajo
        if keys[pygame.K_w]:
            self.camera.move(0, -self.camera.speed)
        elif keys[pygame.K_s]:
            self.camera.move(0, self.camera.speed)

        if pygame.mouse.get_pressed()[0]:
            mouse_x, mouse_y = pygame.mouse.get_pos()

            # Send the click to the minimap. If the player clicks inside it,
            # the camera will jump instantly to that location.
            self.minimap.handle_click(mouse_x, mouse_y, self.camera)

        if self.is_shop_open:
            self.shop.update(self.player_gold)

        self.world.update()

    def draw(self):

        # ======================= Variables ============================
        pantalla_w = self.screen.get_width()
        pantalla_h = self.screen.get_height()
        grosor = 5
        color_alerta = (255, 0, 0)  # Rojo

        # ======================= BG COLOR ============================
        self.screen.fill(self.MAINDARK)

        # ======================= MAIN ELEMENTS ============================
        self.world.draw(self.screen, self.camera)
        self.minimap.draw(self.screen,self.world,self.camera)
        self.telemetry.draw(self.screen, self.screen_manager.clock , self.screen_manager.network)
        if self.is_shop_open:
            self.shop.draw(self.screen)

        # ========================== RED BORDER OF THE SCREEN =====================================
        # Borde Izquierdo (La cámara llegó a X = 0)
        if self.camera.x <= 0:
            pygame.draw.rect(self.screen, color_alerta, (0, 0, grosor, pantalla_h))

        # Borde Derecho (La cámara llegó al límite derecho del mapa)
        if self.camera.x >= self.camera.map_width - self.camera.screen_width:
            pygame.draw.rect(
                self.screen, color_alerta, (pantalla_w - grosor, 0, grosor, pantalla_h)
            )

        # Borde Superior (La cámara llegó a Y = 0)
        if self.camera.y <= 0:
            pygame.draw.rect(self.screen, color_alerta, (0, 0, pantalla_w, grosor))

        # Borde Inferior (La cámara llegó al límite inferior del mapa)
        if self.camera.y >= self.camera.map_height - self.camera.screen_height:
            pygame.draw.rect(
                self.screen, color_alerta, (0, pantalla_h - grosor, pantalla_w, grosor)
            )

        # ================================== INFO BOXES========================================
        self.infobox_gold.draw(self.screen)
        self.infobox_hat.draw(self.screen)
        self.infobox_sword.draw(self.screen)

        # ================================= SELECTION BOX =======================================
        # DRAW SELECTION BOX
        if self.is_dragging and self.drag_current_screen:
            # 1. Normalize screen coordinates
            left = min(self.drag_start_screen[0], self.drag_current_screen[0])
            top = min(self.drag_start_screen[1], self.drag_current_screen[1])
            width = abs(self.drag_start_screen[0] - self.drag_current_screen[0])
            height = abs(self.drag_start_screen[1] - self.drag_current_screen[1])

            # 2. Draw outer border (solid)
            box_rect = (left, top, width, height)
            pygame.draw.rect(self.screen, (50, 220, 50), box_rect, 1)

            # 3. Draw inner fill (transparent)
            # Pygame needs a new Surface to handle alpha transparency on rects
            alpha_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            alpha_surface.fill((50, 220, 50, 40))  # Green with low opacity
            self.screen.blit(alpha_surface, (left, top))

        if self.is_game_over:
            self.winner_box.draw(self.screen)
            self.game_over_button.draw(self.screen)