import pygame
import random
import math


class FloatingShape:
    def __init__(self, screen_width, screen_height):
        # 1. Random start position across the whole screen
        self.x = random.randint(0, screen_width)
        self.y = random.randint(0, screen_height)

        # Colors from your image: Cyan, Magenta, Yellow, Red

        CYAN_BLUE = (0, 212, 255),  # Cyan
        PINK_MAGENTA = (227, 0, 255),  # Magenta
        YELLOW = (233, 246, 14),  # Yellow
        CRIMSON_RED = (255, 0, 85),  # Crimson Red

        # Random properties based on your Sharp Blaze aesthetic
        self.shape_type = random.choice(
            ["square", "circle", "triangle", "diamond", "star"]
        )

        #Assign color based strictly on the shape type
        if self.shape_type == "diamond":
            self.color = PINK_MAGENTA
            
        elif self.shape_type == "star":
            self.color = YELLOW
            
        else:
            # For square, triangle, and circle, pick randomly between Red and Blue
            self.color = random.choice([CRIMSON_RED, CYAN_BLUE])
            
        self.size = random.randint(8, 20)

        # 3. Simple floating physics (drift speed)
        self.speed_x = random.uniform(-0.5, 0.5)
        self.speed_y = random.uniform(-0.5, 0.5)

    def update(self, screen_width, screen_height):
        """Moves the shape and wraps it around the screen if it goes out of bounds."""
        self.x += self.speed_x
        self.y += self.speed_y

        # Screen wrap-around logic (Pac-Man style)
        margin = 50
        if self.x > screen_width + margin:
            self.x = -margin
        elif self.x < -margin:
            self.x = screen_width + margin

        if self.y > screen_height + margin:
            self.y = -margin
        elif self.y < -margin:
            self.y = screen_height + margin

    def draw(self, screen):
        """Renders the specific geometric shape directly to the screen."""
        ix, iy = int(self.x), int(self.y)

        if self.shape_type == "circle":
            pygame.draw.circle(screen, self.color, (ix, iy), self.size)

        elif self.shape_type == "square":
            rect = (ix - self.size, iy - self.size, self.size * 2, self.size * 2)
            pygame.draw.rect(screen, self.color, rect)

        elif self.shape_type == "triangle":
            p1 = (ix, iy - self.size)
            p2 = (ix - self.size, iy + self.size)
            p3 = (ix + self.size, iy + self.size)
            pygame.draw.polygon(screen, self.color, [p1, p2, p3])

        elif self.shape_type == "diamond":
            p1 = (ix, iy - self.size)
            p2 = (ix + self.size, iy)
            p3 = (ix, iy + self.size)
            p4 = (ix - self.size, iy)
            pygame.draw.polygon(screen, self.color, [p1, p2, p3, p4])

        elif self.shape_type == "star":
            star_points = []
            angle = math.pi / 2 * 3
            angle_increment = math.pi / 5
            for i in range(10):
                radius = self.size if i % 2 == 0 else self.size / 2
                px = ix + math.cos(angle) * radius
                py = iy + math.sin(angle) * radius
                star_points.append((px, py))
                angle += angle_increment
            pygame.draw.polygon(screen, self.color, star_points)
