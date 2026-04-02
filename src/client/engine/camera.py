class Camera:
    def __init__(self, screen_width, screen_height, map_width, map_height):
        self.x = 0
        self.y = 0
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        self.map_width = map_width
        self.map_height = map_height
        
        self.speed = 15
    
    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        
        self.x = max(0, min(self.x, self.map_width - self.screen_width))
        self.y = max(0, min(self.y, self.map_height - self.screen_height))