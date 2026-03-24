# ui/connection_screen.py
import pygame
from ui.component import Button

class MainScreen:
    def __init__(self, screen):
        self.screen = screen
        self.MAINDARK = (19,23,34)

        # Instanciar tus componentes según la HU-01
        # self.ip_input = InputBox(x, y, width, height, "IP Address")
        # self.id_input = InputBox(x, y, width, height, "Username")
        self.btn_host = Button((362,360),(0,212,255),(556,68.7), "Host Game",24)
        # self.btn_join = Button(x, y, "Join Game")

    def handle_events(self, events):
        # Aquí le pasas los eventos (clics, teclado) a tus inputs y botones
        pass

    def draw(self):
        self.screen.fill((self.MAINDARK))  # Fondo oscuro
        # self.ip_input.draw(self.screen)
        # self.id_input.draw(self.screen)
        self.btn_host.draw(self.screen)
