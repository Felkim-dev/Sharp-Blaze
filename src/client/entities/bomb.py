import pygame
import math

from ui.component import Health_Indicator

CELL_SIZE = 50
BOMB_MAX_HP = 200

BOMB_RADIUS = 20
FUSE_WIDTH = 10
FUSE_HEIGHT = 18


class Bomb:

    def __init__(self, entity_id, world_x, world_y):
        self.id = entity_id
        self.hp = BOMB_MAX_HP
        self.max_hp = BOMB_MAX_HP

        self.x = float(world_x)
        self.y = float(world_y)

        self.health_bar = Health_Indicator(self.max_hp, BOMB_RADIUS * 2)

        self.is_selected = False
        self.is_targeted = False
        self.hitbox_radius = 25

        self.path_queue = []
        self.speed = 5.5

    def update_position(self, world_x, world_y):
        self.x = float(world_x)
        self.y = float(world_y)

    def reduce_health(self, current_health):
        self.hp = min(self.hp, current_health)

    def check_click(self, world_click_x, world_click_y):
        distance = math.hypot(self.x - world_click_x, self.y - world_click_y)
        return distance <= self.hitbox_radius

    def add_target_position(self, new_x, new_y):
        if len(self.path_queue) > 0:
            last_x, last_y = self.path_queue[-1]
            if last_x == new_x and last_y == new_y:
                return
        self.path_queue.append((new_x, new_y))

    def update_physics(self):
        if len(self.path_queue) > 0:
            current_target_x, current_target_y = self.path_queue[0]
            dx = current_target_x - self.x
            dy = current_target_y - self.y
            distance = math.hypot(dx, dy)
            if distance < 20.0:
                self.path_queue.pop(0)
            else:
                self.x += (dx / distance) * self.speed
                self.y += (dy / distance) * self.speed

    def draw(self, screen, camera):
        screen_x = int(self.x - camera.x)
        screen_y = int(self.y - camera.y)

        margin = BOMB_RADIUS + FUSE_HEIGHT
        if not (-margin < screen_x < screen.get_width() + margin and
                -margin < screen_y < screen.get_height() + margin):
            return

        fuse_top_y = screen_y - BOMB_RADIUS - FUSE_HEIGHT + 4
        fuse_rect = pygame.Rect(
            screen_x - FUSE_WIDTH // 2,
            fuse_top_y,
            FUSE_WIDTH,
            FUSE_HEIGHT,
        )
        pygame.draw.rect(screen, (255, 140, 0), fuse_rect, border_radius=3)

        spark_y = fuse_top_y - 4
        spark_color = (255, 200, 0) if (pygame.time.get_ticks() // 150) % 2 == 0 else (255, 80, 0)
        pygame.draw.circle(screen, spark_color, (screen_x, int(spark_y)), 4)

        pygame.draw.circle(screen, (0, 0, 0), (screen_x, screen_y), BOMB_RADIUS)
        pygame.draw.circle(screen, (40, 40, 40), (screen_x, screen_y), BOMB_RADIUS, 2)

        if self.is_selected:
            pygame.draw.circle(screen, (0, 255, 0), (screen_x, screen_y), self.hitbox_radius + 2, 2)
        elif self.is_targeted:
            pygame.draw.circle(screen, (255, 0, 0), (screen_x, screen_y), self.hitbox_radius + 2, 2)

        self.health_bar.draw(screen, self.hp, self.x, self.y, (camera.x, camera.y))
