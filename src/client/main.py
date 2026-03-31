# main.py
import pygame
import sys

# IMPORT OF SCREENS
from ui.main_screen import MainScreen
from ui.host_screen import HostScreen
from ui.join_screen import JoinScreen
from ui.lobby_screen import LobbyScreen
from ui.conecting_screen import ConnectingScreen

#IMPORT NETWORK MANAGER
from network.network import NetworkManager

#MAIN CLASS
class GAME:

    def __init__(self):

        
        #RESOLUTION OF TE MAIN WINDOW
        WIDTH = 1280
        HEIGHT = 720

        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sharp Blaze")
        self.clock = pygame.time.Clock()

        #OBJECT NETWORK
        self.network = NetworkManager()

        #DICTIONARY OF THE VALID SCREENS
        self.screens = {
            "MAIN": MainScreen(self, self.screen),
            "HOST": HostScreen(self, self.screen),
            "JOIN": JoinScreen(self, self.screen),
            "LOBBY": LobbyScreen(self, self.screen),
            "CONNECTING": ConnectingScreen(self, self.screen)
        }

        #MAIN SCREEN WHEN THE GAME IS OPENED
        self.current_screen = self.screens["MAIN"]

    def change_screen(self, screen_name):
        if screen_name in self.screens:
            self.current_screen = self.screens[screen_name]
        else:
            print("ERROR: Screen Does not Exists")

    def run(self):
        #MAIN LOOP
        while True:
            
            #LIST EVENTS OF THE GAME
            events = pygame.event.get()
            
            for event in events:
                
                #IF THE USER CLOSES THE GAME
                if event.type == pygame.QUIT:
                    self.network.disconnect()
                    pygame.quit()
                    sys.exit()

            #KEYS pressed by the user
            keys = pygame.key.get_pressed()

            #DEFINITION OF EACH SCREEN FUNCTIONALITY
            self.current_screen.handle_events(events, keys)
            self.current_screen.draw()
            self.current_screen.update()

            #UPDATING RATE
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    game = GAME()
    game.run()
