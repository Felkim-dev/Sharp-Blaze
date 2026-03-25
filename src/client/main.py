# main.py
import pygame
import sys
from ui.connection_screen import ConnectionScreen
from ui.main_screen import MainScreen

WIDTH=1280
HEIGHT=720

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Sharp Blaze")
    clock = pygame.time.Clock()
    # Cargamos la pantalla inicial
    current_screen = MainScreen(screen)
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        # 1. Procesar eventos (clics, teclas)
        current_screen.handle_events(events)
        # 2. Renderizar gráficos
        current_screen.draw()

        pygame.display.flip()
        clock.tick(30)  # Limitamos a 30 FPS según el Project Charter

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
