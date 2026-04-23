import pygame
import sys
import os
import threading

from ui.component import Button, Text
from ui.floating_shapes import FloatingShape
from ia.bot_player import BotPlayer
from ia.bot_game_loop import BotGameLoop
from utils.config import Config

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

        # Create a list of background shapes (e.g., 25 floating shapes)
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        self.background_shapes = []
        for _ in range(25):
            shape = FloatingShape(self.screen_width, self.screen_height)
            self.background_shapes.append(shape)
        
        # Bot match state
        self.bot_instance = None
        self.bot_loop = None

    def handle_events(self, events,keys):

        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                # COLISSION WITH EACH BUTTON

                if self.btn_join.button_rectangle.collidepoint(mouse_pos):
                    self.screen_manager.change_screen("JOIN")

                elif self.btn_bot.button_rectangle.collidepoint(mouse_pos):
                    self._start_bot_match()

                elif self.btn_options.button_rectangle.collidepoint(mouse_pos):
                    print("Abriendo OPCIONES...")

                elif self.btn_exit.button_rectangle.collidepoint(mouse_pos):
                    pygame.quit()
                    sys.exit()

            elif event.type == pygame.MOUSEMOTION:

                # MOUSE ON BUTTON DETECTION
                mouse_pos = event.pos

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

        # BUTTONS DRAW
        self.btn_join.draw(self.screen)
        self.btn_bot.draw(self.screen)
        self.btn_options.draw(self.screen)
        self.btn_exit.draw(self.screen)

        # TEXT DRAW

        self.text_title.draw(self.screen)

    def _start_bot_match(self):
        """Initialize bot and connect both bot and player to server for bot match"""
        print("[MAIN_SCREEN] Starting Bot Match...")
        
        # Create bot player instance
        self.bot_instance = BotPlayer("SharpBlaze_Bot_1")
        
        # Connect bot in background thread
        def connect_bot():
            print("[MAIN_SCREEN] Bot connecting to server...")
            if self.bot_instance.connect():
                print("[MAIN_SCREEN] Bot connected successfully")
                # Store bot reference in screen manager for other screens
                self.screen_manager.bot_instance = self.bot_instance
            else:
                print("[MAIN_SCREEN] Bot connection failed")
        
        # Launch bot connection in thread to avoid blocking UI
        bot_thread = threading.Thread(target=connect_bot, daemon=True)
        bot_thread.start()
        
        # Now connect the player as well (using same protocol as join_screen)
        from utils.json import JSON_Manager
        player_join_data = JSON_Manager.get_datajoin("Player")
        
        print("[MAIN_SCREEN] Player connecting to server...")
        self.screen_manager.network.connect(player_join_data)
        
        # Move to connecting screen (player will wait there)
        self.screen_manager.change_screen("CONNECTING")
