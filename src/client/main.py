# main.py
import pygame
import sys

# IMPORT OF SCREENS
from ui.main_screen import MainScreen
from ui.join_screen import JoinScreen
from ui.lobby_screen import LobbyScreen
from ui.conecting_screen import ConnectingScreen
from ui.game_screen import GameScreen

#IMPORT NETWORK MANAGER
from network.network import NetworkManager

#IMPORT AUDIO MANAGER
from utils.audio import AudioManager

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
        
        # Bot match state
        self.bot_instance = None
        self.bot_game_loop = None
        # Local server container handle (docker SDK container object)
        self.local_server_container = None

        #DICTIONARY OF THE VALID SCREENS
        self._build_screens()

        #MAIN SCREEN WHEN THE GAME IS OPENED
        self.current_screen = self.screens["MAIN"]

        # Start the background music loop on launch
        AudioManager().start_music()

    def _build_screens(self):
        """Create (or re-create) all screen objects for the current display size."""
        self.screens = {
            "MAIN": MainScreen(self, self.screen),
            "JOIN": JoinScreen(self, self.screen),
            "LOBBY": LobbyScreen(self, self.screen),
            "CONNECTING": ConnectingScreen(self, self.screen),
            "GAME": GameScreen(self, self.screen),
        }

    def change_screen(self, screen_name):
        if screen_name in self.screens:
            audio = AudioManager()

            # Stop music when entering the game, resume when leaving it
            if screen_name == "GAME":
                audio.stop_music()
            elif isinstance(self.current_screen, GameScreen):
                # We are leaving the GameScreen back to a menu
                audio.resume_music()

            self.current_screen = self.screens[screen_name]
        else:
            print("ERROR: Screen Does not Exists")

    def stop_local_server_container(self):
        """Stop and remove the local docker container if it was started by the client."""
        if getattr(self, 'local_server_container', None) is None:
            return

        try:
            container = self.local_server_container
            # Container may be either a docker.models.containers.Container or an id string
            try:
                # Stop container gently
                container.stop(timeout=3)
            except Exception:
                # Try using client API if object is not a container
                try:
                    import docker
                    cli = docker.from_env()
                    cli.containers.get(str(container)).stop()
                except Exception:
                    pass

            try:
                container.remove()
            except Exception:
                try:
                    import docker
                    cli = docker.from_env()
                    cli.containers.get(str(container)).remove()
                except Exception:
                    pass

        except Exception as e:
            print(f"[MAIN] Error stopping local server container: {e}")
        finally:
            self.local_server_container = None

    def change_resolution(self, width, height):
        """Resize the game window and rebuild all screens for the new resolution."""
        # Preserve fullscreen state
        is_fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)
        flags = pygame.FULLSCREEN if is_fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("Sharp Blaze")

        # Re-create every screen so all UI elements recalculate positions & sizes
        self._build_screens()

        # If in-game, stay on the game screen instead of redirecting to main menu
        if isinstance(self.current_screen, GameScreen):
            self.current_screen = self.screens["GAME"]
        else:
            main_screen = self.screens["MAIN"]
            main_screen.menu_state = "RESOLUTION"
            self.current_screen = main_screen

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode, keeping the current resolution."""
        current_w = self.screen.get_width()
        current_h = self.screen.get_height()
        is_fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)

        if is_fullscreen:
            # Switch to windowed
            self.screen = pygame.display.set_mode((current_w, current_h))
        else:
            # Switch to fullscreen
            self.screen = pygame.display.set_mode((current_w, current_h), pygame.FULLSCREEN)

        pygame.display.set_caption("Sharp Blaze")

        # Re-create every screen for the new display mode
        self._build_screens()

        # If in-game, stay on the game screen
        if isinstance(self.current_screen, GameScreen):
            self.current_screen = self.screens["GAME"]
        else:
            main_screen = self.screens["MAIN"]
            main_screen.menu_state = "RESOLUTION"
            self.current_screen = main_screen

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
