# ui/connection_screen.py
import pygame

# from ui.components import InputBox, Button # Si hiciste tus propios componentes

class ConnectionScreen:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 32)

        # Instanciar tus componentes según la HU-01
        # self.ip_input = InputBox(x, y, width, height, "IP Address")
        # self.id_input = InputBox(x, y, width, height, "Username")
        # self.btn_host = Button(x, y, "Host Game")
        # self.btn_join = Button(x, y, "Join Game")

    def handle_events(self, events):
        # Aquí le pasas los eventos (clics, teclado) a tus inputs y botones
        pass

    def draw(self):
        self.screen.fill((19, 23, 35))  # Fondo oscuro
        # self.ip_input.draw(self.screen)
        # self.id_input.draw(self.screen)
        # self.btn_host.draw(self.screen)
