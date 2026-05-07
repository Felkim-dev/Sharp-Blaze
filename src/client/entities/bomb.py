import pygame
import os
import math

from ui.component import Health_Indicator

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BOMB_SPRITE_PATH = os.path.join(CURRENT_DIR, "..", "assets", "bomb.png")

CELL_SIZE = 50
BOMB_MAX_HP = 200


class Bomb:

    _sprite = None

    @classmethod
    def _load_sprite(cls):
        if cls._sprite is None:
            try:
                cls._sprite = pygame.image.load(BOMB_SPRITE_PATH).convert_alpha()
            except Exception as e:
                print(f"[BOMB] Could not load sprite: {e}")
                cls._sprite = pygame.Surface((40, 40), pygame.SRCALPHA)
                cls._sprite.fill((255, 100, 0, 180))
        return cls._sprite

    def __init__(self, entity_id, grid_x, grid_y):
        self.id = entity_id
        self.hp = BOMB_MAX_HP
        self.max_hp = BOMB_MAX_HP

        self.x, self.y = self._grid_to_world(grid_x, grid_y)

        self.sprite = self._load_sprite()
        self.sprite_size = self.sprite.get_width()

        self.health_bar = Health_Indicator(self.max_hp, self.sprite_size)

        self.is_selected = False
        self.is_targeted = False
        self.hitbox_radius = 25

    @staticmethod
    def _grid_to_world(grid_x, grid_y):
        world_x = grid_x * CELL_SIZE + (CELL_SIZE // 2)
        world_y = grid_y * CELL_SIZE + (CELL_SIZE // 2)
        return world_x, world_y

    def update_position(self, grid_x, grid_y):
        self.x, self.y = self._grid_to_world(grid_x, grid_y)

    def reduce_health(self, current_health):
        self.hp = min(self.hp, current_health)

    def check_click(self, world_click_x, world_click_y):
        distance = math.hypot(self.x - world_click_x, self.y - world_click_y)
        return distance <= self.hitbox_radius

    def draw(self, screen, camera):
        screen_x = int(self.x - camera.x)
        screen_y = int(self.y - camera.y)

        half = self.sprite_size // 2
        if not (-half < screen_x < screen.get_width() + half and
                -half < screen_y < screen.get_height() + half):
            return

        sprite_rect = self.sprite.get_rect(center=(screen_x, screen_y))
        screen.blit(self.sprite, sprite_rect)

        self.health_bar.draw(screen, self.hp, self.x, self.y, (camera.x, camera.y))
