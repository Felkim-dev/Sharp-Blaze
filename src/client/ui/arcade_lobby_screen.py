import pygame
import os

from ui.component import Button, Text, TextBox, CloseButton

from utils.json import JSON_Manager
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
            self.GRAY,
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
            "WAITING...",
            self.GRAY,
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

        self.session_id = None
        self.player_id = None
        self.local_player_id = None
        self.enemy_player_id = None
        self.connected = False

    def handle_events(self, events, keys):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos
                    if self.btn_start.button_rectangle.collidepoint(mouse_pos) and self.connected:
                        AudioManager().play_click()
                        session_id = getattr(self, 'session_id', None)
                        self.screen_manager.network.send_json(JSON_Manager.get_startgame(session_id))

            if self.btn_close.handle_event(event):
                AudioManager().play_click()
                self.screen_manager.network.disconnect()
                if hasattr(self.screen_manager, "container_manager") and self.screen_manager.container_manager:
                    self.screen_manager.container_manager.stop()
                self.screen_manager.change_screen("MAIN")

            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
                if self.connected:
                    self.btn_start.check_hover(mouse_pos)

    def update(self):
        data = self.screen_manager.network.receive_json()
        if data:
            print(data)
            message_type = data.get("type") or data.get("action")

            if message_type == "BROKER_MATCH_FOUND":
                self.local_player_id = data["payload"]["you"]
                self.enemy_player_id = data["payload"]["opponent"]
                self.session_id = data["payload"]["session_id"]
                self.player_id = data["payload"]["global_player_id"]
                self.textbox_you.text = self.local_player_id
                self.textbox_bot.text = self.enemy_player_id
                self.textbox_bot.text_color = self.WHITE
                self.screen_manager.network.connect_to_game_server(data["payload"])
                self.connected = True
                self.btn_start.ButtonColor = self.LIGHT_BLUE
                self.btn_start.ButtonColor_copy = self.LIGHT_BLUE

            elif message_type == "START_GAME" and data["payload"]["start"]:
                units = data["payload"]["units"]
                structures = data["payload"]["structures"]
                gold = data["payload"]["gold"]
                obstacles = data["payload"]["obstacles"]
                game_screen = self.screen_manager.screens["GAME"]
                game_screen.load_initial_state(gold, units, structures, self.player_id, obstacles, self.local_player_id, self.enemy_player_id)
                game_screen.set_arcade_mode(True)
                self.screen_manager.network.init_udp_connection(self.session_id, self.player_id)
                self.screen_manager.change_screen("GAME")

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
