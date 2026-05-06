import pygame
import os

from ui.component import Button, Text, Slider
from utils.audio import AudioManager

# Pause menu overlay displayed during gameplay.
# Phase 1: Visual only -- no actual game freeze, no network messages.


class PauseOverlay:
    """In-game pause menu overlay with volume controls and surrender option.

    State machine: MAIN -> VOLUME, MAIN -> SURRENDER_CONFIRM.
    Draws a centered celeste (#0cc0df) panel on top of the game world.
    Handles its own widget events and returns actions to GameScreen.
    """
    def __init__(self, screen, screen_manager, audio_manager):
        self.screen = screen
        self.screen_manager = screen_manager
        self.audio_manager = audio_manager

        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        self.state = "MAIN"  # "MAIN", "VOLUME", "SURRENDER_CONFIRM"
        self.is_initiator = True  # True if this player initiated the pause

        # Panel dimensions and position (centered on screen)
        panel_width = int(600 * sx)
        panel_height = int(300 * sy)
        panel_x = (self.screen.get_width() - panel_width) // 2
        panel_y = (self.screen.get_height() - panel_height) // 2

        self.panel_width = panel_width
        self.panel_height = panel_height
        self.panel_x = panel_x
        self.panel_y = panel_y

        self.bg_color = (12, 192, 223, 200)  # #0cc0df at ~78% opacity
        self.temp_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(
            self.temp_surface,
            self.bg_color,
            (0, 0, panel_width, panel_height),
            border_radius=15,
        )

        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        TITLE_FONT = os.path.join(CURRENT_DIR, "..", "assets", "Anton-Regular.ttf")

        # Title using Anton font
        title_pos = (panel_x + panel_width // 2, panel_y + int(50 * sy))
        title_size = int(70 * sy)
        self.title = Text(title_pos, "Pause", title_size, (255, 255, 255), TITLE_FONT)
        self.title_foreign = Text(title_pos, "GAME PAUSED", title_size, (255, 255, 255), TITLE_FONT)

        # Main menu buttons (centered within panel)
        btn_w = int(350 * sx)
        btn_h = int(40 * sy)
        btn_x = panel_x + (panel_width - btn_w) // 2
        btn_y = panel_y + int(110 * sy)
        separation_y = int(50 * sy)

        self.btn_resume = Button(
            (btn_x, btn_y + separation_y * 0),
            (btn_w, btn_h),
            (0, 159, 12),
            "RESUME",
            (0, 0, 0),
            int(24 * sy),
        )

        self.btn_volume = Button(
            (btn_x, btn_y + separation_y * 1),
            (btn_w, btn_h),
            (0, 212, 255),  # #00d4ff
            "Volume",
            (0, 0, 0),
            int(24 * sy),
        )

        self.btn_surrender = Button(
            (btn_x, btn_y + separation_y * 2),
            (btn_w, btn_h),
            (204, 5, 35),  # #cc0523
            "Surrender",
            (0, 0, 0),
            int(24 * sy),
        )

        # Volume submenu: title, back button, sliders
        self.text_volume_title = Text(
            title_pos, "Volume", title_size, (255, 255, 255), TITLE_FONT
        )
        
        self.btn_volume_back = Button(
            (btn_x, self.panel_y + self.panel_height - int(80 * sy)),
            (btn_w, btn_h),
            (204, 5, 35),
            "Back",
            (0, 0, 0),
            int(24 * sy),
        )
        
        label_area_width = int(160 * sx)
        gap = int(20 * sx)
        bar_width = int(220 * sx)
        bar_height = int(25 * sy)
        total_width = label_area_width + gap + bar_width
        block_left = panel_x + (panel_width - total_width) // 2
        
        label_right_x = block_left + label_area_width
        bar_x = label_right_x + gap
        slider_y_music = panel_y + int(120 * sy)
        slider_y_sfx = slider_y_music + int(55 * sy)
        label_size_slider = int(22 * sy)
        
        # Music and Effects volume sliders
        self.slider_music = Slider(
            label_y=slider_y_music,
            label_right_x=label_right_x,
            bar_x=bar_x,
            bar_width=bar_width,
            bar_height=bar_height,
            label_text="Music:",
            initial_value=int(self.audio_manager.music_volume * 100),
            label_size=label_size_slider,
        )
        
        self.slider_sfx = Slider(
            label_y=slider_y_sfx,
            label_right_x=label_right_x,
            bar_x=bar_x,
            bar_width=bar_width,
            bar_height=bar_height,
            label_text="Effects:",
            initial_value=int(self.audio_manager.sfx_volume * 100),
            label_size=label_size_slider,
        )
        
        # Surrender confirmation dialog
        confirm_text_y = panel_y + int(140 * sy)
        self.text_confirm = Text(
            (panel_x + panel_width // 2, confirm_text_y),
            "Are you sure you want to surrender?",
            int(28 * sy),
            (204, 5, 35),
            TITLE_FONT,
        )

        si_btn_w = int(180 * sx)
        si_btn_h = int(40 * sy)
        si_btn_gap = int(20 * sx)
        si_btn_total_w = si_btn_w * 2 + si_btn_gap
        si_btn_x = panel_x + (panel_width - si_btn_total_w) // 2
        si_btn_y = panel_y + int(200 * sy)

        self.btn_si = Button(
            (si_btn_x, si_btn_y),
            (si_btn_w, si_btn_h),
            (204, 5, 35),
            "Yes",
            (0, 0, 0),
            int(22 * sy),
        )

        self.btn_no = Button(
            (si_btn_x + si_btn_w + si_btn_gap, si_btn_y),
            (si_btn_w, si_btn_h),
            (84, 84, 84),
            "No",
            (0, 0, 0),
            int(22 * sy),
        )

    def draw(self, screen):
        """Render the overlay based on current state."""
        if self.state is None:
            return

        if self.state == "MAIN":
            screen.blit(self.temp_surface, (self.panel_x, self.panel_y))
            if self.is_initiator:
                self.title.draw(screen)
            else:
                self.title_foreign.draw(screen)
            mouse_pos = pygame.mouse.get_pos()
            self.btn_resume.check_hover(mouse_pos)
            self.btn_resume.draw(screen)
            self.btn_volume.check_hover(mouse_pos)
            self.btn_volume.draw(screen)
            self.btn_surrender.check_hover(mouse_pos)
            self.btn_surrender.draw(screen)

        elif self.state == "VOLUME":
            self._draw_volume_submenu(screen)
        elif self.state == "SURRENDER_CONFIRM":
            self._draw_surrender_confirm(screen)

    def handle_events(self, events):
        """Process events for interactive widgets. Returns action string or None."""
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if self.state == "MAIN":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_resume.button_rectangle.collidepoint(mouse_pos):
                        self.state = None
                        AudioManager().play_click()
                        return "resume"
                    if self.btn_volume.button_rectangle.collidepoint(mouse_pos):
                        self.state = "VOLUME"
                        AudioManager().play_click()
                        return "volume"
                    if self.btn_surrender.button_rectangle.collidepoint(mouse_pos):
                        self.state = "SURRENDER_CONFIRM"
                        AudioManager().play_click()
                        return "surrender"

            elif self.state == "VOLUME":
                return self._handle_volume_events(event, mouse_pos)
            elif self.state == "SURRENDER_CONFIRM":
                return self._handle_surrender_confirm_events(event, mouse_pos)

        return None

    def update_volumes(self):
        """Sync slider positions with AudioManager values."""
        if hasattr(self, 'slider_music'):
            self.slider_music.value = int(self.audio_manager.music_volume * 100)
        if hasattr(self, 'slider_sfx'):
            self.slider_sfx.value = int(self.audio_manager.sfx_volume * 100)

    def _draw_volume_submenu(self, screen):
        """Draw the Volume submenu (panel, title, back, sliders)."""
        screen.blit(self.temp_surface, (self.panel_x, self.panel_y))
        self.text_volume_title.draw(screen)
        self.btn_volume_back.check_hover(pygame.mouse.get_pos())
        self.btn_volume_back.draw(screen)
        self.slider_music.draw(screen)
        self.slider_sfx.draw(screen)

    def _draw_surrender_confirm(self, screen):
        """Draw the surrender confirmation dialog."""
        screen.blit(self.temp_surface, (self.panel_x, self.panel_y))
        if self.is_initiator:
            self.title.draw(screen)
        else:
            self.title_foreign.draw(screen)
        self.text_confirm.draw(screen)
        mouse_pos = pygame.mouse.get_pos()
        self.btn_si.check_hover(mouse_pos)
        self.btn_si.draw(screen)
        self.btn_no.check_hover(mouse_pos)
        self.btn_no.draw(screen)

    def _handle_volume_events(self, event, mouse_pos):
        """Handle Volume submenu events (back, sliders). Returns action or None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_volume_back.button_rectangle.collidepoint(mouse_pos):
                self.state = "MAIN"
                AudioManager().play_click()
                return "back"
        
        if self.slider_music.handle_event(event):
            self.audio_manager.set_music_volume(self.slider_music.value)
            return "music_volume"
        
        if self.slider_sfx.handle_event(event):
            self.audio_manager.set_sfx_volume(self.slider_sfx.value)
            return "sfx_volume"
        
        return None

    def _handle_surrender_confirm_events(self, event, mouse_pos):
        """Handle surrender confirm events (X, Yes, No). Returns action or None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_si.button_rectangle.collidepoint(mouse_pos):
                AudioManager().play_click()
                return "surrender_confirm"
            if self.btn_no.button_rectangle.collidepoint(mouse_pos):
                self.state = "MAIN"
                AudioManager().play_click()
                return "cancel"
        return None
