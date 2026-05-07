import pygame
import os
from ui.component import Button, Text, CloseButton
from utils.audio import AudioManager

class BotDifficultyScreen:
    def __init__(self, screen_manager, screen):
        self.screen_manager = screen_manager
        self.screen = screen

        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        self.MAINDARK = (19, 23, 34)
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.LIGHT_BLUE = (0, 212, 255)
        self.RED = (204, 5, 35)
        self.GRAY = (112, 112, 112)

        BUTTON_WH = (int(400 * sx), int(60 * sy))
        TEXT_SIZE = int(28 * sy)

        center_x = self.screen.get_rect().centerx - (BUTTON_WH[0] // 2)
        init_y = int(280 * sy)
        separation_y = int(80 * sy)

        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        TITLE_FONT = os.path.join(CURRENT_DIR, "..", "assets", "Anton-Regular.ttf")
        title_y = int(180 * sy)
        title_size = int(80 * sy)

        self.text_title = Text(
            (self.screen.get_rect().centerx, title_y),
            "SELECT DIFFICULTY", 
            title_size, 
            self.WHITE, 
            TITLE_FONT
        )

        self.btn_easy = Button(
            (center_x, init_y + separation_y * 0), 
            BUTTON_WH, 
            self.LIGHT_BLUE, 
            "EASY", 
            self.BLACK, 
            TEXT_SIZE
        )
        self.btn_medium = Button(
            (center_x, init_y + separation_y * 1), 
            BUTTON_WH, 
            self.LIGHT_BLUE, 
            "MEDIUM", 
            self.BLACK, 
            TEXT_SIZE
        )
        self.btn_hard = Button(
            (center_x, init_y + separation_y * 2), 
            BUTTON_WH, 
            self.LIGHT_BLUE, 
            "HARD", 
            self.BLACK, 
            TEXT_SIZE
        )

        button_size = int(30 * sy)
        margin = int(50 * sx)
        self.btn_close = CloseButton(
            self.screen.get_width() - button_size - margin, 
            margin, 
            button_size
        )

        self.selected_difficulty = None

    def handle_events(self, events, keys):
        for event in events:
            if self.btn_close.handle_event(event):
                AudioManager().play_click()
                self.screen_manager.change_screen("MAIN")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos
                    
                    if self.btn_easy.button_rectangle.collidepoint(mouse_pos):
                        self._start_bot_match("EASY")
                    
                    elif self.btn_medium.button_rectangle.collidepoint(mouse_pos):
                        self._start_bot_match("MEDIUM")
                    
                    elif self.btn_hard.button_rectangle.collidepoint(mouse_pos):
                        self._start_bot_match("HARD")

            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                self.btn_easy.check_hover(mouse_pos)
                self.btn_medium.check_hover(mouse_pos)
                self.btn_hard.check_hover(mouse_pos)

    def _start_bot_match(self, difficulty):
        AudioManager().play_click()
        self.selected_difficulty = difficulty
        print(f"[BotUI] Difficulty selected: {difficulty}")
        
        from ia import BotMatchController
        
        self.screen_manager.bot_controller = BotMatchController(
            difficulty,
            self.screen_manager.network,
            self.screen_manager
        )
        self.screen_manager.bot_controller.start_match()
        
        self.screen_manager.change_screen("LOBBY")

    def update(self):
        pass

    def draw(self):
        self.screen.fill(self.MAINDARK)
        self.text_title.draw(self.screen)
        self.btn_easy.draw(self.screen)
        self.btn_medium.draw(self.screen)
        self.btn_hard.draw(self.screen)
        self.btn_close.draw(self.screen)
