# main.py
import pygame
import sys

#IMPORT OF SCREENS
from ui.main_screen import MainScreen
from ui.host_screen import HostScreen
from ui.join_screen import JoinScreen

class GAME:
    
    def __init__(self):
        
        WIDTH=1280
        HEIGHT=720
        
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sharp Blaze")
        self.clock = pygame.time.Clock()
        
        self.screens = {
            "MAIN": MainScreen(self,self.screen),
            "HOST": HostScreen(self,self.screen),
            # "JOIN": JoinScreen(self,self.screen),
                        }
        
        self.current_screen = self.screens["MAIN"]
        
    def change_screen(self, screen_name):
        if screen_name in self.screens:
            self.current_screen = self.screens[screen_name]
        else:
         #Borrar
            print("ERROR: Screen Does not Exists")
    
    def run(self):
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            
            self.current_screen.handle_events(events)
            self.current_screen.draw()
            
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    game = GAME()
    game.run()
