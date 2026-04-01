import pygame
import math
import struct

class GameScreen:
    def __init__(self, screen_manager , screen):

        # MAIN SCREEN
        self.screen_manager = screen_manager
        self.screen  = screen

        # MAIN COLOR
        self.MAINDARK = (19, 23, 34)

    def handle_events(self, events, keys):
        pass

    def update(self):
        print(self.screen_manager.network.get_latest_positions())

    def draw(self):
        self.screen.fill(self.MAINDARK)
