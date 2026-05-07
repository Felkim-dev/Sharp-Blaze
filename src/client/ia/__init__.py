"""
Sharp-Blaze Bot AI Module
=========================

Organized by responsibility:

ia/core/   — AI decision logic ("what the bot thinks")
    BotAI, DecisionEngine, GameStateAnalyzer, UnitCommander,
    GameConfigLoader, BotConfig

ia/infra/  — Infrastructure ("how the bot communicates")
    BotNetworkClient, BotMatchSpawner

This __init__.py re-exports everything so external code can do:
    from ia import BotAI, BotNetworkClient
without knowing the internal package structure.
"""

# ── Core: AI brain ──
from .core import (
    BotAI,
    DecisionEngine,
    GameStateAnalyzer,
    UnitCommander,
    GameConfigLoader,
    BotConfig,
    ArcadeBotAI,
    ArcadeDecisionEngine,
    ArcadeGameStateAnalyzer,
)

# ── Infrastructure: networking & Docker ──
from .infra import (
    BotNetworkClient,
    BotMatchSpawner,
    BotMatchController,
    ArcadeMatchController,
)

__all__ = [
    # Core
    "BotAI",
    "DecisionEngine",
    "GameStateAnalyzer",
    "UnitCommander",
    "GameConfigLoader",
    "BotConfig",
    "ArcadeBotAI",
    "ArcadeDecisionEngine",
    "ArcadeGameStateAnalyzer",
    # Infra
    "BotNetworkClient",
    "BotMatchSpawner",
    "BotMatchController",
    "ArcadeMatchController",
]
