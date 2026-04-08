import pygame
import math
import struct

from engine.world import GameWorld
from engine.camera import Camera
from ui.minimap import Minimap
from ui.telemetry import TelemetryPanel

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

    def load_initial_state(self, units, structures):
        self.world.build_initial_state(units,structures)

    def handle_events(self, events, keys):
        """Processes one-time events like mouse clicks."""
        for event in events:
            # Detect Mouse Button Press
            if event.type == pygame.MOUSEBUTTONDOWN:

                mouse_x, mouse_y = event.pos

                # 1. UI PROTECTION: Check if click is on the Square Minimap first!
                # We simply ask Pygame if the mouse coordinates are inside the minimap's Rect
                if self.minimap.rect.collidepoint(mouse_x, mouse_y):
                    # Click was inside the minimap UI, ignore world selection
                    continue

                # 2. TRANSLATE: Screen Coordinates -> World Coordinates
                world_x = mouse_x + self.camera.x
                world_y = mouse_y + self.camera.y

                # -------------------------------------------------------------
                # LEFT CLICK (Button 1) -> Select Units
                # -------------------------------------------------------------
                if event.button == 1:
                    self.world.handle_left_click(world_x, world_y)

                # -------------------------------------------------------------
                # RIGHT CLICK (Button 3) -> Issue Move Commands
                # -------------------------------------------------------------
                elif event.button == 3:
                    self.world.handle_right_click(world_x, world_y)

    def update(self):

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

        # ========================================================================================
