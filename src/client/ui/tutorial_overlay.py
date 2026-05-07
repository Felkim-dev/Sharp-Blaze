import pygame
import os

from ui.component import TextBox, Button

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ANTON_FONT = os.path.join(CURRENT_DIR, "..", "assets", "Anton-Regular.ttf")


class TutorialOverlay:
    """Manages 6 tutorial pop-up modals triggered by game events in arcade mode."""

    def __init__(self, screen):
        self.screen = screen
        self.game_start_time = pygame.time.get_ticks()
        self.disabled = False
        self.active_step_index = -1

        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        BASE_W, BASE_H = 1280, 720
        sx = screen_w / BASE_W
        sy = screen_h / BASE_H

        self.steps = [
            {
                "trigger": "game_start",
                "text": "Welcome to Arcade Mode!\nDefeat the enemy base\nbefore time runs out!",
                "shown": False,
            },
            {
                "trigger": "first_move",
                "text": "Right-click on the map\nto move your units.",
                "shown": False,
            },
            {
                "trigger": "first_kill",
                "text": "Great shot! Destroy enemy\nunits to earn gold.",
                "shown": False,
            },
            {
                "trigger": "shop_open",
                "text": "Buy units from the shop.\nAttackers cost 200g,\nBombs cost 1000g.",
                "shown": False,
            },
            {
                "trigger": "bomb_purchased",
                "text": "Bomb purchased! Move it\nnear the enemy base\nto deal massive damage.",
                "shown": False,
            },
            {
                "trigger": "bomb_near_base",
                "text": "Your bomb is near the\nenemy base! Watch it\nexplode and destroy it!",
                "shown": False,
            },
        ]

        box_w = int(600 * sx)
        box_h = int(200 * sy)
        box_x = (screen_w - box_w) // 2
        box_y = (screen_h - box_h) // 2
        text_size = int(22 * sy)

        self.modal_box = TextBox(
            (box_x, box_y),
            (box_w, box_h),
            (20, 20, 30),
            "",
            (255, 255, 255),
            text_size,
        )

        btn_w = int(120 * sx)
        btn_h = int(40 * sy)
        btn_x = (screen_w - btn_w) // 2
        btn_y = box_y + box_h + int(20 * sy)
        btn_text_size = int(20 * sy)

        self.ok_button = Button(
            (btn_x, btn_y),
            (btn_w, btn_h),
            (84, 84, 84),
            "OK",
            (255, 255, 255),
            btn_text_size,
        )

    def check_triggers(self, trigger, data=None):
        if self.disabled:
            return
        if self.active_step_index != -1:
            return

        for i, step in enumerate(self.steps):
            if not step["shown"] and step["trigger"] == trigger:
                step["shown"] = True
                self.active_step_index = i
                self.modal_box.update_text(step["text"])
                break

    def update(self):
        if self.disabled:
            return
        elapsed = pygame.time.get_ticks() - self.game_start_time
        if elapsed >= 60000:
            self.disabled = True
            self.active_step_index = -1

    def handle_event(self, event):
        if self.active_step_index == -1:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.ok_button.button_rectangle.collidepoint(event.pos):
                self.active_step_index = -1
                return True
        return False

    def is_active(self):
        return self.active_step_index != -1

    def draw(self):
        if self.active_step_index == -1:
            return

        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()

        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        self.modal_box.draw(self.screen)
        self.ok_button.draw(self.screen)
