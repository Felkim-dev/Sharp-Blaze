import pygame
import sys
import os
import threading

from ui.component import Button, Text, Slider, Checkbox, InputBox
from ui.floating_shapes import FloatingShape
from ia.bot_player import BotPlayer
from ia.bot_game_loop import BotGameLoop
from utils.config import Config
from utils.audio import AudioManager

# Available resolution options
RESOLUTIONS = ["1280x720", "1600x900", "1920x1080"]

class MainScreen:
    def __init__(self, screen_manager,screen):
        # SCREEN FROM THE MAIN GAME LOOP
        self.screen_manager = screen_manager
        self.screen = screen

        # SCALE FACTORS relative to base resolution 1280x720
        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        # COLORS
        self.MAINDARK = (19,23,34)
        self.WHITE = (255, 255, 255)
        self.LIGHT_BLUE = (0,212,255)
        self.BLACK = (0, 0, 0)
        self.RED = (204, 5, 35)

        # Button and Text Size (scaled)
        BUTTON_WH = (int(350 * sx), int(50 * sy))
        TEXT_SIZE = int(24 * sy)

        # Calculating POSITION (scaled)
        width_button = BUTTON_WH[0]
        center_x = self.screen.get_rect().centerx - (width_button //2)
        init_y = int(310 * sy)
        separation_y = int(60 * sy)

        # Buttons declarations
        self.btn_join = Button((center_x, init_y + separation_y * 0), BUTTON_WH, self.LIGHT_BLUE, "Join Game", self.BLACK, TEXT_SIZE)
        self.btn_bot = Button((center_x, init_y + separation_y * 1), BUTTON_WH, self.LIGHT_BLUE, "Bot Match", self.BLACK, TEXT_SIZE)
        self.btn_options = Button((center_x, init_y + separation_y * 2), BUTTON_WH, self.LIGHT_BLUE, "Options", self.BLACK, TEXT_SIZE)
        self.btn_exit = Button((center_x, init_y + separation_y * 3), BUTTON_WH, self.RED, "Exit", self.BLACK, TEXT_SIZE)

        # FONT
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        TITLE_FONT = os.path.join(CURRENT_DIR, "..","assets", "Anton-Regular.ttf")

        # Title position and size (scaled)
        title_y = int(180 * sy)
        title_size = int(100 * sy)

        # TEXT
        self.text_title = Text((self.screen.get_rect().centerx, title_y),"SHARP BLAZE", title_size,self.WHITE,TITLE_FONT)

        # =====================================================
        # MENU STATE: "MAIN", "OPTIONS", "VOLUME", "RESOLUTION"
        # =====================================================
        self.menu_state = "MAIN"

        # =====================================================
        # OPTIONS MENU
        # =====================================================

        # OPTIONS TITLE (using Anton font)
        self.text_options_title = Text(
            (self.screen.get_rect().centerx, title_y),
            "OPTIONS", title_size, self.WHITE, TITLE_FONT
        )

        # OPTIONS BUTTONS
        options_init_y = init_y
        self.btn_volume = Button((center_x, options_init_y + separation_y * 0), BUTTON_WH, self.LIGHT_BLUE, "Volume", self.BLACK, TEXT_SIZE)
        self.btn_resolution = Button((center_x, options_init_y + separation_y * 1), BUTTON_WH, self.LIGHT_BLUE, "Resolution", self.BLACK, TEXT_SIZE)
        self.btn_credits = Button((center_x, options_init_y + separation_y * 2), BUTTON_WH, self.LIGHT_BLUE, "Credits", self.BLACK, TEXT_SIZE)
        self.btn_back = Button((center_x, options_init_y + separation_y * 3), BUTTON_WH, self.RED, "Back", self.BLACK, TEXT_SIZE)

        # =====================================================
        # VOLUME MENU
        # =====================================================

        # VOLUME TITLE (using Anton font)
        self.text_volume_title = Text(
            (self.screen.get_rect().centerx, title_y),
            "VOLUME", title_size, self.WHITE, TITLE_FONT
        )

        # SLIDERS (scaled)
        audio = AudioManager()

        # Layout: center the entire label+bar block on screen
        label_area_width = int(160 * sx)
        gap = int(20 * sx)
        bar_width = int(400 * sx)
        bar_height = int(50 * sy)
        total_width = label_area_width + gap + bar_width
        block_left = self.screen.get_rect().centerx - total_width // 2 - int(60 * sx)

        label_right_x = block_left + label_area_width
        bar_x = label_right_x + gap
        slider_y_music = init_y
        slider_y_sfx = init_y + int(80 * sy)
        label_size_slider = int(22 * sy)

        self.slider_music = Slider(
            label_y=slider_y_music,
            label_right_x=label_right_x,
            bar_x=bar_x,
            bar_width=bar_width,
            bar_height=bar_height,
            label_text="Music:",
            initial_value=int(audio.music_volume * 100),
            label_size=label_size_slider,
        )

        self.slider_sfx = Slider(
            label_y=slider_y_sfx,
            label_right_x=label_right_x,
            bar_x=bar_x,
            bar_width=bar_width,
            bar_height=bar_height,
            label_text="Effects:",
            initial_value=int(audio.sfx_volume * 100),
            label_size=label_size_slider,
        )

        # VOLUME BACK BUTTON
        volume_back_y = options_init_y + separation_y * 3
        self.btn_volume_back = Button((center_x, volume_back_y), BUTTON_WH, self.RED, "Back", self.BLACK, TEXT_SIZE)

        # =====================================================
        # RESOLUTION MENU
        # =====================================================

        # RESOLUTION TITLE (using Anton font)
        self.text_resolution_title = Text(
            (self.screen.get_rect().centerx, title_y),
            "RESOLUTION", title_size, self.WHITE, TITLE_FONT
        )

        # Determine current resolution and fullscreen state
        current_res_str = f"{self.screen.get_width()}x{self.screen.get_height()}"
        is_fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)

        # Resolution option buttons (scaled, same layout as other menus)
        RES_BUTTON_WH = (int(350 * sx), int(50 * sy))
        self.res_buttons = []
        for i, res in enumerate(RESOLUTIONS):
            # Selected resolution gets cyan text, others get white
            is_selected = (res == current_res_str)
            text_color = self.LIGHT_BLUE if is_selected else self.WHITE
            btn = Button(
                (center_x, options_init_y + separation_y * i),
                RES_BUTTON_WH, self.BLACK, res, text_color, TEXT_SIZE
            )
            self.res_buttons.append(btn)

        # FULLSCREEN CHECKBOX (row 3, between res buttons and Back)
        checkbox_y = options_init_y + separation_y * 3 + int(25 * sy)
        checkbox_size = int(35 * sy)
        # Align label to the left of the checkbox box
        checkbox_label_right_x = self.screen.get_rect().centerx - int(10 * sx)
        checkbox_box_x = self.screen.get_rect().centerx + int(10 * sx)
        self.checkbox_fullscreen = Checkbox(
            label_y=checkbox_y,
            label_right_x=checkbox_label_right_x,
            box_x=checkbox_box_x,
            box_size=checkbox_size,
            label_text="Fullscreen:",
            checked=is_fullscreen,
            label_size=int(22 * sy),
        )

        # RESOLUTION BACK BUTTON (row 4)
        res_back_y = options_init_y + separation_y * 4
        self.btn_resolution_back = Button((center_x, res_back_y), BUTTON_WH, self.RED, "Back", self.BLACK, TEXT_SIZE)

        # =====================================================
        # CREDITS MENU
        # =====================================================

        # CREDITS TITLE (using Anton font)
        self.text_credits_title = Text(
            (self.screen.get_rect().centerx, title_y),
            "CREDITS", title_size, self.WHITE, TITLE_FONT
        )

        # CREDITS MESSAGE (using IntroRust font, inside a black box)
        INTRO_FONT = os.path.join(CURRENT_DIR, "..", "assets", "IntroRust.otf")

        # Box dimensions: 80% of screen width, centered
        credits_box_w = int(self.screen.get_width() * 0.80)
        credits_box_h = int(120 * sy)
        credits_box_x = (self.screen.get_width() - credits_box_w) // 2
        credits_box_y = init_y
        self.credits_box_rect = pygame.Rect(credits_box_x, credits_box_y, credits_box_w, credits_box_h)

        # Size the font to fill the box width (fit the longer line)
        credits_text_1 = "Thanks to the AI Agents used on this game,"
        credits_text_2 = "and AOE for inspired our work :D"
        padding_x = int(20 * sx)
        target_width = credits_box_w - padding_x * 2

        # Find the largest font size where the longest line fits the box
        credits_font_size = int(30 * sy)
        test_font = pygame.font.Font(INTRO_FONT, credits_font_size)
        while test_font.size(credits_text_1)[0] > target_width and credits_font_size > 8:
            credits_font_size -= 1
            test_font = pygame.font.Font(INTRO_FONT, credits_font_size)

        self.credits_font = test_font
        self.credits_surface_1 = self.credits_font.render(credits_text_1, True, self.WHITE)
        self.credits_surface_2 = self.credits_font.render(credits_text_2, True, self.WHITE)

        # Center both lines vertically inside the box
        line_h = self.credits_surface_1.get_height()
        line_gap = int(8 * sy)
        total_text_h = line_h * 2 + line_gap
        text_top = credits_box_y + (credits_box_h - total_text_h) // 2

        self.credits_rect_1 = self.credits_surface_1.get_rect(center=(self.screen.get_rect().centerx, text_top + line_h // 2))
        self.credits_rect_2 = self.credits_surface_2.get_rect(center=(self.screen.get_rect().centerx, text_top + line_h + line_gap + line_h // 2))

        # CREDITS BACK BUTTON
        credits_back_y = credits_box_y + credits_box_h + int(30 * sy)
        self.btn_credits_back = Button((center_x, credits_back_y), BUTTON_WH, self.RED, "Back", self.BLACK, TEXT_SIZE)

        # Create a list of background shapes (e.g., 25 floating shapes)
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        self.background_shapes = []
        for _ in range(25):
            shape = FloatingShape(self.screen_width, self.screen_height)
            self.background_shapes.append(shape)
        
        # Bot match state
        self.bot_instance = None
        self.bot_loop = None

    def handle_events(self, events,keys):

        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                    if self.menu_state == "VOLUME":
                        # ---- VOLUME MENU EVENT HANDLING ----

                        # Slider interactions are handled below (all event types)
                        if self.btn_volume_back.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "OPTIONS"

                    elif self.menu_state == "RESOLUTION":
                        # ---- RESOLUTION MENU EVENT HANDLING ----

                        # Check resolution option buttons
                        for i, btn in enumerate(self.res_buttons):
                            if btn.button_rectangle.collidepoint(mouse_pos):
                                AudioManager().play_click()
                                selected = RESOLUTIONS[i]
                                w, h = selected.split("x")
                                self.screen_manager.change_resolution(int(w), int(h))
                                break

                        # Fullscreen checkbox
                        if self.checkbox_fullscreen.handle_event(event):
                            AudioManager().play_click()
                            self.screen_manager.toggle_fullscreen()

                        if self.btn_resolution_back.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "OPTIONS"

                    elif self.menu_state == "CREDITS":
                        # ---- CREDITS MENU EVENT HANDLING ----
                        if self.btn_credits_back.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "OPTIONS"

                    elif self.menu_state == "OPTIONS":
                        # ---- OPTIONS MENU EVENT HANDLING ----

                        if self.btn_volume.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "VOLUME"

                        elif self.btn_resolution.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "RESOLUTION"

                        elif self.btn_credits.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "CREDITS"

                        elif self.btn_back.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "MAIN"

                    else:
                        # ---- MAIN MENU EVENT HANDLING ----

                        if self.btn_join.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.screen_manager.change_screen("JOIN")

                        elif self.btn_bot.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self._start_bot_match()

                        elif self.btn_options.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            self.menu_state = "OPTIONS"

                        elif self.btn_exit.button_rectangle.collidepoint(mouse_pos):
                            AudioManager().play_click()
                            pygame.quit()
                            sys.exit()

            elif event.type == pygame.MOUSEMOTION:

                mouse_pos = event.pos

                if self.menu_state == "OPTIONS":
                    # HOVER DETECTION FOR OPTIONS BUTTONS
                    self.btn_volume.check_hover(mouse_pos)
                    self.btn_resolution.check_hover(mouse_pos)
                    self.btn_credits.check_hover(mouse_pos)
                    self.btn_back.check_hover(mouse_pos)
                elif self.menu_state == "VOLUME":
                    # HOVER DETECTION FOR VOLUME BACK BUTTON
                    self.btn_volume_back.check_hover(mouse_pos)
                elif self.menu_state == "RESOLUTION":
                    # HOVER DETECTION FOR RESOLUTION BUTTONS
                    for btn in self.res_buttons:
                        btn.check_hover(mouse_pos)
                    self.btn_resolution_back.check_hover(mouse_pos)
                elif self.menu_state == "CREDITS":
                    # HOVER DETECTION FOR CREDITS BACK BUTTON
                    self.btn_credits_back.check_hover(mouse_pos)
                else:
                    # HOVER DETECTION FOR MAIN MENU BUTTONS
                    self.btn_join.check_hover(mouse_pos)
                    self.btn_bot.check_hover(mouse_pos)
                    self.btn_options.check_hover(mouse_pos)
                    self.btn_exit.check_hover(mouse_pos)

            # SLIDER EVENT HANDLING (needs all event types: down, up, motion)
            if self.menu_state == "VOLUME":
                audio = AudioManager()

                if self.slider_music.handle_event(event):
                    audio.set_music_volume(self.slider_music.value)

                if self.slider_sfx.handle_event(event):
                    audio.set_sfx_volume(self.slider_sfx.value)



    def update(self):
        for shape in self.background_shapes:
            shape.update(self.screen_width, self.screen_height)

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))  # Fondo oscuro

        # Figures
        for shape in self.background_shapes:
            shape.draw(self.screen)

        if self.menu_state == "VOLUME":
            # ---- VOLUME MENU DRAW ----
            self.text_volume_title.draw(self.screen)

            self.slider_music.draw(self.screen)
            self.slider_sfx.draw(self.screen)

            self.btn_volume_back.draw(self.screen)

        elif self.menu_state == "RESOLUTION":
            # ---- RESOLUTION MENU DRAW ----
            self.text_resolution_title.draw(self.screen)

            for btn in self.res_buttons:
                btn.draw(self.screen)
                # Draw white border on top
                pygame.draw.rect(self.screen, self.WHITE, btn.button_rectangle, 3, border_radius=btn.CORNERS_RADIUS)

            self.checkbox_fullscreen.draw(self.screen)

            self.btn_resolution_back.draw(self.screen)

        elif self.menu_state == "OPTIONS":
            # ---- OPTIONS MENU DRAW ----
            self.text_options_title.draw(self.screen)

            self.btn_volume.draw(self.screen)
            self.btn_resolution.draw(self.screen)
            self.btn_credits.draw(self.screen)
            self.btn_back.draw(self.screen)

        elif self.menu_state == "CREDITS":
            # ---- CREDITS MENU DRAW ----
            self.text_credits_title.draw(self.screen)

            # Black box behind text
            pygame.draw.rect(self.screen, self.BLACK, self.credits_box_rect)
            pygame.draw.rect(self.screen, self.WHITE, self.credits_box_rect, 3)

            # Text lines
            self.screen.blit(self.credits_surface_1, self.credits_rect_1)
            self.screen.blit(self.credits_surface_2, self.credits_rect_2)

            self.btn_credits_back.draw(self.screen)
        else:
            # ---- MAIN MENU DRAW ----
            self.btn_join.draw(self.screen)
            self.btn_bot.draw(self.screen)
            self.btn_options.draw(self.screen)
            self.btn_exit.draw(self.screen)

            # TEXT DRAW
            self.text_title.draw(self.screen)


    def _start_bot_match(self):
        """Initialize bot and connect both bot and player to server for bot match"""
        print("[MAIN_SCREEN] Starting Bot Match (prompting for Bot ID)...")

        # Create an InputBox modal to get the bot id from the user
        WIDTH, HEIGHT = self.screen.get_size()
        box_w, box_h = int(600 * (WIDTH / 1280)), int(60 * (HEIGHT / 720))
        box_x = (WIDTH - box_w) // 2
        box_y = (HEIGHT // 3)

        input_box = InputBox((box_x, box_y), (box_w, box_h), "ENTER BOT ID (e.g. BOTSITO)")
        ok_btn = Button(((WIDTH // 2) - 80, box_y + box_h + 40), (160, 50), self.LIGHT_BLUE, "OK", self.BLACK, 24)
        cancel_btn = Button(((WIDTH // 2) + 120, box_y + box_h + 40), (160, 50), self.RED, "CANCEL", self.BLACK, 24)

        # Modal loop (blocks until user enters ID or cancels)
        modal_done = False
        bot_name = None
        clock = pygame.time.Clock()

        while not modal_done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if ok_btn.button_rectangle.collidepoint(event.pos) and len(input_box.user_input) > 0:
                        bot_name = input_box.user_input
                        modal_done = True
                    elif cancel_btn.button_rectangle.collidepoint(event.pos):
                        modal_done = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and len(input_box.user_input) > 0:
                        bot_name = input_box.user_input
                        modal_done = True
                    # forward to input box
                    if input_box.inputbox_rectangle.collidepoint(pygame.mouse.get_pos()):
                        if event.unicode.isalnum() and len(input_box.user_input) < input_box.max_length:
                            input_box.user_input += event.unicode
                        elif event.key == pygame.K_BACKSPACE:
                            input_box.user_input = input_box.user_input[:-1]

            # Draw modal
            self.screen.fill(self.MAINDARK)
            for shape in self.background_shapes:
                shape.draw(self.screen)

            # Draw input and buttons
            input_box.draw(self.screen)
            ok_btn.draw(self.screen)
            cancel_btn.draw(self.screen)

            pygame.display.flip()
            clock.tick(30)

        # If canceled, return to main menu
        if not bot_name:
            print("[MAIN_SCREEN] Bot match canceled by user")
            return

        print(f"[MAIN_SCREEN] Bot ID entered: {bot_name}")

        # Create bot player instance but do NOT connect yet (we'll start it once server is up)
        self.bot_instance = BotPlayer(bot_name)
        # Store bot reference in screen manager for other screens
        self.screen_manager.bot_instance = self.bot_instance

        # Prepare lobby: show player and bot
        lobby = self.screen_manager.screens.get("LOBBY")
        if lobby:
            lobby.textbox_nickname1.text = "YOU"
            lobby.textbox_nickname2.text = bot_name
            lobby.textbox_nickname2.text_color = self.WHITE

        # Move to Lobby screen
        self.screen_manager.change_screen("LOBBY")
