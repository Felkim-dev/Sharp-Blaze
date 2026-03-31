import pygame

COMPONENTS_FONT = r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\assets\IntroRust.otf"

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
        self.font_size = RectangleDimension[1]//2
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
