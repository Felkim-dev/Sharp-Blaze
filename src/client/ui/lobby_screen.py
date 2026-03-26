import pygame
from ui.component import Button, Text,TextBox,CloseButton

class LobbyScreen:
    def __init__(self, screen_manager, screen):

        # SCREEN FROM THE MAIN GAME LOOP
        self.screen_manager = screen_manager
        self.screen = screen

        # COLORS
        # PRINCIPAL BG
        self.MAINDARK = (19, 23, 34)

        self.WHITE = (255, 255, 255)
        self.GRAY = (54, 54, 54)
        self.BLACK = (0, 0, 0)

        # PLAYER BOX SIZE
        TEXT_WH = (300, 50)

        # BUTTON SIZE
        BUTTON_WH = (350, 50)

        # TEXT SIZE
        TEXT_SIZE = BUTTON_WH[1]//2

        # EXIT MAIN MENU BUTTON
        width_screen = self.screen.get_width()
        button_size = 30
        margin = 50 
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

        init_y = (self.screen.height // 3) + 50

        # Button creation
        self.btn_Start = Button((center_x_button, init_y+100),BUTTON_WH,self.GRAY,"START GAME",self.WHITE,TEXT_SIZE,)

        # TEXT BOX CREATION
        self.textbox_nickname1 = TextBox((center_x_text_player1, init_y),TEXT_WH,self.BLACK,"USER1",self.WHITE)
        self.textbox_nickname2 = TextBox((center_x_text_player2, init_y),TEXT_WH,self.BLACK,"USER2",self.WHITE)

        # Player text CREATION

        posx_text_player1 = center_x_text_player1 + width_text//2
        posy_text_player1 = init_y - 40
        self.text_player1 = Text((posx_text_player1, posy_text_player1), "YOU", TEXT_WH[1] // 2, self.WHITE)

        posx_text_player2 = center_x_text_player2 + width_text // 2
        posy_text_player2 = init_y - 40
        self.text_player2 = Text((posx_text_player2, posy_text_player2), "OPPONENT", TEXT_WH[1] // 2, self.WHITE)

    def handle_events(self, events, keys):
        """where screen manages the events of their buttons and input boxes"""
        for event in events:
            if self.btn_close.handle_event(event):
                self.screen_manager.change_screen("MAIN")

    def update(self):
        data = self.screen_manager.network.receive_json()

        if data:
            
            print(data)
            
            if data.get("type") == "QUEUE_STATUS":
                self.textbox_nickname1.text = data["payload"]["you"]
                self.textbox_nickname2.text = "WAITING..."
                self.textbox_nickname2.text_color = (84, 84, 84)
                
            if data.get("type") == "MATCH_FOUND":

                self.textbox_nickname1.text = data["payload"]["you"]
                self.textbox_nickname2.text = data["payload"]["opponent"]
                self.textbox_nickname2.text_color = self.WHITE
            

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
