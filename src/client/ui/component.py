import pygame

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
        self.text_string = Text
        self.button_font = pygame.font.Font(r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\assets\IntroRust.otf", TextSize)
        self.corners_radius = 7
        self.WHITE = (255, 255, 255)
        
        # Figures Instantiation
        self.button_rectangle = pygame.Rect(Position,(RectangleDimension))
        self.text_surface = self.button_font.render(Text,True,TextColor)

        # Text Rec Center
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.center = self.button_rectangle.center
    
    def check_hover(self,mouse_pos):
        
        if self.button_rectangle.collidepoint(mouse_pos):
            self.ButtonColor = self.WHITE
        else: 
            self.ButtonColor = self.ButtonColor_copy
    
    def draw(self,screen):
        
        pygame.draw.rect(screen,self.ButtonColor,self.button_rectangle, border_radius= self.corners_radius)
        screen.blit(self.text_surface, self.text_rect)

class InputBox:
    def __init__(
        self,
        Position: tuple,
        RectangleDimension: tuple,
        DefaultText: str
    ):
        # Characteristics
        self.Position = Position
        self.RectangleDimension = RectangleDimension
        self.default_string = DefaultText
        self.string_input = ""

        # COLORS
        self.BG_COLOR = (0,0,0)
        self.BORDER_COLOR = (255,255,255)
        self.DEFAULT_TEXT_COLOR = (84,84,84)

        # FONT
        self.button_font = pygame.font.Font(r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\assets\IntroRust.otf",25,)

        # INPUT DESIGN
        self.corners_radius = 7
        self.BORDER_SIZE = 5

        # Figures Instantiation
        self.button_rectangle = pygame.Rect(Position, (RectangleDimension))
        self.text_surface_DEFAULT = self.button_font.render(self.default_string, True, self.DEFAULT_TEXT_COLOR)
        self.text_surface_USER = self.button_font.render(self.string_input, True, self.BORDER_COLOR)

        # Text Rec Center
        self.text_rect = self.text_surface_DEFAULT.get_rect()
        self.text_rect.center = self.button_rectangle.center

        # INITIAL STATES
        self.is_selected = False

    def draw(self,screen):

        # BGCOLOR
        pygame.draw.rect(screen,self.BG_COLOR,self.button_rectangle, border_radius= self.corners_radius)
        # BORDER COLOR
        pygame.draw.rect(screen,self.BORDER_COLOR,self.button_rectangle, self.BORDER_SIZE, border_radius=self.corners_radius,)

        # Draw Object
        if self.is_selected or len(self.string_input)>0:
            self.text_surface_USER = self.button_font.render(self.string_input, True, self.BORDER_COLOR)
            screen.blit(self.text_surface_USER, self.text_rect)
        else:
            screen.blit(self.text_surface_DEFAULT, self.text_rect)
