import json
import os

class BotConfig:
    def __init__(self):
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..","..",
            "config",
            "bot_ai_config.json"
        )
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def get_difficulty(self, difficulty: str):
        """ Return paramters about the difficulty """
        return self.config['difficulties'].get(difficulty)
    
bot_config = BotConfig()
easy_params = bot_config.get_difficulty("EASY")
print(easy_params['decision_interval_ms'])