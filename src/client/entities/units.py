import pygame
import math

from ui.component import Health_Indicator

class Unit:
    def __init__(self, unit_id, start_x, start_y):

        self.id = unit_id

        # Initial Position
        self.x = start_x
        self.y = start_y

        # Final Position
        self.target_x = start_x
        self.target_y = start_y

        # Extra attributes
        self.hp = 100
        self.color = (255,255,255)

        # SELECTION
        self.is_selected = False
        self.is_targeted = False
        self.hitbox_radius = 20  # How forgiving the click detection is

    def update_target(self, new_x, new_y):
        '''Update where the unit will be move'''
        self.target_x = new_x
        self.target_y = new_y

    def change_color(self,color):
        self.color = color

    def update_physics(self):
        """LERP"""
        lerp_factor = 0.2
        self.x += (self.target_x - self.x) * lerp_factor
        self.y += (self.target_y - self.y) * lerp_factor

    def check_click(self, world_click_x, world_click_y):
        """Returns True if the world coordinates fall inside this unit's hitbox."""
        distance = math.hypot(self.x - world_click_x, self.y - world_click_y)
        return distance <= self.hitbox_radius

    def draw_selection_ring(self, screen, camera_x, camera_y):
        """Draws a green ring around the unit if it is selected."""
        if self.is_selected:
            screen_x = int(self.x - camera_x)
            screen_y = int(self.y - camera_y)

            # Draw a green circle with 2px thickness (outline only)
            pygame.draw.circle(
                screen, (0, 255, 0), (screen_x, screen_y), self.hitbox_radius + 2, 2
            )
    def reduce_health(self,current_health):
        self.hp = current_health


class Attacker(Unit):
    def __init__(self, unit_id, start_x, start_y):
        super().__init__(unit_id, start_x, start_y)

        self.size = 15
        self.health_bar = Health_Indicator(self.hp, self.size*2)

    def draw(self,screen, camera_x, camera_y):
        """The unit is drawed"""

        self.draw_selection_ring(screen, camera_x, camera_y)

        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        if (-self.size < screen_x < screen.get_width() + self.size) and (-self.size < screen_y < screen.get_height() + self.size):
            p1 = (screen_x, screen_y - self.size)
            p2 = (screen_x - self.size, screen_y + self.size)
            p3 = (screen_x + self.size, screen_y + self.size)

            pygame.draw.polygon(screen, self.color, [p1, p2, p3])
        
            self.health_bar.draw(screen,self.hp,self.x,self.y,(camera_x,camera_y))


class Recolectors(Unit):
    def __init__(self, unit_id, start_x, start_y):
        super().__init__(unit_id, start_x, start_y)

        self.radius = 15
        self.health_bar = Health_Indicator(self.hp, self.radius*2)

    def draw(self,screen,camera_x,camera_y):

        pos_x = int(self.x - camera_x)
        pos_y = int(self.y - camera_y)

        self.draw_selection_ring(screen, camera_x, camera_y)

        if (-self.radius < pos_x < screen.get_width() + self.radius) and (-self.radius < pos_y < screen.get_height() + self.radius):
            pygame.draw.circle(screen, self.color, (pos_x,pos_y), 15)

            self.health_bar.draw(screen, self.hp, self.x, self.y, (camera_x,camera_y))
