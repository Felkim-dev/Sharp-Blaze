import pygame
import time

COMPONENTS_FONT = r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\src\client\assets\IntroRust.otf"

class TelemetryPanel:
    def __init__(self, screen_width):
        # 1. Panel Dimensions and Position (Top Right Corner)
        self.width = 180
        self.height = 60
        self.x = screen_width - self.width - 20
        self.y = 20

        # 2. Pygame Font setup (Using a default bold font, similar to your image)
        pygame.font.init()
        self.font = pygame.font.SysFont(COMPONENTS_FONT, 16, bold=True)

        # 3. Create a semi-transparent dark surface
        self.bg_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.bg_surface.fill((40, 40, 45, 200))  # RGBA: Dark grey with 200/255 opacity

        # 4. Networking Variables
        self.rtt_ms = 0
        self.last_ping_time = 0

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
        screen.blit(latency_text, (self.x + 15, self.y + 10))
        screen.blit(fps_text, (self.x + 15, self.y + 30))
