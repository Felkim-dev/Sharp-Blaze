import pygame

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


class Attacker(Unit):
    def __init__(self, unit_id, start_x, start_y):
        super().__init__(unit_id, start_x, start_y)

        self.size = 10
        
    def get_points(self):
        # Calculate the vertex based on the central position x,y
        p1 = (self.x, self.y - self.size)
        p2 = (self.x - self.size, self.y + self.size)
        p3 = (self.x + self.size, self.y + self.size)
        return [p1, p2, p3]

    def draw(self,screen):
        """The unit is drawed"""

        self.points = self.get_points()

        pygame.draw.polygon(screen,self.color,self.points)


class Recolectors(Unit):
    def __init__(self, unit_id, start_x, start_y):
        super().__init__(unit_id, start_x, start_y)
        
    def draw(self,screen):
        
        pos_x = int(self.x)
        pos_y = int(self.y)
        
        pygame.draw.circle(screen, self.color, (pos_x,pos_y), 15)
