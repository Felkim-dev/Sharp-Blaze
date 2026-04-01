from entities.units import Attacker,Recolectors

from utils.config import Config

class GameWorld:
    def __init__(self, network_manager):
        
        self.netwok = network_manager
        
        self.units = {}
        self.structures = {}
    
    def update(self):
        
        network_data = self.netwok.get_latest_positions()
        print(network_data)
        
        for entity_id,(net_x, net_y) in network_data.items():
            if entity_id not in self.units:
                self.units[entity_id] = Attacker(1,100,100)
            
            else:
                self.units[entity_id].update_target(net_x,net_y)
        
        for unit in self.units.values():
            unit.update_physics()
            
    def draw(self,screen):
        
        for unit in self.units.values():
            unit.draw(screen)
                