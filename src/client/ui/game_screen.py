import pygame
import math
import struct

from engine.world import GameWorld

class GameScreen:
    def __init__(self, screen_manager , screen):

        # MAIN SCREEN
        self.screen_manager = screen_manager
        self.screen  = screen

        # MAIN COLOR
        self.MAINDARK = (19, 23, 34)
        
        #WORLD
        self.world = GameWorld(self.screen_manager.network)

    def handle_events(self, events, keys):
        pass

    def update(self):
        self.world.update()

    def draw(self):
        self.screen.fill(self.MAINDARK)
        
        self.world.draw(self.screen)
