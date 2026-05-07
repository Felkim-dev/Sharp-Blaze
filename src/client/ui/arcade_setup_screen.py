import pygame
import os

from ui.component import Button, InputBox, CloseButton, TextBox

from utils.audio import AudioManager


class ArcadeSetupScreen:
    def __init__(self, screen_manager, screen):

        self.screen_manager = screen_manager
        self.screen = screen

        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        self.MAINDARK = (19, 23, 34)
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.GRAY = (112, 112, 112)
        self.LIGHT_BLUE = (0, 150, 255)
        self.RED_ERROR = (204, 5, 35)

        INPUT_WH = (int(500 * sx), int(50 * sy))
        BUTTON_WH = (int(350 * sx), int(50 * sy))
        ERROR_WH = (int(800 * sx), int(200 * sy))
        TEXT_SIZE = BUTTON_WH[1] // 2

        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        TITLE_FONT_PATH = os.path.join(CURRENT_DIR, "..", "assets", "Anton-Regular.ttf")
        self.title_font = pygame.font.Font(TITLE_FONT_PATH, int(64 * sy))

        width_button = BUTTON_WH[0]
        center_x_button = self.screen.get_rect().centerx - (width_button // 2)

        width_input = INPUT_WH[0]
        center_x_input = self.screen.get_rect().centerx - (width_input // 2)

        init_y = self.screen.get_height() // 3
        separation_y = int(100 * sy)

        self.btn_start = Button(
            (center_x_button, init_y + separation_y),
            BUTTON_WH,
            self.GRAY,
            "START GAME",
            self.BLACK,
            TEXT_SIZE,
        )

        self.inputbox_username = InputBox(
            (center_x_input, init_y),
            INPUT_WH,
            "ENTER USERNAME (>3 CHARS)",
        )

        width_screen = self.screen.get_width()
        button_size = int(30 * sy)
        margin = int(50 * sx)
        pos_x = width_screen - button_size - margin
        pos_y = margin

        self.btn_close = CloseButton(pos_x, pos_y, button_size)

        error_text_size = int(50 * sy)
        error_x = (self.screen.get_width() - ERROR_WH[0]) // 2
        self.error_box = TextBox(
            (error_x, init_y + separation_y + int(100 * sy)),
            ERROR_WH,
            self.RED_ERROR,
            "Docker is required for Arcade Mode.\nPlease start Docker and try again.",
            self.WHITE,
            error_text_size,
        )
        self.show_error = False
        self.error_time_init = 0
        self.duration_error = 5000

        self.backspace_ready = True
        self.backspace_last_time = 0
        self.backspace_initial_delay = 400
        self.backspace_repeat_interval = 50

    def show_notification(self):
        self.show_error = True
        self.error_time_init = pygame.time.get_ticks()

    def _is_username_valid(self):
        return len(self.inputbox_username.user_input) > 3

    def _check_docker_available(self):
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    def handle_events(self, events, keys):

        for event in events:

            if self.btn_close.handle_event(event):
                AudioManager().play_click()
                self.inputbox_username.user_input = ""
                self.screen_manager.change_screen("MAIN")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                    if (
                        self.btn_start.button_rectangle.collidepoint(mouse_pos)
                        and self._is_username_valid()
                    ):
                        AudioManager().play_click()

                        if self._check_docker_available():
                            from ia.infra.arcade_match_controller import ArcadeMatchController
                            controller = ArcadeMatchController(
                                "HARD",
                                self.screen_manager.network,
                                self.screen_manager,
                            )
                            self.screen_manager.arcade_controller = controller
                            self.screen_manager.container_manager = controller
                            controller.start_match()
                            self.screen_manager.change_screen("ARCADE_LOBBY")
                        else:
                            self.show_notification()

                    if self.inputbox_username.inputbox_rectangle.collidepoint(mouse_pos):
                        self.inputbox_username.is_selected = True
                    else:
                        self.inputbox_username.is_selected = False

            if event.type == pygame.KEYDOWN:

                if self.inputbox_username.is_selected:
                    char = event.unicode

                    if (
                        len(self.inputbox_username.user_input)
                        < self.inputbox_username.max_length
                    ):

                        if char.isalnum():
                            self.inputbox_username.user_input += char

                if event.key == pygame.K_RETURN and self._is_username_valid():
                    AudioManager().play_click()

                    if self._check_docker_available():
                        from ia.infra.arcade_match_controller import ArcadeMatchController
                        controller = ArcadeMatchController(
                            "HARD",
                            self.screen_manager.network,
                            self.screen_manager,
                        )
                        self.screen_manager.arcade_controller = controller
                        self.screen_manager.container_manager = controller
                        controller.start_match()
                        self.screen_manager.change_screen("ARCADE_LOBBY")
                    else:
                        self.show_notification()

            elif event.type == pygame.MOUSEMOTION and self._is_username_valid():

                mouse_pos = event.pos

                self.btn_start.check_hover(mouse_pos)

        if keys[pygame.K_BACKSPACE]:
            now = pygame.time.get_ticks()
            if self.backspace_ready:
                if len(self.inputbox_username.user_input) > 0:
                    self.inputbox_username.user_input = self.inputbox_username.user_input[:-1]
                self.backspace_ready = False
                self.backspace_last_time = now
            elif now - self.backspace_last_time > self.backspace_repeat_interval:
                if now - self.backspace_last_time > self.backspace_initial_delay or len(self.inputbox_username.user_input) > 0:
                    if len(self.inputbox_username.user_input) > 0:
                        self.inputbox_username.user_input = self.inputbox_username.user_input[:-1]
                    self.backspace_last_time = now
        else:
            self.backspace_ready = True

    def update(self):
        if self._is_username_valid():
            self.btn_start.ButtonColor = self.LIGHT_BLUE
            self.btn_start.ButtonColor_copy = self.LIGHT_BLUE
        else:
            self.btn_start.ButtonColor = self.GRAY
            self.btn_start.ButtonColor_copy = self.GRAY

        if self.show_error:
            actual_time = pygame.time.get_ticks()

            elapsed_time = actual_time - self.error_time_init

            if elapsed_time > self.duration_error:
                self.show_error = False

    def draw(self):
        self.screen.fill(self.MAINDARK)

        title_text = "ARCADE MODE"
        title_surface = self.title_font.render(title_text, True, self.WHITE)
        title_rect = title_surface.get_rect()
        title_rect.centerx = self.screen.get_rect().centerx
        title_rect.top = int(80 * (self.screen.get_height() / 720))
        self.screen.blit(title_surface, title_rect)

        self.btn_start.draw(self.screen)
        self.inputbox_username.draw(self.screen)

        self.btn_close.draw(self.screen)

        if self.show_error:
            self.error_box.draw(self.screen)
