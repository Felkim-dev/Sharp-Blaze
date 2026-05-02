import pygame
import sys
import os

from ui.component import Button, Text
from ui.floating_shapes import FloatingShape
from utils.audio import AudioManager

class MainScreen:
    def __init__(self, screen_manager,screen):
        # SCREEN FROM THE MAIN GAME LOOP
        self.screen_manager = screen_manager
        self.screen = screen

        # COLORS
        self.MAINDARK = (19,23,34)
        self.WHITE = (255, 255, 255)
        self.LIGHT_BLUE = (0,212,255)
        self.BLACK = (0, 0, 0)
        self.RED = (204, 5, 35)

        # Button and Text Size
        BUTTON_WH = (350, 50)
        TEXT_SIZE = 24

        # Calculating POSITION
        width_button = BUTTON_WH[0]
        center_x = self.screen.get_rect().centerx - (width_button //2)
        init_y = 310
        separation_y = 60

        # Buttons declarations
        self.btn_join = Button((center_x, init_y + separation_y * 0), BUTTON_WH, self.LIGHT_BLUE, "Join Game", self.BLACK, TEXT_SIZE)
        self.btn_bot = Button((center_x, init_y + separation_y * 1), BUTTON_WH, self.LIGHT_BLUE, "Bot Match", self.BLACK, TEXT_SIZE)
        self.btn_options = Button((center_x, init_y + separation_y * 2), BUTTON_WH, self.LIGHT_BLUE, "Options", self.BLACK, TEXT_SIZE)
        self.btn_exit = Button((center_x, init_y + separation_y * 3), BUTTON_WH, self.RED, "Exit", self.BLACK, TEXT_SIZE)

        # FONT
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        TITLE_FONT = os.path.join(CURRENT_DIR, "..","assets", "Anton-Regular.ttf")

        # TEXT
        self.text_title = Text((self.screen.get_rect().centerx, self.screen.get_rect().centery//2),"SHARP BLAZE", 100,self.WHITE,TITLE_FONT)

        # =====================================================
        # OPTIONS MENU
        # =====================================================
        self.show_options = False

        # OPTIONS TITLE (using Anton font)
        self.text_options_title = Text(
            (self.screen.get_rect().centerx, self.screen.get_rect().centery // 2),
            "OPTIONS", 100, self.WHITE, TITLE_FONT
        )

        # OPTIONS BUTTONS
        options_init_y = 310
        self.btn_volume = Button((center_x, options_init_y + separation_y * 0), BUTTON_WH, self.LIGHT_BLUE, "Volume", self.BLACK, TEXT_SIZE)
        self.btn_resolution = Button((center_x, options_init_y + separation_y * 1), BUTTON_WH, self.LIGHT_BLUE, "Resolution", self.BLACK, TEXT_SIZE)
        self.btn_credits = Button((center_x, options_init_y + separation_y * 2), BUTTON_WH, self.LIGHT_BLUE, "Credits", self.BLACK, TEXT_SIZE)
        self.btn_back = Button((center_x, options_init_y + separation_y * 3), BUTTON_WH, self.RED, "Back", self.BLACK, TEXT_SIZE)

        # Create a list of background shapes (e.g., 25 floating shapes)
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        self.background_shapes = []
        for _ in range(25):
            shape = FloatingShape(self.screen_width, self.screen_height)
            self.background_shapes.append(shape)

    def handle_events(self, events,keys):

        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                    if self.show_options:
                        # ---- OPTIONS MENU EVENT HANDLING ----

                        if self.btn_volume.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            print("Abriendo VOLUME...")

                        elif self.btn_resolution.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            print("Abriendo RESOLUTION...")

                        elif self.btn_credits.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            print("Abriendo CREDITS...")

                        elif self.btn_back.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.show_options = False

                    else:
                        # ---- MAIN MENU EVENT HANDLING ----

                        if self.btn_join.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.screen_manager.change_screen("JOIN")

                        elif self.btn_bot.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            print("Iniciando partida BOT MATCH...")

                        elif self.btn_options.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.show_options = True

                        elif self.btn_exit.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            pygame.quit()
                            sys.exit()

            elif event.type == pygame.MOUSEMOTION:

                mouse_pos = event.pos

                if self.show_options:
                    # HOVER DETECTION FOR OPTIONS BUTTONS
                    self.btn_volume.check_hover(mouse_pos)
                    self.btn_resolution.check_hover(mouse_pos)
                    self.btn_credits.check_hover(mouse_pos)
                    self.btn_back.check_hover(mouse_pos)
                else:
                    # HOVER DETECTION FOR MAIN MENU BUTTONS
                    self.btn_join.check_hover(mouse_pos)
                    self.btn_bot.check_hover(mouse_pos)
                    self.btn_options.check_hover(mouse_pos)
                    self.btn_exit.check_hover(mouse_pos)

    def update(self):
        for shape in self.background_shapes:
            shape.update(self.screen_width, self.screen_height)

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))  # Fondo oscuro

        # Figures
        for shape in self.background_shapes:
            shape.draw(self.screen)

        if self.show_options:
            # ---- OPTIONS MENU DRAW ----
            self.text_options_title.draw(self.screen)

            self.btn_volume.draw(self.screen)
            self.btn_resolution.draw(self.screen)
            self.btn_credits.draw(self.screen)
            self.btn_back.draw(self.screen)
        else:
            # ---- MAIN MENU DRAW ----
            self.btn_join.draw(self.screen)
            self.btn_bot.draw(self.screen)
            self.btn_options.draw(self.screen)
            self.btn_exit.draw(self.screen)

            # TEXT DRAW
            self.text_title.draw(self.screen)
