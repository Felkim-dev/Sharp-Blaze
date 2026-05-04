import pygame

from ui.component import Button, Text,TextBox,CloseButton

from utils.config import Config
from utils.json import JSON_Manager
from utils.audio import AudioManager
class LobbyScreen:
    def __init__(self, screen_manager, screen):

        # SCREEN FROM THE MAIN GAME LOOP
        self.screen_manager = screen_manager
        self.screen = screen

        # SCALE FACTORS relative to base resolution 1280x720
        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        # COLORS
        # PRINCIPAL BG
        self.MAINDARK = (19, 23, 34)

        self.WHITE = (255, 255, 255)
        self.GRAY = (112, 112, 112)
        self.BLACK = (0, 0, 0)

        # PLAYER BOX SIZE (scaled)
        TEXT_WH = (int(300 * sx), int(50 * sy))

        # BUTTON SIZE (scaled)
        BUTTON_WH = (int(350 * sx), int(50 * sy))

        # TEXT SIZE
        TEXT_SIZE = BUTTON_WH[1]//2

        # EXIT MAIN MENU BUTTON
        width_screen = self.screen.get_width()
        button_size = int(30 * sy)
        margin = int(50 * sx)
        # POS CALCULATION
        pos_x = width_screen - button_size - margin
        pos_y = margin  

        # CLOSE BUTTON INSTANCE
        self.btn_close = CloseButton(pos_x, pos_y, button_size)

        # Positioning COMPONENTS
        # START BUTTON
        width_button = BUTTON_WH[0]
        center_x_button = self.screen.get_rect().centerx - (width_button // 2)

        # TEXT BOX
        width_text = TEXT_WH[0]
        center_x_text_player1 = self.screen.get_rect().centerx - width_text * 1.5
        center_x_text_player2 = self.screen.get_rect().centerx + width_text//2

        init_y = (self.screen.get_height() // 3) + int(50 * sy)

        # Button creation
        self.btn_Start = Button((center_x_button, init_y + int(100 * sy)),BUTTON_WH,self.GRAY,"START GAME",self.BLACK,TEXT_SIZE,)

        # TEXT BOX CREATION
        size_text_boxes = int(25 * sy)
        self.textbox_nickname1 = TextBox((center_x_text_player1, init_y),TEXT_WH,self.BLACK,"USER1",self.WHITE,size_text_boxes)
        self.textbox_nickname2 = TextBox((center_x_text_player2, init_y),TEXT_WH,self.BLACK,"USER2",self.WHITE,size_text_boxes)

        # Player text CREATION
        posx_text_player1 = center_x_text_player1 + width_text//2
        posy_text_player1 = init_y - int(40 * sy)
        self.text_player1 = Text((posx_text_player1, posy_text_player1), "YOU", TEXT_WH[1] // 2, self.WHITE)

        posx_text_player2 = center_x_text_player2 + width_text // 2
        posy_text_player2 = init_y - int(40 * sy)
        self.text_player2 = Text((posx_text_player2, posy_text_player2), "OPPONENT", TEXT_WH[1] // 2, self.WHITE)

    def handle_events(self, events, keys):
        """where screen manages the events of their buttons and input boxes"""
        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                    if self.textbox_nickname2.text != "WAITING..." and self.btn_Start.button_rectangle.collidepoint(mouse_pos):
                        AudioManager().play_click()

                        if Config.OFFLINE_DEBUG_MODE: # DEBUG MODE

                            units = {
                            1000: (450, 4550),
                            1001: (550, 4450),
                            3002: (350, 4450),
                            
                            6000: (4550,450),
                            6001: (4450,550),
                            8002: (4650,550)
                                }

                            structures = {
                                100: (300, 4700),
                                5000: (4700, 300),
                                # Neutral entity in the exact center of a 5000x5000 map
                                11000: (2500, 2500),
                                10000: (2000, 1000),
                                10001: (1000, 2000),
                            }

                            game_screen = self.screen_manager.screens["GAME"]
                            game_screen.load_initial_state(units,structures)
                            self.screen_manager.change_screen("GAME")
                        else:
                            # Send START_GAME with session_id if available (dedicated session)
                            session_id = getattr(self, 'session_id', None)
                            self.screen_manager.network.send_json(JSON_Manager.get_startgame(session_id))

            if self.btn_close.handle_event(event):
                AudioManager().play_click()
                self.screen_manager.network.disconnect()
                self.screen_manager.change_screen("MAIN")

            elif event.type == pygame.MOUSEMOTION:

                # MOUSE ON BUTTON DETECTION
                mouse_pos = event.pos

                if self.textbox_nickname2.text != "WAITING...":
                    self.btn_Start.check_hover(mouse_pos)

    def update(self):

        if not Config.OFFLINE_DEBUG_MODE:
            data = self.screen_manager.network.receive_json()

            if data:

                print(data)

                message_type = data.get("type") or data.get("action")

                if message_type == "QUEUE_STATUS":
                    self.textbox_nickname1.text = data["payload"]["you"]
                    self.textbox_nickname2.text = "WAITING..."
                    self.textbox_nickname2.text_color = (84, 84, 84)

                elif message_type == "BROKER_MATCH_FOUND":

                    self.local_player_id = data["payload"]["you"]
                    self.enemy_player_id = data["payload"]["opponent"]

                    self.session_id = data["payload"]["session_id"]
                    self.player_id = data["payload"]["global_player_id"]

                    self.textbox_nickname1.text = self.local_player_id
                    self.textbox_nickname2.text = self.enemy_player_id

                    self.textbox_nickname2.text_color = self.WHITE

                    self.screen_manager.network.connect_to_game_server(data["payload"])

                if message_type == "START_GAME" and data["payload"]["start"]:

                    units = data["payload"]["units"]

                    structures = data["payload"]["structures"]

                    gold = data["payload"]["gold"]

                    obstacles = data["payload"]["obstacles"]

                    game_screen = self.screen_manager.screens["GAME"]

                    game_screen.load_initial_state(gold,units,structures, self.player_id,obstacles,self.local_player_id,self.enemy_player_id)

                    self.screen_manager.network.init_udp_connection(self.session_id,self.player_id)

                    self.screen_manager.change_screen("GAME")

        else:
            # ======================= DEBUG MODE =======================
            self.textbox_nickname1.text = "Player1"
            self.textbox_nickname2.text = "Player2"

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))

        # COMPONENTS DRAW
        self.btn_Start.draw(self.screen)

        self.textbox_nickname1.draw(self.screen)
        self.textbox_nickname2.draw(self.screen)

        # TEXT
        self.text_player1.draw(self.screen)
        self.text_player2.draw(self.screen)

        # EXIT BUTTON
        self.btn_close.draw(self.screen)
