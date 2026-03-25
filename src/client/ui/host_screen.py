import pygame
from ui.component import Button,InputBox
import sys


class HostScreen:
    def __init__(self, screen_manager, screen):
        self.screen_manager = screen_manager
        self.screen = screen

        # Colors
        self.MAINDARK = (19, 23, 34)
        self.WHITE = (255, 255, 255)
        GRAY = (54, 54, 54)

        # INPUT BOX SIXE
        INPUT_WH = (500,50)

        # Button and Text Size
        BUTTON_WH = (350, 50)
        TEXT_SIZE = 24

        # Calculate Pos
        width_button = BUTTON_WH[0]
        center_x_button = self.screen.get_rect().centerx - (width_button // 2)
        width_input = INPUT_WH[0]
        center_x_input = self.screen.get_rect().centerx - (width_input // 2)

        init_y = 310
        separation_y = 60

        # Buttons declarations
        self.btn_connect = Button(
            (center_x_button, init_y),
            BUTTON_WH,
            GRAY,
            "CONNECT",
            self.WHITE,
            TEXT_SIZE,
        )

        self.box_name = InputBox((center_x_input,init_y-100), INPUT_WH, "ENTER USERNAME (>3 CHARACTERS)")

    def handle_events(self, events,keys):

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos
                
                if self.box_name.button_rectangle.collidepoint(mouse_pos):
                    self.box_name.change_isselected()
                else:
                    self.box_name.change_isselected()

            if event.type == pygame.KEYDOWN:
                if self.box_name.is_selected:
                    self.box_name.string_input += event.unicode
                    
        if keys[pygame.K_BACKSPACE]:
            self.box_name.string_input = self.box_name.string_input[:-1]
                        

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))  # Fondo oscuro
        self.btn_connect.draw(self.screen)
        self.box_name.draw(self.screen)
