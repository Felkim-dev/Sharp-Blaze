import pygame
import os

from ui.component import ShopButton
from ui.component import CloseButton

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TITLE_FONT = os.path.join(CURRENT_DIR, "..", "assets", "Anton-Regular.ttf")
GOLD_ICON = os.path.join(CURRENT_DIR, "..", "assets", "gold.png")
SWORD_ICON = os.path.join(CURRENT_DIR, "..", "assets", "sword.png")
HAT_ICON = os.path.join(CURRENT_DIR, "..", "assets", "hat.png")
BOMB_ICON = os.path.join(CURRENT_DIR, "..", "assets", "bomb.png")


class Shop:
    def __init__(self, is_arcade=False):

        # 1. Panel Dimensions and Position
        self.width = 500
        self.height = 382
        self.x = 50
        self.y = 200

        # UI Colors
        self.bg_color = (12, 192, 233, 150)
        self.button_color = (84, 84, 84)     # Dark Gray
        self.text_color = (255, 255, 255)    # White

        # 2. Pygame Font setup (FIXED: Using Font instead of SysFont for custom files)
        pygame.font.init()
        self.title_font = pygame.font.Font(TITLE_FONT, 70)

        # Render the Title Text
        self.title_surface = self.title_font.render("Store", True, self.text_color)
        self.title_rect = self.title_surface.get_rect()

        # Center the title horizontally inside the panel, and push it down a bit
        self.title_rect.centerx = self.x + (self.width // 2)
        self.title_rect.top = self.y + 45

        # -------------------------------------------------------------
        # 3. BUTTONS INSTANTIATION & LAYOUT
        # -------------------------------------------------------------
        btn_width = 380
        btn_height = 60
        btn_text_size = 22

        # Math: Center the buttons horizontally relative to the panel's X coordinate
        btn_x = self.x + ((self.width - btn_width) // 2)

        # Button 1: COLLECTORS
        btn1_y = self.y + 160
        self.collector_shop_button = ShopButton(
            Position=(btn_x, btn1_y),
            RectangleDimension=(btn_width, btn_height),
            ButtonColor=self.button_color,
            Text="COLLECTORS",
            TextColor=self.text_color,
            TextSize=btn_text_size,
            CostText="100",
            ItemIconPath=HAT_ICON,
            GoldIconPath=GOLD_ICON,
        )

        # Button 2: ATTACKERS
        btn2_y = self.y + 250  # Add 80px of vertical space
        self.attacker_shop_button = ShopButton(
            Position=(btn_x, btn2_y),
            RectangleDimension=(btn_width, btn_height),
            ButtonColor=self.button_color,
            Text="ATTACKERS",
            TextColor=self.text_color,
            TextSize=btn_text_size,
            CostText="200",
            ItemIconPath=SWORD_ICON,
            GoldIconPath=GOLD_ICON,
        )

        self.bomb_shop_button = ShopButton(
            Position=(btn_x, btn1_y),
            RectangleDimension=(btn_width, btn_height),
            ButtonColor=self.button_color,
            Text="BOMBS",
            TextColor=self.text_color,
            TextSize=btn_text_size,
            CostText="1000",
            ItemIconPath=BOMB_ICON,
            GoldIconPath=GOLD_ICON,
        )

        self.is_arcade = is_arcade

        self.cross_btn = CloseButton(self.x + self.width - 50, self.y + 20)

    def set_arcade_mode(self, enabled: bool):
        self.is_arcade = enabled

    def update(self, gold):
        """Updates color based on gold and processes mouse hover"""
        if self.is_arcade:
            self.bomb_shop_button.update_availability(gold)
            self.attacker_shop_button.update_availability(gold)
        else:
            self.collector_shop_button.update_availability(gold)
            self.attacker_shop_button.update_availability(gold)


    def handle_click(self, event,mouse_pos) -> str:
        """
        Checks if any button was clicked.
        Returns a string command ('CLOSE', 'BUY_COLLECTOR', 'BUY_ATTACKER') or None.
        """
        if self.cross_btn.handle_event(event):
            return "CLOSE"

        if self.is_arcade:
            if self.bomb_shop_button.button_rectangle.collidepoint(mouse_pos):
                if self.bomb_shop_button.is_active:
                    return "BUY_BOMB"
        else:
            if self.collector_shop_button.button_rectangle.collidepoint(mouse_pos):
                if self.collector_shop_button.is_active:
                    return "BUY_COLLECTOR"

        if self.attacker_shop_button.button_rectangle.collidepoint(mouse_pos):
            if self.attacker_shop_button.is_active:
                return "BUY_ATTACKER"

        return None

    def draw(self, screen):
        """Draws the shop panel and its buttons on the screen."""

        # We draw onto a temporary transparent surface to handle the alpha correctly
        # with rounded corners in Pygame.
        temp_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(
            temp_surface,
            self.bg_color,
            (0, 0, self.width, self.height),
            border_radius=15,
        )
        screen.blit(temp_surface, (self.x, self.y))

        # B. Draw the Title
        screen.blit(self.title_surface, self.title_rect)

        # C. Draw the Shop Buttons
        if self.is_arcade:
            self.bomb_shop_button.draw(screen)
        else:
            self.collector_shop_button.draw(screen)
        self.attacker_shop_button.draw(screen)
        self.cross_btn.draw(screen)
