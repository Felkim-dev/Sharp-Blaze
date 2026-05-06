import pygame
import math


class RectangularProjectile:
    def __init__(self, start_x, start_y, target_entity, hp, speed=20):
        # 1. Posición y Físicas
        self.pos = pygame.math.Vector2(start_x, start_y)
        self.target = target_entity
        self.speed = speed

        # 2. El Cargamento (El daño que viaja con la bala)
        self.hp= hp
        self.is_dead = False

        # 3. Diseño visual (Un láser/bala rectangular)
        self.width = 15
        self.height = 4
        self.color = (255, 200, 0)  # Amarillo/Naranja

        # Creamos una superficie transparente y dibujamos el rectángulo base
        self.base_image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.base_image.fill(self.color)

    def update(self):
        if self.is_dead or not self.target:
            return

        # Vector de dirección hacia el objetivo
        target_pos = pygame.math.Vector2(self.target.x, self.target.y)
        direction_vector = target_pos - self.pos
        distance = direction_vector.length()

        # -------------------------------------------------------------
        # EL MOMENTO DEL IMPACTO (Sincronización visual)
        # -------------------------------------------------------------
        if distance < self.speed:
            self.pos = target_pos
            self.is_dead = True
        else:
            # Mover la bala
            direction_vector.normalize_ip()
            self.pos += direction_vector * self.speed

    def draw(self, screen, camera):
        if self.is_dead:
            return

        # 1. Calcular el ángulo de rotación hacia el objetivo
        dx = self.target.x - self.pos.x
        dy = self.target.y - self.pos.y
        # Pygame invierte el eje Y, por eso usamos -dy
        angle = math.degrees(math.atan2(-dy, dx))

        # 2. Rotar la imagen rectangular
        rotated_image = pygame.transform.rotate(self.base_image, angle)

        # 3. Trasladar a coordenadas de cámara y centrar el rectángulo rotado
        screen_x = int(self.pos.x - camera.x)
        screen_y = int(self.pos.y - camera.y)

        rect = rotated_image.get_rect(center=(screen_x, screen_y))
        screen.blit(rotated_image, rect)
