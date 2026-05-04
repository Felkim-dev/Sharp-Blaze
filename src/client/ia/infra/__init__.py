"""
ia.infra — Infrastructure layer (networking and Docker).

Contains:
- BotNetworkClient: Headless TCP/UDP client for the bot (no Pygame)
- BotMatchSpawner: Spawns Docker game server for bot matches (no broker)
"""

from .bot_network_client import BotNetworkClient
from .bot_match_spawner import BotMatchSpawner
from .bot_match_controller import BotMatchController

__all__ = [
    "BotNetworkClient",
    "BotMatchSpawner",
    "BotMatchController",
]
