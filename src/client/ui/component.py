import pygame
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENTS_FONT = os.path.join(CURRENT_DIR, "..","assets", "IntroRust.otf")

class Button:

    def __init__(
        self,
        Position: tuple,
        RectangleDimension: tuple,
        ButtonColor: tuple,
        Text: str,
        TextColor:tuple,
        TextSize: int,
    ):

        # Characteristics
        self.Position = Position
        self.ButtonColor = ButtonColor
        self.ButtonColor_copy = ButtonColor
        self.RectangleDimension = RectangleDimension
        self.button_text = Text
        self.button_font = pygame.font.Font(COMPONENTS_FONT, TextSize)
        self.text = Text
        self.text_color = TextColor
        self.CORNERS_RADIUS = 7

        # COLORS
        self.WHITE = (255, 255, 255)
        self.LIGHTGRAY = (112, 112, 112)

        # Figures Instantiation
        # Rectangle
        self.button_rectangle = pygame.Rect(Position,(RectangleDimension))

    def check_hover(self,mouse_pos):
        """If the mouse is on the button then it changes the color
        """
        if self.button_rectangle.collidepoint(mouse_pos):
            self.ButtonColor = self.WHITE
        else: 
            self.ButtonColor = self.ButtonColor_copy

    def draw(self,screen):

        # Draw rectangle on the screen
        pygame.draw.rect(screen,self.ButtonColor,self.button_rectangle, border_radius= self.CORNERS_RADIUS)

        # Text Draw
        self.text_surface = self.button_font.render(self.text, True, self.text_color)

        # Text Centered in relation with the rectangle
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.center = self.button_rectangle.center
        
        # Draw the text (text_surface) on a invisible rectangle (text_rect)
        screen.blit(self.text_surface, self.text_rect)

class InputBox:

    def __init__(
        self,
        Position: tuple,
        RectangleDimension: tuple,
        DefaultText: str,
        MaxLength: int = 15,
        NotAllowedChars: list = None,
    ):
        # Characteristics
        self.Position = Position
        self.RectangleDimension = RectangleDimension

        # Strings
        # DEFAULT
        self.default_string = DefaultText
        # USER INPUT
        self.user_input = ""

        # COLORS
        self.BLACK = (0,0,0)
        self.WHITE = (255,255,255)
        self.GRAY = (84,84,84)

        # FONT
        self.font_size = RectangleDimension[1] // 2
        self.inputbox_font = pygame.font.Font(COMPONENTS_FONT,self.font_size)

        # INPUT DESIGN
        self.CORNERS_RADIUS = 7
        self.BORDER_SIZE = 5

        # Figures Instantiation
        # Rectangle
        self.inputbox_rectangle = pygame.Rect(Position, (RectangleDimension))

        # INITIAL STATES
        self.is_selected = False

        # RESTRICTIONS
        self.max_length = MaxLength
        self.notallowed_chars = NotAllowedChars

    def draw(self,screen):

        # Text renders
        # DEFAULT TEXT
        self.text_surface_DEFAULT = self.inputbox_font.render(
            self.default_string, True, self.GRAY
        )
        # USERT TEXT
        self.text_surface_USER = self.inputbox_font.render(
            self.user_input, True, self.WHITE
        )

        # TEXT CENTER INTO THE RECTANGLE
        # DEFAULT TEXT
        self.text_rect_DEFAULT = self.text_surface_DEFAULT.get_rect()
        self.text_rect_DEFAULT.center = self.inputbox_rectangle.center

        # USER DEFAULT TEXT
        self.text_rect_USER = self.text_surface_USER.get_rect()
        self.text_rect_USER.center = self.inputbox_rectangle.center

        # DRAW OF THE BLACK RECTANGLE
        pygame.draw.rect(screen,self.BLACK,self.inputbox_rectangle, border_radius= self.CORNERS_RADIUS)
        # DRAW OF THE WHITE RECTANGLE
        pygame.draw.rect(screen,self.WHITE,self.inputbox_rectangle, self.BORDER_SIZE, border_radius=self.CORNERS_RADIUS,)

        # CONTINUOUS DRAWING COMPROBATION
        if self.is_selected or len(self.user_input)>0:
            # RENDER THE NEW TEXT OF THE USER
            self.text_surface_USER = self.inputbox_font.render(self.user_input, True, self.WHITE)

            # CENTERING THE TEXT OF THE USER
            self.text_rect_USER = self.text_surface_USER.get_rect()
            self.text_rect_USER.center = self.inputbox_rectangle.center

            # SHOWING ON THE SCREEN THE TEXT
            screen.blit(self.text_surface_USER, self.text_rect_USER)
        else:
            # SHOWING THE DEFAULT TEXT
            screen.blit(self.text_surface_DEFAULT, self.text_rect_DEFAULT)

