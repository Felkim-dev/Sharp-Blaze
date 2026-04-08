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

        self.width = 300
        self.height = 300
        
    def draw(self,screen,camera_x,camera_y):

        #CAMERA MOVEMENTE
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)
        
        if (-self.width < screen_x < screen.get_width()+self.width) and (-self.height < screen_y < screen.get_height()+self.height):
            
            rect_x = screen_x - (self.width//2)
            rect_y = screen_y - (self.height//2)
            
            self.rectangle = pygame.Rect((rect_x,rect_y), (self.width,self.height))
            pygame.draw.rect(screen,self.color,self.rectangle)

class GoldMine(Structures):
    def __init__(self, structure_id, final_x, final_y):
        super().__init__(structure_id, final_x, final_y)
        self.color = (233, 246, 14) #YELLOW
        self.inner_radius = 25
        self.outer_radius = 50
        self.points = 5 

    def draw(self,screen,camera_x,camera_y):
        """Draw a star"""
        
        screen_x = int(self.x-camera_x)
        screen_y = int(self.y-camera_y)


        if (-self.outer_radius < screen_x < screen.get_width()+self.outer_radius) and (-self.outer_radius < screen_y < screen.get_height()+self.outer_radius):
            
            star_points = []
            angle = math.pi / 2 * 3 
            angle_increment = math.pi / self.points

            for i in range(2 * self.points):
                radius = self.outer_radius if i % 2 == 0 else self.inner_radius
                px = int(self.x + math.cos(angle) * radius - camera_x)
                py = int(self.y + math.sin(angle) * radius - camera_y)

                # CAMERA MOVEMENT
                
                star_points.append((px, py))
                angle += angle_increment

            

            pygame.draw.polygon(screen, self.color, star_points)


class Shop(Structures):
    def __init__(self, structure_id, final_x, final_y):
        super().__init__(structure_id, final_x, final_y)

        self.size = 50
        self.color = (227, 0, 255) #PINK

    def draw(self,screen,camera_x, camera_y):

        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        if (-self.size < screen_x < screen.get_width() + self.size) and (-self.size < screen_y < screen.get_height() + self.size):
            diamond_points = [
                (screen_x, screen_y - self.size),  # Superior
                (screen_x + self.size, screen_y),  # Derecha
                (screen_x, screen_y + self.size),  # Inferior
                (screen_x - self.size, screen_y),  # Izquierda
            ]

            pygame.draw.polygon(screen, self.color, diamond_points)
        
