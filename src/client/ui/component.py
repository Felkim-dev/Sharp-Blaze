import pygame

class Button:
    def __init__(self, Position:tuple,ButtonColor:tuple, RectangleDimension:tuple, Text:str, TextSize:int):
        
        #Characteristics
        self.Position = Position
        self.ButtonColor = ButtonColor
        self.RectangleDimension = RectangleDimension
        self.text_string = Text
        self.button_font = pygame.font.Font(r"C:\Users\felip\OneDrive\Escritorio\SEPTIMO_SEMESTRE\Sharp-Blaze\assets\IntroRust.otf", TextSize)
        
        #Figures Instantiation
        self.button_rectangle = pygame.Rect(Position,(RectangleDimension))
        self.text_surface = self.button_font.render(self.text_string,True,(0, 0, 0))
        
        # Text Rec Center
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.center = self.button_rectangle.center
        
    def draw(self,screen):
        
        pygame.draw.rect(screen,self.ButtonColor,self.button_rectangle,border_radius=7)
        screen.blit(self.text_surface, self.text_rect)
        

class InputBox:
    pass