class Text:

    def __init__(
        self,
        Position: tuple,
        Text: str,
        TextSize: int,
        Color: tuple,
        Font : str = COMPONENTS_FONT,
    ):
        self.position = Position
        self.text = Text
        self.text_size = TextSize
        self.color = Color
        self.font = Font
        self.text_definition = pygame.font.Font(self.font, self.text_size)

    def draw(self,screen):
        # Text Drawings

        text_surface = self.text_definition.render(self.text, True, self.color)
        text_position = text_surface.get_rect(center=(self.position))

        # Text drawing
        screen.blit(text_surface, text_position)

class TextBox:

    def __init__(
        self,
        Position: tuple,
        RectangleDimension: tuple,
        Rectangle_Color: tuple,
        Text: str,
        Text_Color: tuple,
        Text_size: int
        
    ):
        # Characteristics
        self.Position = Position
        self.RectangleDimension = RectangleDimension
        self.rectangle_color = Rectangle_Color

        # COLOR
        self.WHITE = (255, 255, 255)

        # Strings
        self.text= Text
        self.text_color = Text_Color

        # FONT
        self.font_size = Text_size
        self.inputbox_font = pygame.font.Font(COMPONENTS_FONT, self.font_size)

        # INPUT DESIGN
        self.CORNERS_RADIUS = 7
        self.BORDER_SIZE = 5

        # Figures Instantiation
        # Rectangle
        self.textbox_rectangle = pygame.Rect(Position, (RectangleDimension))

    def draw(self, screen):

        # Text render
        self.text_surface = self.inputbox_font.render(self.text, True, self.text_color)

        # TEXT CENTER INTO THE RECTANGLE
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.center = self.textbox_rectangle.center

        # DRAW OF THE TOP RECTANGLE
        pygame.draw.rect(screen,self.rectangle_color,self.textbox_rectangle,border_radius=self.CORNERS_RADIUS)
        # DRAW OF THE WHITE RECTANGLE
        pygame.draw.rect(screen,self.WHITE,self.textbox_rectangle,self.BORDER_SIZE,border_radius=self.CORNERS_RADIUS)

        screen.blit(self.text_surface, self.text_rect)

class CloseButton:
    def __init__(self, x, y, size=30):

        self.rect = pygame.Rect(x, y, size, size)

        # COLORS
        self.WHITE = (255, 255 , 255)

        # Thickness
        self.thickness = 5

    def handle_event(self, event):

        # Click Detect
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True 

        return False

    def draw(self, screen):

        pygame.draw.line(
            screen,
            self.WHITE,
            self.rect.topleft,
            self.rect.bottomright,
            self.thickness,
        )

        # Línea 2: De Abajo-Izquierda a Arriba-Derecha (/)
        pygame.draw.line(
            screen,
            self.WHITE,
            self.rect.bottomleft,
            self.rect.topright,
            self.thickness,
        )

class InfoBox(TextBox):

    def __init__(
        self,
        Position: tuple,
        RectangleDimension: tuple,
        Rectangle_Color: tuple,
        Text: str,
        Text_Variable: str,
        Text_Color: tuple,
        Text_size: int,
        Icon_Path:str
    ):
        super().__init__(
            Position=Position,
            RectangleDimension=RectangleDimension,
            Rectangle_Color=Rectangle_Color,
            Text=Text,
            Text_Color=Text_Color,
            Text_size=Text_size,
        )

        self.text_variable = Text_Variable

        raw_image = pygame.image.load(Icon_Path).convert_alpha()
        icon_size = self.RectangleDimension[1] - 10
        self.image = pygame.transform.scale(raw_image, (icon_size, icon_size))

    def update_text(self, new_value: str):
        """Allows updating the dynamic value (e.g., '54' to '100') without recreating the object."""
        self.text_variable = new_value

    def draw(self, screen):

        # Text render
        self.text_surface = self.inputbox_font.render(self.text, True, self.text_color)
        self.text_surface2 = self.inputbox_font.render(self.text_variable, True, self.text_color)

        # -------------------------------------------------------------
        # LAYOUT & ALIGNMENT MATH
        # -------------------------------------------------------------
        padding = 10  # Pixels of distance from the edges and between elements

        # A. Icon Positioning (Left side, padded inward)
        self.image_rect = self.image.get_rect()
        self.image_rect.centery = self.textbox_rectangle.centery
        self.image_rect.left = self.textbox_rectangle.left + padding

        # B. Constant Text Positioning ("GOLD" - Next to the icon)
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.centery = self.textbox_rectangle.centery
        self.text_rect.left = self.image_rect.right + padding

        # C. Variable Text Positioning ("54" - Right side, padded inward)
        self.text_rect2 = self.text_surface2.get_rect()
        self.text_rect2.centery = self.textbox_rectangle.centery
        self.text_rect2.right = self.textbox_rectangle.right - padding

        # DRAW OF THE TOP RECTANGLE
        pygame.draw.rect(
            screen,
            self.rectangle_color,
            self.textbox_rectangle,
            border_radius=self.CORNERS_RADIUS,
        )
        # DRAW OF THE WHITE RECTANGLE
        pygame.draw.rect(
            screen,
            self.WHITE,
            self.textbox_rectangle,
            self.BORDER_SIZE,
            border_radius=self.CORNERS_RADIUS,
        )

        screen.blit(self.text_surface,self.text_rect)
        screen.blit(self.text_surface2, self.text_rect2)
        screen.blit(self.image,self.image_rect)


