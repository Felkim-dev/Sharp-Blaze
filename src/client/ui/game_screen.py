import pygame
import math
import struct

from engine.world import GameWorld
from engine.camera import Camera
from ui.minimap import Minimap

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

    def load_initial_state(self, units, structures):
        self.world.build_initial_state(units,structures)

    def handle_events(self, events, keys):
        """Processes one-time events like mouse clicks."""
        for event in events:
            # Detect Mouse Button Press
            if event.type == pygame.MOUSEBUTTONDOWN:

                # event.button == 1 is Left Click
                if event.button == 1:
                    mouse_x, mouse_y = event.pos

                    # 1. UI PROTECTION: Check if click is on the Minimap first!
                    # Assuming your Minimap class has the geometry we built earlier
                    dist_to_minimap = math.hypot(
                        mouse_x - self.minimap.cx, mouse_y - self.minimap.cy
                    )
                    if dist_to_minimap <= self.minimap.radius:
                        # Click was inside the minimap UI, ignore world selection
                        continue

                    # 2. TRANSLATE: Screen Coordinates -> World Coordinates
                    world_x = mouse_x + self.camera.x
                    world_y = mouse_y + self.camera.y

                    # 3. EXECUTE: Tell the world to select units at this world coordinate
                    self.world.handle_left_click(world_x, world_y)

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
        self.screen.fill(self.MAINDARK)

        self.world.draw(self.screen, self.camera)

        self.minimap.draw(self.screen,self.world,self.camera)

        grosor = 5
        color_alerta = (255, 0, 0)  # Rojo

        # Variables auxiliares para no repetir código
        pantalla_w = self.screen.get_width()
        pantalla_h = self.screen.get_height()

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
