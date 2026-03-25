# ui/connection_screen.py
import pygame
from ui.component import Button

class MainScreen:
    def __init__(self, screen):
        self.screen = screen

        # Colors
        self.MAINDARK = (19,23,34)
        self.WHITE = (255, 255, 255)
        LIGHT_BLUE = (0,212,255)
        BLACK = (0, 0, 0)
        RED = (204, 5, 35)

        # Button and Text Size
        BUTTON_WH = (350, 50)
        TEXT_SIZE = 24

        self.btn_host = Button((480, 310), BUTTON_WH, LIGHT_BLUE,"Host Game", BLACK, TEXT_SIZE)
        self.btn_join = Button((480, 370), BUTTON_WH, LIGHT_BLUE, "Join Game", BLACK, TEXT_SIZE)
        self.btn_bot = Button((480, 430), BUTTON_WH, LIGHT_BLUE, "Bot Match", BLACK, TEXT_SIZE)
        self.btn_options = Button((480, 490), BUTTON_WH, LIGHT_BLUE, "Options", BLACK, TEXT_SIZE)
        self.btn_exit = Button((480, 550), BUTTON_WH, RED, "Exit", BLACK, TEXT_SIZE)

    def handle_events(self, events):
        # Aquí le pasas los eventos (clics, teclado) a tus inputs y botones
        pass

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))  # Fondo oscuro

        # BUTTONS DRAW
        self.btn_host.draw(self.screen)
        self.btn_join.draw(self.screen)
        self.btn_bot.draw(self.screen)
        self.btn_options.draw(self.screen)
        self.btn_exit.draw(self.screen)

        # TEXT DRAW
        text_font = pygame.font.Font(r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\assets\Anton-Regular.ttf",80)
        text_surface = text_font.render("SHARP BLAZE", True, self.WHITE)
        self.screen.blit(text_surface,(460,140))