class ShopButton(Button):

    def __init__(self, Position, RectangleDimension, ButtonColor, Text, TextColor, TextSize,CostText,ItemIconPath,GoldIconPath):
        super().__init__(Position, RectangleDimension, ButtonColor, Text, TextColor, TextSize)

        self.cost = int(CostText)
        self.is_active = False

        self.active_color = ButtonColor
        self.inactive_color = (204, 5, 35)

        self.cost_text = CostText
        self.BORDER_SIZE = 2

        padding = 10
        icon_size = self.RectangleDimension[1] - (padding * 2)

        raw_item = pygame.image.load(ItemIconPath).convert_alpha()
        self.item_icon = pygame.transform.scale(raw_item, (icon_size, icon_size))

        raw_gold = pygame.image.load(GoldIconPath).convert_alpha()
        self.gold_icon = pygame.transform.scale(raw_gold, (icon_size, icon_size))

    def update_availability(self, gold):
        if gold >= self.cost:
            self.is_active = True
            self.ButtonColor = self.active_color
        else:
            self.is_active = False
            self.ButtonColor = self.inactive_color


    def draw(self, screen):

        # -------------------------------------------------------------
        # 1. BACKGROUND & BORDERS
        # -------------------------------------------------------------

        # Draw the solid background
        pygame.draw.rect(
            screen,
            self.ButtonColor,
            self.button_rectangle,
            border_radius=self.CORNERS_RADIUS,
        )

        # Draw the outer white border
        pygame.draw.rect(
            screen,
            self.WHITE,
            self.button_rectangle,
            self.BORDER_SIZE,
            border_radius=self.CORNERS_RADIUS,
        )

        # -------------------------------------------------------------
        # 2. LAYOUT MATH (The 70/30 Split)
        # -------------------------------------------------------------

        # We calculate the X coordinate where the vertical divider line goes
        split_x = self.button_rectangle.left + int(self.button_rectangle.width * 0.7)

        # Draw the vertical divider line
        pygame.draw.line(
            screen,
            self.WHITE,
            (split_x, self.button_rectangle.top),
            (split_x, self.button_rectangle.bottom),
            self.BORDER_SIZE,
        )

        # Text rendering
        main_text_surf = self.button_font.render(self.text, True, self.text_color)
        cost_text_surf = self.button_font.render(self.cost_text, True, self.text_color)
        padding = 10

        # -------------------------------------------------------------
        # 3. LEFT SECTION: Item Icon + Main Text
        # -------------------------------------------------------------
        item_icon_rect = self.item_icon.get_rect()
        item_icon_rect.centery = self.button_rectangle.centery
        item_icon_rect.left = self.button_rectangle.left + padding

        main_text_rect = main_text_surf.get_rect()
        main_text_rect.centery = self.button_rectangle.centery
        # Center the text perfectly between the item icon and the divider line
        available_space = split_x - item_icon_rect.right
        main_text_rect.centerx = item_icon_rect.right + (available_space // 2)

        # -------------------------------------------------------------
        # 4. RIGHT SECTION: Coin Icon + Cost Text
        # -------------------------------------------------------------
        coin_icon_rect = self.gold_icon.get_rect()
        coin_icon_rect.centery = self.button_rectangle.centery
        coin_icon_rect.left = split_x + padding

        cost_text_rect = cost_text_surf.get_rect()
        cost_text_rect.centery = self.button_rectangle.centery
        cost_text_rect.left = coin_icon_rect.right + padding

        # -------------------------------------------------------------
        # 5. BLIT EVERYTHING
        # -------------------------------------------------------------
        screen.blit(self.item_icon, item_icon_rect)
        screen.blit(main_text_surf, main_text_rect)
        screen.blit(self.gold_icon, coin_icon_rect)
        screen.blit(cost_text_surf, cost_text_rect)
