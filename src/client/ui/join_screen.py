import pygame
from ui.component import Button, InputBox, Text,CloseButton
import string


class JoinScreen:
    def __init__(self, screen_manager, screen):

        # SCREEN FROM THE MAIN GAME LOOP
        self.screen_manager = screen_manager
        self.screen = screen

        # COLORS
        # PRINCIPAL BG
        self.MAINDARK = (19, 23, 34)
        # BUTTONS
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        GRAY = (112, 112, 112)

        # INPUT BOX SIXE
        INPUT_WH = (500, 50)

        # BUTTON SIZE
        BUTTON_WH = (350, 50)

        # TEXT SIZE
        TEXT_SIZE = BUTTON_WH[1] // 2

        # CENTRATING COMPONENTS
        # HOST BUTTON
        width_button = BUTTON_WH[0]
        center_x_button = self.screen.get_rect().centerx - (width_button // 2)

        # INPUT BOX
        width_input = INPUT_WH[0]
        center_x_input = self.screen.get_rect().centerx - (width_input // 2)

        init_y = self.screen.height // 3
        separation_y = 100

        # Button creation
        self.btn_join = Button(
            (center_x_button, init_y + separation_y),
            BUTTON_WH,
            GRAY,
            "JOIN",
            self.BLACK,
            TEXT_SIZE,
        )

        # INPUT BOX
        # List of Prohibited Simbols
        prohibited_simbols = string.punctuation
        prohibited_simbols += " "
        # INPUT BOX CREATION
        self.inputbox_nickname = InputBox(
            (center_x_input, init_y),
            INPUT_WH,
            "ENTER USERNAME (>3 CHARACTERS)",
            NotAllowedChars=prohibited_simbols,
        )

        # ID CREATION

        posx_text_ID = center_x_input - 20
        posy_text_ID = init_y + 20
        self.text_ID = Text(
            (posx_text_ID, posy_text_ID), "ID: ", INPUT_WH[1] // 2, self.WHITE
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

                if (
                    self.btn_join.button_rectangle.collidepoint(mouse_pos)
                    and len(self.inputbox_nickname.user_input) > 3
                ):
                    self.screen_manager.change_screen("LOBBY")

                # Comprobation that the input box is clicked
                if self.inputbox_nickname.inputbox_rectangle.collidepoint(mouse_pos):
                    self.inputbox_nickname.is_selected = True
                else:
                    self.inputbox_nickname.is_selected = False

            if event.type == pygame.KEYDOWN:

                # Writing if the input box was clicked
                if self.inputbox_nickname.is_selected:
                    char = event.unicode

                    # Comprobation to avoid too large strings
                    if (
                        len(self.inputbox_nickname.user_input)
                        < self.inputbox_nickname.max_length
                    ):

                        # Comprobation to avoid special characters
                        if (
                            not char in self.inputbox_nickname.notallowed_chars
                            or self.inputbox_nickname.notallowed_chars is None
                        ):
                            self.inputbox_nickname.user_input += char

            elif event.type == pygame.MOUSEMOTION and len(self.inputbox_nickname.user_input) > 3:

                # MOUSE ON BUTTON DETECTION
                mouse_pos = event.pos

                self.btn_join.check_hover(mouse_pos)

        # Deleting of characters of the string
        if keys[pygame.K_BACKSPACE]:
            self.inputbox_nickname.user_input = self.inputbox_nickname.user_input[:-1]

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))

        # COMPONENTS DRAW
        self.btn_join.draw(self.screen)
        self.inputbox_nickname.draw(self.screen)

        # TEXT
        self.text_ID.draw(self.screen)

        # EXIT BUTTON
        self.btn_close.draw(self.screen)
