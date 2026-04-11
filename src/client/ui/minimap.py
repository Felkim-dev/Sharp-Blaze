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

        # If the click was INSIDE the minimap square
        if self.rect.collidepoint(mouse_x, mouse_y):
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

        # B. Iterate through BOTH dictionaries (units and structures)
        # This prevents code duplication and keeps rendering efficient
        for entity_dictionary in (world.units, world.structures):
            for entity in entity_dictionary.values():

                # Scale coordinates to the minimap
                mini_x = int(self.x + (entity.x * self.scale_x))
                mini_y = int(self.y + (entity.y * self.scale_y))

                # Miniature icon size (radius/half-width)
                icon_size = 4

                # Get the exact class name of the object as a string
                entity_type = entity.__class__.__name__

                if entity_type == "Recolectors":
                    # Draw a standard Circle
                    pygame.draw.circle(
                        screen, entity.color, (mini_x, mini_y), icon_size
                    )

                elif entity_type == "Base":
                    # Draw a Square (centered on mini_x, mini_y)
                    base_rect = (
                        mini_x - icon_size,
                        mini_y - icon_size,
                        icon_size * 2,
                        icon_size * 2,
                    )
                    pygame.draw.rect(screen, entity.color, base_rect)

                elif entity_type == "Attacker":
                    # Draw an upward-pointing Triangle
                    p1 = (mini_x, mini_y - icon_size)
                    p2 = (mini_x - icon_size, mini_y + icon_size)
                    p3 = (mini_x + icon_size, mini_y + icon_size)
                    pygame.draw.polygon(screen, entity.color, [p1, p2, p3])

                elif entity_type == "Shop":
                    # Draw a Diamond (Rhombus)
                    p1 = (mini_x, mini_y - icon_size)
                    p2 = (mini_x + icon_size, mini_y)
                    p3 = (mini_x, mini_y + icon_size)
                    p4 = (mini_x - icon_size, mini_y)
                    pygame.draw.polygon(screen, entity.color, [p1, p2, p3, p4])

                elif entity_type == "GoldMine":
                    # Draw a miniature 5-point Star
                    star_points = []
                    angle = math.pi / 2 * 3
                    angle_increment = math.pi / 5

                    for i in range(10):
                        # Alternate between outer and inner radius
                        radius = icon_size if i % 2 == 0 else icon_size / 2
                        px = mini_x + math.cos(angle) * radius
                        py = mini_y + math.sin(angle) * radius
                        star_points.append((px, py))
                        angle += angle_increment

                    pygame.draw.polygon(screen, entity.color, star_points)

                else:
                    # Fallback just in case an unknown entity is added later
                    pygame.draw.circle(screen, entity.color, (mini_x, mini_y), 2)

        # 4. Draw the camera rectangle
        cam_mini_x = int(self.x + (camera.x * self.scale_x))
        cam_mini_y = int(self.y + (camera.y * self.scale_y))
        cam_mini_w = int(camera.screen_width * self.scale_x)
        cam_mini_h = int(camera.screen_height * self.scale_y)

        pygame.draw.rect(screen, self.camera_color, (cam_mini_x, cam_mini_y, cam_mini_w, cam_mini_h), 1)

        # 6. Draw the thick white border on top
        pygame.draw.rect(screen, self.border_color, self.rect, 4)
