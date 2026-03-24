import pygame

class Button:
    def __init__(self, Position:tuple,ButtonColor:tuple, RectangleDimension:tuple, Text:str, TextSize:int):
        
        #Characteristics
        self.Position = Position
        self.ButtonColor = ButtonColor
        self.RectangleDimension = RectangleDimension
        self.text_string = Text
        self.button_font = pygame.font.SysFont("Intro Rust", TextSize, bold= True)
        
        #Figures Instantiation
        self.button_rectangle = pygame.Rect(Position,(RectangleDimension))
        self.button_text = self.button_font.render(self.text_string,True,(255, 255, 255))
        
    def draw(self,screen):
        pygame.draw.rect(screen,self.ButtonColor,self.button_rectangle)
        screen.blit(self.button_text,(self.Position[0] + self.RectangleDimension[0]/2 ,self.Position[1]+self.RectangleDimension[1]/3))
        

class InputBox:
    pass