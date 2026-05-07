import pygame
import os

from engine.world import GameWorld
from engine.camera import Camera
from ui.minimap import Minimap
from ui.telemetry import TelemetryPanel
from ui.component import InfoBox, TextBox, Button
from entities.projectile import RectangularProjectile
from ui.shop import Shop
from ui.pause_overlay import PauseOverlay
from ui.tutorial_overlay import TutorialOverlay

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

        # SCALE FACTORS relative to base resolution 1280x720
        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        # WORLD
        self.world = GameWorld(self.screen_manager.network)

        # CAMERA
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        self.camera = Camera(screen_w, screen_h, map_width=5000, map_height=5000)

        # MINIMAP (scaled)
        self.minimap = Minimap(screen_w, screen_h, map_width=5000, map_height=5000)

        # Instantiate the Telemetry Panel (scaled)
        self.telemetry = TelemetryPanel(screen_w, screen_h)

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
        # Positions are relative to screen dimensions for resolution scaling
        info_y = screen_h - int(70 * sy)
        info_box_h = int(40 * sy)
        info_text_size = int(15 * sy)
        self.infobox_gold = InfoBox((int(50 * sx), info_y),(int(175 * sx), info_box_h),gray,"GOLD",self.player_gold_string,white,info_text_size,GOLD_PATH)
        self.infobox_hat = InfoBox((int(250 * sx), info_y),(int(200 * sx), info_box_h),gray,"COLLECTORS",self.player_recolector_units_string,white,info_text_size,HAT_PATH)
        self.infobox_sword = InfoBox((int(470 * sx), info_y),(int(200 * sx), info_box_h),gray,"ATTACKERS",self.player_attacker_units_string,white,info_text_size,SWORD_PATH)

        BOMB_PATH = os.path.join(CURRENT_DIR, "..", "assets", "bomb.png")
        self.infobox_bomb = InfoBox((int(250 * sx), info_y),(int(200 * sx), info_box_h),gray,"BOMBS","0",white,info_text_size,BOMB_PATH)

        self.is_arcade = False
        self.timer_seconds = Config.ARCADE_GAME_DURATION
        self.timer_font = pygame.font.Font(
            os.path.join(CURRENT_DIR, "..", "assets", "Anton-Regular.ttf"),
            int(48 * sy),
        )
        self.previous_gold = self.player_gold
        self.last_kill_world = None
        self.kill_gold_floats = []
        self.immune_floats = []
        self.tutorial = TutorialOverlay(self.screen)

        # UI Drag State
        self.is_dragging = False
        self.drag_start_screen = None
        self.drag_current_screen = None

        # GAME STATE
        self.is_game_over = False
        self.winner_player_id = None
        self.is_paused = False
        self.pause_initiator = False
        self.pause_overlay = None

        self.explosion_effects = []
        # Center the game-over UI relative to screen dimensions
        go_box_w, go_box_h = int(800 * sx), int(200 * sy)
        go_box_x = (screen_w - go_box_w) // 2
        go_box_y = (screen_h - go_box_h) // 2 - int(60 * sy)
        go_text_size = int(72 * sy)
        self.winner_box = TextBox((go_box_x, go_box_y),(go_box_w, go_box_h),(0,159, 12),f"SHARP BLAZE\nVICTORY!",(255,255,255),go_text_size)
        go_btn_w, go_btn_h = int(350 * sx), int(70 * sy)
        go_btn_x = (screen_w - go_btn_w) // 2
        go_btn_y = go_box_y + go_box_h + int(40 * sy)
        go_btn_text_size = int(36 * sy)
        self.game_over_button = Button((go_btn_x, go_btn_y),(go_btn_w, go_btn_h),(112,112,112),"RETURN TO MENU", (255,255,255),go_btn_text_size)

    def reset_state(self):
        # Clear world objects
        self.world.units.clear()
        self.world.structures.clear()
        self.world.projectiles.clear()
        self.world.obstacles.clear()
        self.world.bombs.clear()
        self.explosion_effects.clear()
        
        # Reset game states
        self.is_game_over = False
        self.winner_player_id = None
        self.is_shop_open = False
        self.is_dragging = False
        self.is_paused = False
        self.pause_initiator = False
        self.pause_overlay = None
        
        # Reset camera
        self.camera.x = 0
        self.camera.y = 0
        
        # Reset Network variables
        if hasattr(self.screen_manager.network, 'latest_positions'):
            self.screen_manager.network.latest_positions.clear()
        
        self.is_arcade = False
        self.timer_seconds = Config.ARCADE_GAME_DURATION
        self.last_kill_world = None
        self.kill_gold_floats.clear()
        self.immune_floats.clear()
        self.tutorial = TutorialOverlay(self.screen)

    def set_arcade_mode(self, enabled=True):
        self.is_arcade = enabled
        self.shop.set_arcade_mode(enabled)
        self.timer_seconds = Config.ARCADE_GAME_DURATION
        if enabled:
            self.tutorial = TutorialOverlay(self.screen)
            self.tutorial.check_triggers("game_start")

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

        target_x, target_y = None, None
        for s_id, structure in self.world.structures.items():
            if self.world.get_owner_from_id(s_id) == self.player_Id:
                target_x, target_y = structure.x, structure.y
                break

        if target_x is None:
            if self.player_Id == 1:
                target_x, target_y = 300, 4700
            else:
                target_x, target_y = 4700, 300

        self.camera.x = target_x - self.camera.screen_width // 2
        self.camera.y = target_y - self.camera.screen_height // 2
        self.camera.x = max(0, min(self.camera.x, self.camera.map_width - self.camera.screen_width))
        self.camera.y = max(0, min(self.camera.y, self.camera.map_height - self.camera.screen_height))

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
        AudioManager().resume_music()
        self.is_paused = False
        self.pause_initiator = False
        if self.pause_overlay:
            self.pause_overlay.state = None
        self.is_game_over = True
        self.winner_player_id = winner_name

        self.screen_manager.network.disconnect()

        if hasattr(self.screen_manager, "container_manager") and self.screen_manager.container_manager:
            self.screen_manager.container_manager.stop()

        nuevo_texto = f"SHARP BLAZE\n{self.winner_player_id} VICTORY!"
        self.winner_box.update_text(nuevo_texto)
        
    def trigger_disconnect(self):
        self.is_paused = False
        self.pause_initiator = False
        if self.pause_overlay:
            self.pause_overlay.state = None
        self.is_game_over = True
        nuevo_texto = f"GAME\nDISCONNECTED!"
        self.winner_box.update_text(nuevo_texto)

        if hasattr(self.screen_manager, "container_manager") and self.screen_manager.container_manager:
            self.screen_manager.container_manager.stop()

    def handle_events(self, events, keys):
        """Processes one-time events like mouse clicks."""
        for event in events:

            # ESC toggle: open the pause menu (close only via RESUME button)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.is_game_over:
                    pass  # Game over takes priority over pause
                elif self.pause_overlay and self.pause_overlay.state == "SURRENDER_CONFIRM":
                    # ESC during surrender confirmation closes dialog only
                    self.pause_overlay.state = "MAIN"
                elif self.pause_overlay and self.pause_overlay.state == "VOLUME":
                    # ESC during volume submenu returns to main
                    self.pause_overlay.state = "MAIN"
                elif not self.is_paused:
                    # Open the pause menu (send PAUSE to server)
                    self.is_paused = True
                    self.pause_initiator = True
                    if self.pause_overlay is None:
                        self.pause_overlay = PauseOverlay(self.screen, self.screen_manager, AudioManager())
                    else:
                        self.pause_overlay.state = "MAIN"
                    self.pause_overlay.is_initiator = True
                    AudioManager().play_click()
                    AudioManager().stop_music()
                    if not Config.OFFLINE_DEBUG_MODE:
                        self.screen_manager.network.send_json(JSON_Manager.get_pause_game(True))
                # else: ESC is ignored while paused (use RESUME button instead)

            if self.is_game_over:
                # Si el juego terminó, SOLO escuchamos clics izquierdos para el botón
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = event.pos

                    # Tu lógica exacta de detección:
                    if self.game_over_button.button_rectangle.collidepoint(mouse_pos):
                        AudioManager().play_click()
                        print("[GAME SCREEN] Return to Menu clicked!")
                        self.screen_manager.network.disconnect()
                        if hasattr(self.screen_manager, "container_manager") and self.screen_manager.container_manager:
                            self.screen_manager.container_manager.stop()
                        self.is_game_over = False
                        self.winner_player_id = None
                        self.screen_manager.change_screen("MAIN")
                continue

            if self.is_arcade and self.tutorial.is_active():
                if self.tutorial.handle_event(event):
                    continue

            # Delegate events to pause overlay (initiator only)
            if self.is_paused and not self.is_game_over:
                if self.pause_initiator and self.pause_overlay:
                    action = self.pause_overlay.handle_events([event])
                    if action == "resume":
                        self.is_paused = False
                        self.pause_initiator = False
                        self.pause_overlay.state = None
                        AudioManager().resume_music()
                        if not Config.OFFLINE_DEBUG_MODE:
                            self.screen_manager.network.send_json(JSON_Manager.get_pause_game(False))
                    elif action == "surrender_confirm":
                        if not Config.OFFLINE_DEBUG_MODE:
                            self.screen_manager.network.send_json(JSON_Manager.get_surrender())
                        self.is_paused = False
                        self.pause_initiator = False
                        if self.pause_overlay:
                            self.pause_overlay.state = None
                # Non-initiator: ignore all input during pause
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
                        elif action == "BUY_BOMB":
                            print("[GAME] Sending TCP command to buy Bomb...")
                            self.screen_manager.network.send_json(JSON_Manager.get_unit_bomb())

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
                    if self.is_arcade:
                        self.tutorial.check_triggers("first_move")
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
                        if self.is_arcade:
                            self.tutorial.check_triggers("shop_open")
                        print("[GAME SCREEN] Shop selected! Opening UI.")
                    else:
                        self.is_shop_open = False

    def handle_entity_death(self, entity_id: int):

        if entity_id in self.world.units:
            del self.world.units[entity_id]
            print(f"[WORLD] Unit {entity_id} destroyed and removed.")

        elif entity_id in self.world.structures:
            del self.world.structures[entity_id]
            print(f"[WORLD] Structure {entity_id} destroyed and removed.")

        elif entity_id in self.world.bombs:
            bomb = self.world.bombs[entity_id]
            self.explosion_effects.append({
                "x": bomb.x,
                "y": bomb.y,
                "start_time": pygame.time.get_ticks(),
                "duration": 500,
            })
            del self.world.bombs[entity_id]
            print(f"[WORLD] Bomb {entity_id} destroyed and removed.")

        self.update_unit_counts()

    def update(self):

        if self.is_game_over:
            return

        if not Config.OFFLINE_DEBUG_MODE:
            while True:
                data = self.screen_manager.network.receive_json()
                if not data:
                    break

                print(data)

                if data.get("type") == "GAME_PAUSED":
                    paused_by = data["payload"].get("paused_by", -1)
                    self.is_paused = True
                    self.pause_initiator = (paused_by == self.player_Id)
                    if self.pause_initiator:
                        if self.pause_overlay is None:
                            self.pause_overlay = PauseOverlay(self.screen, self.screen_manager, AudioManager())
                        self.pause_overlay.state = "MAIN"
                        self.pause_overlay.is_initiator = True
                    # Discard any UDP positions received just before/during pause
                    self.screen_manager.network.latest_positions.clear()
                    AudioManager().stop_music()

                elif data.get("type") == "GAME_RESUMED":
                    self.is_paused = False
                    self.pause_initiator = False
                    if self.pause_overlay:
                        self.pause_overlay.state = None
                    # Discard stale UDP positions accumulated during pause
                    self.screen_manager.network.latest_positions.clear()
                    AudioManager().resume_music()

                elif data.get("type") == "SHOP_AUTORIZATION":
                    self.shop_autorization = data["payload"]["authorized"]

                elif data.get("type") == "BUY_UNIT_RESULT":
                    if data["status"] == "accepted":
                        self.new_unit_id = data["payload"]["unit_id"]
                        self.new_spawn_x = data["payload"]["spawn_x"]
                        self.new_spawn_y = data["payload"]["spawn_y"]
                        self.new_gold = data["payload"]["new_balance"]

                        is_bomb = data["payload"].get("unit_type", "") == "Bomb"

                        self.world.spawn_unit(self.new_unit_id,self.new_spawn_x,self.new_spawn_y)
                        self.update_unit_counts()

                        if is_bomb and self.is_arcade:
                            self.infobox_bomb.update_text(str(int(self.infobox_bomb.text_variable) + 1))
                            self.tutorial.check_triggers("bomb_purchased")

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

                elif data.get("type") == "TIMER_UPDATE":
                    self.timer_seconds = data["payload"]["remaining_seconds"]

                elif data.get("type") == "RESOURCES":

                    self.new_gold = data["payload"]["new_balance"]
                    gold_diff = self.new_gold - self.player_gold

                    if gold_diff > 0 and self.is_arcade and self.last_kill_world is not None:
                        gold_per_entity = Config.ARCADE_KILL_GOLD_UNIT
                        bomb_gold = Config.ARCADE_KILL_GOLD_BOMB
                        if gold_diff >= bomb_gold:
                            text = f"+{bomb_gold}"
                        else:
                            text = f"+{gold_diff}"
                        world_x, world_y = self.last_kill_world
                        self.kill_gold_floats.append({
                            "text": text,
                            "world_x": world_x,
                            "world_y": world_y,
                            "alpha": 255,
                            "start_time": pygame.time.get_ticks(),
                            "duration": 1000,
                        })

                    self.player_gold = self.new_gold
                    self.previous_gold = self.player_gold
                    self.infobox_gold.update_text(str(self.player_gold))

                elif data.get("type") == "UNIT_DAMAGED":

                    self.target_entity_id = data["payload"]["target_entity_id"]
                    self.attacker_entity_id = data["payload"]["attacker_entity_id"]
                    self.target_current_hp = data["payload"]["current_hp"]

                    if self.is_arcade:
                        if self.target_current_hp <= 0:
                            self.tutorial.check_triggers("first_kill")

                    if 1000 <= self.target_entity_id <= 4999 or 6000 <= self.target_entity_id <= 9999:
                        self.world.units[self.target_entity_id].reduce_health(self.target_current_hp)

                    elif 0 <= self.target_entity_id <= 999 or 5000 <= self.target_entity_id <= 5999:
                        self.world.structures[self.target_entity_id].reduce_health(self.target_current_hp)

                    AudioManager().play_receive_shot()

                elif data.get("type") == "ATTACK_RESULT":
                    if data.get("status") == "accepted":
                        self.attacker_entity_id = data["payload"]["attacker_id"]
                        self.target_entity_id = data["payload"]["target_id"]

                        attacker = self.world.get_entity(self.attacker_entity_id)
                        target = self.world.get_entity(self.target_entity_id)

                        if attacker is not None and target is not None:
                            new_bullet = RectangularProjectile(
                                start_x=attacker.x,
                                start_y=attacker.y,
                                target_entity=target,
                                hp=0,
                            )
                            self.world.projectiles.append(new_bullet)
                            if self.is_arcade and self.target_entity_id in (0, 5000):
                                self.immune_floats.append({
                                    "world_x": target.x,
                                    "world_y": target.y,
                                    "alpha": 255,
                                    "start_time": pygame.time.get_ticks(),
                                    "duration": 800,
                                })
                                AudioManager().play_immune()
                            else:
                                AudioManager().play_shoot()

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

                    if id is not None and self.world.is_bomb_id(id):
                        AudioManager().play_explosion()

                    AudioManager().play_dead()

                    if id is not None and id in self.world.units:
                        self.last_kill_world = (self.world.units[id].x, self.world.units[id].y)

                    self.handle_entity_death(id)
                    self.screen_manager.network.latest_positions.pop(id,None)
                    
                elif data.get("type") == "DISCONNECTED":
                    self.trigger_disconnect()

        else:
            # DEBUG MODE
            if self.player_gold > 100:
                self.shop_autorization = True

        if self.is_paused:
            return

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

        if self.is_arcade:
            self.tutorial.update()
            if self.tutorial.is_active():
                return
            self._check_bomb_near_base()

        now = pygame.time.get_ticks()
        self.explosion_effects = [
            e for e in self.explosion_effects
            if now - e["start_time"] < e["duration"]
        ]
        self.immune_floats = [
            e for e in self.immune_floats
            if now - e["start_time"] < e["duration"]
        ]

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
        self._draw_explosion_effects()
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
        if self.is_arcade:
            self.infobox_bomb.draw(self.screen)
        else:
            self.infobox_hat.draw(self.screen)
        self.infobox_sword.draw(self.screen)

        if self.is_arcade:
            minutes = self.timer_seconds // 60
            seconds = self.timer_seconds % 60
            timer_text = f"{minutes}:{seconds:02d}"
            timer_surface = self.timer_font.render(timer_text, True, (255, 255, 255))
            timer_rect = timer_surface.get_rect()
            timer_rect.centerx = self.screen.get_width() // 2
            timer_rect.top = int(20 * (self.screen.get_height() / 720))
            self.screen.blit(timer_surface, timer_rect)

        now = pygame.time.get_ticks()
        for anim in self.kill_gold_floats[:]:
            elapsed = now - anim["start_time"]
            progress = elapsed / anim["duration"]
            if progress >= 1.0:
                self.kill_gold_floats.remove(anim)
                continue
            screen_x = int(anim["world_x"] - self.camera.x)
            screen_y = int(anim["world_y"] - self.camera.y) - int(40 * progress)
            alpha = int(255 * (1.0 - progress))
            font = pygame.font.Font(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "Anton-Regular.ttf"),
                int(28 * (self.screen.get_height() / 720)),
            )
            text_surf = font.render(anim["text"], True, (50, 220, 50))
            text_surf.set_alpha(alpha)
            text_rect = text_surf.get_rect(center=(screen_x, screen_y))
            self.screen.blit(text_surf, text_rect)

        for anim in self.immune_floats[:]:
            elapsed = now - anim["start_time"]
            progress = elapsed / anim["duration"]
            if progress >= 1.0:
                self.immune_floats.remove(anim)
                continue
            screen_x = int(anim["world_x"] - self.camera.x)
            screen_y = int(anim["world_y"] - self.camera.y) - int(40 * progress)
            alpha = int(255 * (1.0 - progress))
            font = pygame.font.Font(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "Anton-Regular.ttf"),
                int(32 * (self.screen.get_height() / 720)),
            )
            text_surf = font.render("IMMUNE", True, (255, 50, 50))
            text_surf.set_alpha(alpha)
            text_rect = text_surf.get_rect(center=(screen_x, screen_y))
            self.screen.blit(text_surf, text_rect)

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

        # Draw pause overlay or message box
        if self.is_paused and not self.is_game_over:
            if self.pause_initiator and self.pause_overlay:
                self.pause_overlay.draw(self.screen)
            else:
                self._draw_game_paused_message()

        if self.is_arcade:
            self.tutorial.draw()

    def _draw_game_paused_message(self):
        """Draw a simple gray message box for the non-initiator player during pause."""
        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        box_w = int(800 * sx)
        box_h = int(220 * sy)
        box_x = (self.screen.get_width() - box_w) // 2
        box_y = (self.screen.get_height() - box_h) // 2

        box_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box_surface.fill((40, 40, 50, 230))
        self.screen.blit(box_surface, (box_x, box_y))

        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(CURRENT_DIR, "..", "assets", "Anton-Regular.ttf")
        font_size = int(85 * sy)
        font = pygame.font.Font(font_path, font_size)
        text_surface = font.render("GAME PAUSED", True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
        self.screen.blit(text_surface, text_rect)

    def _check_bomb_near_base(self):
        if self.tutorial.disabled or self.tutorial.is_active():
            return
        enemy_base = None
        for s_id, structure in self.world.structures.items():
            owner = self.world.get_owner_from_id(s_id)
            if owner is not None and owner != self.player_Id:
                if 0 <= s_id <= 999 or 5000 <= s_id <= 5999:
                    enemy_base = structure
                    break
        if enemy_base is None:
            return
        for b_id, bomb in self.world.bombs.items():
            dx = bomb.x - enemy_base.x
            dy = bomb.y - enemy_base.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 500:
                self.tutorial.check_triggers("bomb_near_base")
                break

    def _draw_explosion_effects(self):
        now = pygame.time.get_ticks()
        for effect in self.explosion_effects:
            elapsed = now - effect["start_time"]
            progress = elapsed / effect["duration"]

            screen_x = int(effect["x"] - self.camera.x)
            screen_y = int(effect["y"] - self.camera.y)

            max_radius = 60
            radius = int(max_radius * progress)
            alpha = int(255 * (1.0 - progress))

            explosion_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            color = (255, int(160 * (1.0 - progress)), 0, alpha)
            pygame.draw.circle(explosion_surface, color, (radius, radius), radius)
            self.screen.blit(explosion_surface, (screen_x - radius, screen_y - radius))
