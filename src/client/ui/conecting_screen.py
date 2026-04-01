import pygame
from ui.component import Button, Text, CloseButton,TextBox
import string


class ConnectingScreen:
    def __init__(self, screen_manager, screen):

        # SCREEN FROM THE MAIN GAME LOOP
        self.screen_manager = screen_manager
        self.screen = screen

        # COLORS
        # PRINCIPAL BG
        self.MAINDARK = (19, 23, 34)
        # BUTTONS
        self.WHITE = (255, 255, 255)
        self.GREEN = (0, 159, 12)
        self.RED = (204, 5, 35)
        self.BLACK = (0, 0, 0)

        # TEXT BOX SIZE
        TEXTBOX_WH = (500, 50)

        # BUTTON SIZE
        BUTTON_WH = (350, 50)

        # TEXT SIZE
        TEXT_SIZE = BUTTON_WH[1] // 2

        # CENTRATING COMPONENTS
        # HOST BUTTON
        width_button = BUTTON_WH[0]
        center_x_button = self.screen.get_rect().centerx - (width_button // 2)

        # TEXT BOX
        width_input = TEXTBOX_WH[0]
        center_x_input = self.screen.get_rect().centerx - (width_input // 2)

        init_y = self.screen.get_height() // 3
        separation_y = 100

        # Button creation
        self.btn_cancel = Button(
            (center_x_button, init_y + separation_y),
            BUTTON_WH,
            self.RED,
            "CANCEL",
            self.BLACK,
            TEXT_SIZE,
        )

        # TEXT BOX
        # TEXT BOX CREATION
        self.textbox_connecting = TextBox(
            (center_x_input, init_y),
            TEXTBOX_WH,
            self.GREEN,
            "CONNECTING",
            self.BLACK
        )

        # EXIT MAIN MENU BUTTON
        width_screen = self.screen.get_width()
        button_size = 30
        margin = 50
        # POS CALCULATION
        pos_x = width_screen - button_size - margin
        pos_y = margin

        # CLOSE BUTTON INSTANCE
        self.btn_close = CloseButton(pos_x, pos_y, button_size)

    def handle_events(self, events, keys):
        """where screen manages the events of their buttons and input boxes"""
        for event in events:
            if self.btn_close.handle_event(event):
                self.screen_manager.change_screen("MAIN")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                # Comprobation that the input box is clicked
                if self.btn_cancel.button_rectangle.collidepoint(mouse_pos):
                    self.screen_manager.network.desconectar()
                    self.screen_manager.change_screen("JOIN")

            elif event.type == pygame.MOUSEMOTION:

                # MOUSE ON BUTTON DETECTION
                mouse_pos = event.pos

                self.btn_cancel.check_hover(mouse_pos)

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))

        # COMPONENTS DRAW
        self.btn_cancel.draw(self.screen)
        self.textbox_connecting.draw(self.screen)

        # EXIT BUTTON
        self.btn_close.draw(self.screen)
