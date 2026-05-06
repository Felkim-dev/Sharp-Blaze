import pygame
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENTS_FONT = os.path.join(CURRENT_DIR, "..", "assets", "IntroRust.otf")

class TelemetryPanel:
    def __init__(self, screen_width, screen_height):
        BASE_W, BASE_H = 1280, 720
        sx = screen_width / BASE_W
        sy = screen_height / BASE_H

        self.width = int(220 * sx)
        self.height = int(110 * sy)
        self.x = screen_width - self.width - int(20 * sx)
        self.y = int(20 * sy)

        pygame.font.init()
        font_size = int(14 * sy)
        self.font = pygame.font.Font(COMPONENTS_FONT, font_size)

        self.bg_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.bg_surface.fill((40, 40, 45, 200))

        self.rtt_ms = 0
        self.last_ping_time = 0

        self.pad_x = int(12 * sx)
        self.line_height = int(22 * sy)
        self.pad_y_start = int(8 * sy)

    def draw(self, screen, clock, network_manager):
        screen.blit(self.bg_surface, (self.x, self.y))

        current_fps = int(clock.get_fps())

        if hasattr(network_manager, "current_rtt"):
            self.rtt_ms = int(network_manager.current_rtt)

        udp_recv = getattr(network_manager, "udp_packets_received", 0)
        udp_loss = getattr(network_manager, "udp_timeouts", 0)
        tcp_sent = getattr(network_manager, "tcp_messages_sent", 0)
        tcp_recv = getattr(network_manager, "tcp_messages_received", 0)

        text_color = (200, 200, 200)
        gold_color = (255, 215, 0)

        lines = [
            (f"FPS: {current_fps}", text_color),
            (f"LATENCY: {self.rtt_ms}ms", gold_color if self.rtt_ms > 100 else text_color),
            (f"UDP  OK:{udp_recv}  LOSS:{udp_loss}", text_color),
            (f"TCP  OUT:{tcp_sent}  IN:{tcp_recv}", text_color),
        ]

        for i, (text_str, color) in enumerate(lines):
            text_surface = self.font.render(text_str, True, color)
            y_pos = self.y + self.pad_y_start + (i * self.line_height)
            screen.blit(text_surface, (self.x + self.pad_x, y_pos))
