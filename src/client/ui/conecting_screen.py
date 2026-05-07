import pygame
from ui.component import Button, CloseButton,TextBox
from utils.audio import AudioManager

class ConnectingScreen:
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
        # BUTTONS
        self.WHITE = (255, 255, 255)
        self.GREEN = (0, 159, 12)
        self.RED = (204, 5, 35)
        self.BLACK = (0, 0, 0)

        # TEXT BOX SIZE (scaled)
        TEXTBOX_WH = (int(500 * sx), int(50 * sy))

        # BUTTON SIZE (scaled)
        BUTTON_WH = (int(350 * sx), int(50 * sy))

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
        separation_y = int(100 * sy)

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
        size_text_boxes = int(25 * sy)
        self.textbox_connecting = TextBox(
            (center_x_input, init_y),
            TEXTBOX_WH,
            self.GREEN,
            "CONNECTING",
            self.BLACK,
            size_text_boxes,
        )

        # EXIT MAIN MENU BUTTON
        width_screen = self.screen.get_width()
        button_size = int(30 * sy)
        margin = int(50 * sx)
        # POS CALCULATION
        pos_x = width_screen - button_size - margin
        pos_y = margin

        # CLOSE BUTTON INSTANCE
        self.btn_close = CloseButton(pos_x, pos_y, button_size)

    def handle_events(self, events, keys):
        """where screen manages the events of their buttons and input boxes"""
        for event in events:
            if self.btn_close.handle_event(event):
                AudioManager().play_click()
                self.screen_manager.change_screen("MAIN")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                    # Comprobation that the button is clicked
                    if self.btn_cancel.button_rectangle.collidepoint(mouse_pos):
                        AudioManager().play_click()
                        self.screen_manager.network.disconnect()
                        self.screen_manager.change_screen("JOIN")

            elif event.type == pygame.MOUSEMOTION:

                # MOUSE ON BUTTON DETECTION
                mouse_pos = event.pos

                self.btn_cancel.check_hover(mouse_pos)

    def update(self):
        """Handle connection-state transitions while this screen is active."""
        state = self.screen_manager.network.connection_status

        if state == "IDLE" and self.screen_manager.network.connected:
            self.screen_manager.change_screen("LOBBY")
        elif state == "ERROR":
            self.textbox_connecting.update_text("CONNECTION ERROR")

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))

        # COMPONENTS DRAW
        self.btn_cancel.draw(self.screen)
        self.textbox_connecting.draw(self.screen)

        # EXIT BUTTON
        self.btn_close.draw(self.screen)
