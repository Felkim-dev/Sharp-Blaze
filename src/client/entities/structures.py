import pygame
import math


class Structures:
    def __init__(self,structure_id,final_x,final_y):
        
        self.id = structure_id

        # Initial Position
        self.x = final_x
        self.y = final_y

        # Extra attributes
        self.hp = 1000
        self.color = (255, 255, 255)
        self.attackable = True
        
    def change_color(self,color):
        self.color = color

class Base(Structures):
    def __init__(self, structure_id, final_x, final_y):
        super().__init__(structure_id, final_x, final_y)

        self.width = 10
        self.height = 10
        
    def draw(self,screen):

        self.rectangle = pygame.Rect((self.x,self.y), (self.width,self.height))
        pygame.draw.rect(screen,self.color,self.rectangle)

class GoldMine(Structures):
    def __init__(self, structure_id, final_x, final_y):
        super().__init__(structure_id, final_x, final_y)
        self.color = (233, 246, 14) #YELLOW
        self.inner_radius = 5
        self.outer_radius = 10
        self.points = 5 
        self.star_points = []

    def draw(self,screen):
        """Draw a star"""

        angle = math.pi / 2 * 3 
        angle_increment = math.pi / self.points

        # Calculate 5 vertex (punta-valle-punta...)
        for i in range(2 * self.points):
            radius = self.outer_radius if i % 2 == 0 else self.inner_radius
            x = self.x + math.cos(angle) * radius
            y = self.y + math.sin(angle) * radius
            self.star_points.append((x, y))
            angle += angle_increment

        pygame.draw.polygon(screen, self.color, self.star_points)


class Shop(Structures):
    def __init__(self, structure_id, final_x, final_y):
        super().__init__(structure_id, final_x, final_y)

        self.size = 10
        self.points = []
        self.color = (227, 0, 255) #PINK
        
    def draw(self,screen):

        self.points = [
            (self.x, self.y - self.size),  # Superior
            (self.x + self.size, self.y),  # Right
            (self.x, self.y + self.size),  # Bottom
            (self.x - self.size, self.y),  # Left
        ]

        pygame.draw.polygon(screen,self.color,self.points,0)
