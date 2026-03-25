import pygame
from ui.component import Button
import sys

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

        # Calculate Pos
        width_button = BUTTON_WH[0]
        center_x = self.screen.get_rect().centerx - (width_button //2)

        init_y = 310
        separation_y = 60

        # Buttons declarations
        self.btn_host = Button((center_x, init_y + separation_y * 0), BUTTON_WH, LIGHT_BLUE,"Host Game", BLACK, TEXT_SIZE)
        self.btn_join = Button((center_x, init_y + separation_y * 1), BUTTON_WH, LIGHT_BLUE, "Join Game", BLACK, TEXT_SIZE)
        self.btn_bot = Button((center_x, init_y + separation_y * 2), BUTTON_WH, LIGHT_BLUE, "Bot Match", BLACK, TEXT_SIZE)
        self.btn_options = Button((center_x, init_y + separation_y * 3), BUTTON_WH, LIGHT_BLUE, "Options", BLACK, TEXT_SIZE)
        self.btn_exit = Button((center_x, init_y + separation_y * 4), BUTTON_WH, RED, "Exit", BLACK, TEXT_SIZE)

    def handle_events(self, events):

        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                if self.btn_host.button_rectangle.collidepoint(mouse_pos):
                    print("Cambiando a pantalla HOST...")

                elif self.btn_join.button_rectangle.collidepoint(mouse_pos):
                    print("Cambiando a pantalla JOIN...")

                elif self.btn_bot.button_rectangle.collidepoint(mouse_pos):
                    print("Iniciando partida BOT MATCH...")

                elif self.btn_options.button_rectangle.collidepoint(mouse_pos):
                    print("Abriendo OPCIONES...")

                elif self.btn_exit.button_rectangle.collidepoint(mouse_pos):
                    print("Saliendo del juego...")
                    pygame.quit()
                    sys.exit()

            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos

                self.btn_host.check_hover(mouse_pos)
                self.btn_join.check_hover(mouse_pos)
                self.btn_bot.check_hover(mouse_pos)
                self.btn_options.check_hover(mouse_pos)
                self.btn_exit.check_hover(mouse_pos)

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
        text_font = pygame.font.Font(r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\assets\Anton-Regular.ttf",100)
        text_surface = text_font.render("SHARP BLAZE", True, self.WHITE)
        title_rect = text_surface.get_rect(center = (self.screen.get_rect().centerx, 180))
        self.screen.blit(text_surface,title_rect)
