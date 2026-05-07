"""
ia.core — AI decision-making logic (the "brain" of the bot).

Contains:
- BotAI: Main orchestrator (decision cycle)
- DecisionEngine: Simplex LP optimizer
- GameStateAnalyzer: Threat, resource, positional metrics
- UnitCommander: Translates decisions into game commands
- GameConfigLoader: Reads combat_stats.json and bot_ai_config.json
- BotConfig: Difficulty parameter accessor
"""

from .bot_ai import BotAI
from .decision_engine import DecisionEngine
from .game_state_analyzer import GameStateAnalyzer
from .unit_commander import UnitCommander
from .game_config_loader import GameConfigLoader
from .bot_config import BotConfig
from .arcade_bot_ai import ArcadeBotAI
from .arcade_decision_engine import ArcadeDecisionEngine
from .arcade_game_state_analyzer import ArcadeGameStateAnalyzer

__all__ = [
    "BotAI",
    "DecisionEngine",
    "GameStateAnalyzer",
    "UnitCommander",
    "GameConfigLoader",
    "BotConfig",
    "ArcadeBotAI",
    "ArcadeDecisionEngine",
    "ArcadeGameStateAnalyzer",
]
