import pygame
import math


class Minimap:
    def __init__(self, screen_width, screen_height, map_width, map_height):
        # 1. Round Minimap Geometry
        self.radius = 100
        self.margin = 20

        # Calculate the center of the circle (bottom right corner)
        self.cx = screen_width - self.radius - self.margin
        self.cy = screen_height - self.radius - self.margin

        # 2. Scale factors (Diameter is 2 * radius)
        self.scale_x = (self.radius * 2) / map_width
        self.scale_y = (self.radius * 2) / map_height

        # UI Colors
        self.bg_color = (0, 0, 0)  # Black background
        self.border_color = (255, 255, 255)  # White border
        self.camera_color = (0, 255, 0)  # Green rectangle

        # -------------------------------------------------------------
        # THE MASKING SETUP
        # -------------------------------------------------------------
        self.surface_size = self.radius * 2

        # We create a local rectangular surface with transparency (SRCALPHA)
        self.minimap_surface = pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)

        # We create the mask (A solid white circle with transparent background)
        self.mask_surface = pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)
        pygame.draw.circle(self.mask_surface, (255, 255, 255, 255), (self.radius, self.radius), self.radius)

    def handle_click(self, mouse_x, mouse_y, camera):
        """Translates a click on the minimap to camera movement in the world."""
        # Calculate the Euclidean distance from the click to the center of the minimap
        distance_to_center = math.hypot(mouse_x - self.cx, mouse_y - self.cy)

        # If the click was INSIDE the minimap circle
        if distance_to_center <= self.radius:
            # 1. Get the relative coordinate inside the minimap square bounding box
            rel_x = mouse_x - (self.cx - self.radius)
            rel_y = mouse_y - (self.cy - self.radius)

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

        # 1. Clear the local surface completely (make it transparent)
        self.minimap_surface.fill((0, 0, 0, 0))

        # A. Draw the black background of the minimap
        pygame.draw.circle(self.minimap_surface, self.bg_color, (self.radius, self.radius), self.radius)

        # B. Draw the entities
        for entity in world.units.values():
            # Using local coordinates (from 0 to surface_size)
            local_x = int(entity.x * self.scale_x)
            local_y = int(entity.y * self.scale_y)
            pygame.draw.circle(
                self.minimap_surface, entity.color, (local_x, local_y), 3
            )

        # 4. Draw the camera rectangle
        # It doesn't matter if it pokes out of the circle here!
        cam_local_x = int(camera.x * self.scale_x)
        cam_local_y = int(camera.y * self.scale_y)
        cam_local_w = int(camera.screen_width * self.scale_x)
        cam_local_h = int(camera.screen_height * self.scale_y)

        pygame.draw.rect(self.minimap_surface,self.camera_color,(cam_local_x, cam_local_y, cam_local_w, cam_local_h),1,)

        # 5. THE MAGIC: Apply the circular mask
        # BLEND_RGBA_MULT erases any pixels on the minimap_surface that are 
        # transparent on the mask_surface. This cuts off the green corners!
        self.minimap_surface.blit(self.mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # 6. Draw the thick white border on top to hide any rough edges
        pygame.draw.circle(self.minimap_surface, self.border_color, (self.radius, self.radius), self.radius, 4)

        # 7. Paste the finished, masked minimap onto the main game screen
        screen.blit(self.minimap_surface, (self.cx - self.radius, self.cy - self.radius))
