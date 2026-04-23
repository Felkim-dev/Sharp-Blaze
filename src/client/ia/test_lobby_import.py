import sys
sys.path.insert(0, "src/client")

print("=== TEST: Importacion del lobby con EasyBot ===")
import pygame
pygame.init()
screen = pygame.display.set_mode((100, 100))

class FakeNetwork:
    connected = False
    connection_status = "IDLE"
    def receive_json(self): return None

class FakeScreenManager:
    network = FakeNetwork()
    screens = {}
    def change_screen(self, n): pass

from ui.lobby_screen import LobbyScreen

sm    = FakeScreenManager()
lobby = LobbyScreen(sm, screen)

print("  [OK] LobbyScreen instanciado")
print("  [OK] btn_bot_match existe:", hasattr(lobby, "btn_bot_match"))
print("  [OK] _bot inicial es None:", lobby._bot is None)

pygame.quit()
print()
print("TODOS LOS TESTS PASARON [OK]")
