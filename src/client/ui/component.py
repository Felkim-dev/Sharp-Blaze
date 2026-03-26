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
        self.CORNERS_RADIUS = 7
        
        #COLORS
        self.WHITE = (255, 255, 255)
        
        # Figures Instantiation
            #Rectangle
        self.button_rectangle = pygame.Rect(Position,(RectangleDimension))
            #Text
        self.text_surface = self.button_font.render(Text,True,TextColor)

        # Text Centered in relation with the rectangle
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.center = self.button_rectangle.center
    
    def check_hover(self,mouse_pos):
        """If the mouse is on the button then it changes the color
        """
        if self.button_rectangle.collidepoint(mouse_pos):
            self.ButtonColor = self.WHITE
        else: 
            self.ButtonColor = self.ButtonColor_copy
    
    def draw(self,screen):
        #Draw rectangle on the scree
        pygame.draw.rect(screen,self.ButtonColor,self.button_rectangle, border_radius= self.CORNERS_RADIUS)
        
        #Draw the text (text_surface) on a invisible rectangle (text_rect)
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
        
        #Strings
            #DEFAULT
        self.default_string = DefaultText
            #USER INPUT
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
            #Rectangle
        self.inputbox_rectangle = pygame.Rect(Position, (RectangleDimension))
        
            #Text renders
                #DEFAULT TEXT
        self.text_surface_DEFAULT = self.inputbox_font.render(self.default_string, True, self.GRAY)
                #USERT TEXT
        self.text_surface_USER = self.inputbox_font.render(self.user_input, True, self.WHITE)

        # TEXT CENTER INTO THE RECTANGLE
            # DEFAULT TEXT
        self.text_rect_DEFAULT = self.text_surface_DEFAULT.get_rect()
        self.text_rect_DEFAULT.center = self.inputbox_rectangle.center

            # USER DEFAULT TEXT
        self.text_rect_USER = self.text_surface_USER.get_rect()
        self.text_rect_USER.center = self.inputbox_rectangle.center

        # INITIAL STATES
        self.is_selected = False

        # RESTRICTIONS
        self.max_length = MaxLength
        self.notallowed_chars = NotAllowedChars

    def draw(self,screen):

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
