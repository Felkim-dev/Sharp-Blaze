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

        self.BG_COLOR = (0,0,0)
        self.BORDER_COLOR = (255,255,255)
        self.BORDER_SIZE = 5
        
        self.DEFAULT_TEXT_COLOR = (84,84,84)
        self.button_font = pygame.font.Font(r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\assets\IntroRust.otf",25,)
        self.corners_radius = 7

        # Figures Instantiation
        self.button_rectangle = pygame.Rect(Position, (RectangleDimension))
        self.text_surface = self.button_font.render(self.default_string, True, self.DEFAULT_TEXT_COLOR)

        # Text Rec Center
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.center = self.button_rectangle.center

    def draw(self,screen):
        
        #BGCOLOR
        pygame.draw.rect(screen,self.BG_COLOR,self.button_rectangle, border_radius= self.corners_radius)
        #BORDER COLOR
        pygame.draw.rect(screen,self.BORDER_COLOR,self.button_rectangle, self.BORDER_SIZE, border_radius=self.corners_radius,)
        
        screen.blit(self.text_surface, self.text_rect)
