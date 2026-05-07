import pygame
import os

from ui.component import Button, Text, TextBox, CloseButton

from utils.audio import AudioManager


class ArcadeLobbyScreen:
    def __init__(self, screen_manager, screen):

        self.screen_manager = screen_manager
        self.screen = screen

        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        self.MAINDARK = (19, 23, 34)
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.GRAY = (112, 112, 112)
        self.LIGHT_BLUE = (0, 150, 255)

        TEXT_WH = (int(300 * sx), int(50 * sy))
        BUTTON_WH = (int(350 * sx), int(50 * sy))
        TEXT_SIZE = BUTTON_WH[1] // 2

        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        TITLE_FONT_PATH = os.path.join(
            CURRENT_DIR, "..", "assets", "Anton-Regular.ttf"
        )
        self.title_font = pygame.font.Font(TITLE_FONT_PATH, int(64 * sy))

        width_screen = self.screen.get_width()
        button_size = int(30 * sy)
        margin = int(50 * sx)
        pos_x = width_screen - button_size - margin
        pos_y = margin
        self.btn_close = CloseButton(pos_x, pos_y, button_size)

        width_button = BUTTON_WH[0]
        center_x_button = self.screen.get_rect().centerx - (width_button // 2)

        width_text = TEXT_WH[0]
        center_x_text_player1 = self.screen.get_rect().centerx - width_text * 1.5
        center_x_text_player2 = self.screen.get_rect().centerx + width_text // 2

        init_y = (self.screen.get_height() // 3) + int(50 * sy)

        self.btn_start = Button(
            (center_x_button, init_y + int(100 * sy)),
            BUTTON_WH,
            self.LIGHT_BLUE,
            "START GAME",
            self.BLACK,
            TEXT_SIZE,
        )

        size_text_boxes = int(25 * sy)
        self.textbox_you = TextBox(
            (center_x_text_player1, init_y),
            TEXT_WH,
            self.BLACK,
            "YOU",
            self.WHITE,
            size_text_boxes,
        )
        self.textbox_bot = TextBox(
            (center_x_text_player2, init_y),
            TEXT_WH,
            self.BLACK,
            "BOT",
            self.WHITE,
            size_text_boxes,
        )

        posx_text_player1 = center_x_text_player1 + width_text // 2
        posy_text_player1 = init_y - int(40 * sy)
        self.text_label_you = Text(
            (posx_text_player1, posy_text_player1),
            "YOU",
            TEXT_WH[1] // 2,
            self.WHITE,
        )

        posx_text_player2 = center_x_text_player2 + width_text // 2
        posy_text_player2 = init_y - int(40 * sy)
        self.text_label_bot = Text(
            (posx_text_player2, posy_text_player2),
            "BOT",
            TEXT_WH[1] // 2,
            self.WHITE,
        )

    def handle_events(self, events, keys):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos
                    if self.btn_start.button_rectangle.collidepoint(mouse_pos):
                        AudioManager().play_click()
                        self.screen_manager.change_screen("GAME")

            if self.btn_close.handle_event(event):
                AudioManager().play_click()
                self.screen_manager.change_screen("MAIN")

            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                self.btn_start.check_hover(mouse_pos)

    def update(self):
        pass

    def draw(self):
        self.screen.fill(self.MAINDARK)

        title_text = "ARCADE MODE"
        title_surface = self.title_font.render(title_text, True, self.WHITE)
        title_rect = title_surface.get_rect()
        title_rect.centerx = self.screen.get_rect().centerx
        title_rect.top = int(80 * (self.screen.get_height() / 720))
        self.screen.blit(title_surface, title_rect)

        self.btn_start.draw(self.screen)
        self.textbox_you.draw(self.screen)
        self.textbox_bot.draw(self.screen)
        self.text_label_you.draw(self.screen)
        self.text_label_bot.draw(self.screen)
        self.btn_close.draw(self.screen)
