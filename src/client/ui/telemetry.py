import pygame
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENTS_FONT = os.path.join(CURRENT_DIR, "..", "assets", "IntroRust.otf")

class TelemetryPanel:
    def __init__(self, screen_width, screen_height):
        # SCALE FACTORS relative to base resolution 1280x720
        BASE_W, BASE_H = 1280, 720
        sx = screen_width / BASE_W
        sy = screen_height / BASE_H

        # 1. Panel Dimensions and Position (Top Right Corner, scaled)
        self.width = int(180 * sx)
        self.height = int(60 * sy)
        self.x = screen_width - self.width - int(20 * sx)
        self.y = int(20 * sy)

        # 2. Pygame Font setup (scaled)
        pygame.font.init()
        font_size = int(16 * sy)
        self.font = pygame.font.Font(COMPONENTS_FONT, font_size)

        # 3. Create a semi-transparent dark surface
        self.bg_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.bg_surface.fill((40, 40, 45, 200))  # RGBA: Dark grey with 200/255 opacity

        # 4. Networking Variables
        self.rtt_ms = 0
        self.last_ping_time = 0

        # Store padding for text placement (scaled)
        self.pad_x = int(15 * sx)
        self.pad_y1 = int(10 * sy)
        self.pad_y2 = int(30 * sy)

    def draw(self, screen, clock, network_manager):
        """Draws the telemetry panel on the screen."""

        # A. Paste the semi-transparent background
        screen.blit(self.bg_surface, (self.x, self.y))

        # B. Get current FPS from Pygame's clock
        current_fps = int(clock.get_fps())

        # C. Read the latest RTT from the network manager (if implemented)
        # Assuming your NetworkManager has a property 'current_rtt'
        if hasattr(network_manager, "current_rtt"):
            self.rtt_ms = int(network_manager.current_rtt)

        # D. Render the text strings
        text_color = (200, 200, 200)  # Light grey

        latency_text = self.font.render(f"LATENCY: {self.rtt_ms}MS", True, text_color)
        fps_text = self.font.render(f"FPS: {current_fps}", True, text_color)

        # E. Draw the text inside the panel box
        screen.blit(latency_text, (self.x + self.pad_x, self.y + self.pad_y1))
        screen.blit(fps_text, (self.x + self.pad_x, self.y + self.pad_y2))
