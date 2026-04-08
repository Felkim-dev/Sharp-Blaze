import pygame
import math


class Minimap:
    def __init__(self, screen_width, screen_height, map_width, map_height):
        # 1. Square Minimap Geometry
        self.width = 200
        self.height = 200
        self.margin = 20

        # Calculate the top-left corner of the minimap (bottom right of the window)
        self.x = screen_width - self.width - self.margin
        self.y = screen_height - self.height - self.margin

        # We create a Pygame Rect for easy collision detection later
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # 2. Scale factors
        self.scale_x = self.width / map_width
        self.scale_y = self.height / map_height

        # UI Colors
        self.bg_color = (0, 0, 0)  # Black background
        self.border_color = (255, 255, 255)  # White border
        self.camera_color = (0, 255, 0)  # Green rectangle

    def handle_click(self, mouse_x, mouse_y, camera):
        """Translates a click on the minimap to camera movement in the world."""
        # Calculate the Euclidean distance from the click to the center of the minimap
        distance_to_center = math.hypot(mouse_x - self.cx, mouse_y - self.cy)

        # If the click was INSIDE the minimap square
        if distance_to_center <= self.radius:
            ## 1. Get the relative coordinate inside the minimap square bounding box
            rel_x = mouse_x - self.x
            rel_y = mouse_y - self.y

            # 2. Translate it to the giant world (Inverse rule of three)
            world_x = rel_x / self.scale_x
            world_y = rel_y / self.scale_y

            # 3. Center the camera on that world point
            camera.x = world_x - (camera.screen_width / 2)
            camera.y = world_y - (camera.screen_height / 2)

            # 4. Constrain the camera so it doesn't go out of bounds
            camera.move(0, 0)

            return True  # Return True to indicate the minimap was clicked

        return False

    def draw(self, screen, world, camera):

        # A. Draw the black background of the minimap directly to the main screen
        pygame.draw.rect(screen, self.bg_color, self.rect)

        # B. Draw the entities
        for entity in world.units.values():
            # Using absolute screen coordinates directly
            mini_x = int(self.x + (entity.x * self.scale_x))
            mini_y = int(self.y + (entity.y * self.scale_y))
            pygame.draw.circle(screen, entity.color, (mini_x, mini_y), 3)

        # 4. Draw the camera rectangle
        cam_mini_x = int(self.x + (camera.x * self.scale_x))
        cam_mini_y = int(self.y + (camera.y * self.scale_y))
        cam_mini_w = int(camera.screen_width * self.scale_x)
        cam_mini_h = int(camera.screen_height * self.scale_y)

        pygame.draw.rect(screen, self.camera_color, (cam_mini_x, cam_mini_y, cam_mini_w, cam_mini_h), 1)

        # 6. Draw the thick white border on top
        pygame.draw.rect(screen, self.border_color, self.rect, 4)
