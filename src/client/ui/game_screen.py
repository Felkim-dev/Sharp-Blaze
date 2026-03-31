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
        raw_data = self.screen_manager.network.receive_udp()
        if raw_data:
            print(f"Me llegaron estos bytes de Steve: {raw_data}")

    def draw(self):
        self.screen.fill(self.MAINDARK)
