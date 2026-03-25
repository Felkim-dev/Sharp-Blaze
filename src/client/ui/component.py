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
    pass
