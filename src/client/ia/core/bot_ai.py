from typing import Dict, Any
import time

from .game_config_loader import GameConfigLoader


class BotAI:
    """
    Main orchestrator for the bot AI system.
    
    Pipeline:
    1. Analyze game state (GameStateAnalyzer)
    2. Make strategic decision (DecisionEngine with Simplex)
    3. Execute commands (UnitCommander)
    4. Send over network (Network)
    
    Runs on a decision cycle (default: every 500-1000ms depending on difficulty)
    """

    def __init__(self, player_id: int, difficulty: str, 
                 game_state_analyzer, decision_engine, unit_commander, network):
        """
        Initialize BotAI orchestrator
        
        Args:
            player_id: 1 or 2, which player is bot
            difficulty: "EASY", "MEDIUM", or "HARD"
            game_state_analyzer: GameStateAnalyzer instance
            decision_engine: DecisionEngine instance
            unit_commander: UnitCommander instance
            network: Network instance for sending commands
        """
        self.player_id = player_id
        self.difficulty = difficulty
        
        self.analyzer = game_state_analyzer
        self.decision_engine = decision_engine
        self.commander = unit_commander
        self.network = network
        
        # Difficulty parameters are the runtime source of truth for timing.
        self.config_loader = GameConfigLoader()
        self.difficulty_params = self.config_loader.get_difficulty_params(difficulty)

        # Decision cycle timing
        self.decision_cycle_ms = self._get_decision_cycle()
        self.last_decision_time = time.time() * 1000  # ms
        
        # Stats tracking
        self.decision_count = 0
        self.last_game_state = None
        self.last_decision = None

    def _get_decision_cycle(self) -> float:
        """
        Get decision cycle time based on difficulty
        
        Returns:
            Time in milliseconds between decisions
        """
        if self.difficulty_params:
            return float(self.difficulty_params.get("decision_interval_ms", 1000.0))

        if self.difficulty == "EASY":
            return 1500.0  # 1.5 seconds (slower, more predictable)
        elif self.difficulty == "MEDIUM":
            return 800.0   # 0.8 seconds
        elif self.difficulty == "HARD":
            return 300.0   # 0.3 seconds (very reactive)
        else:
            return 1000.0  # Default: 1 second

    def update(self, game_world, game_screen) -> bool:
        """
        Main update method - call this from game loop (60 FPS)
        
        Args:
            game_world: GameWorld instance
            game_screen: GameScreen instance (for player_gold)
        
        Returns:
            True if a decision was made, False if still in cooldown
        """
        
        # Check if enough time has passed
        current_time_ms = time.time() * 1000
        elapsed_ms = current_time_ms - self.last_decision_time
        
        if elapsed_ms < self.decision_cycle_ms:
            return False  # Not yet time for decision
        
        # ====================================
        # STEP 1: Analyze game state
        # ====================================
        
        current_gold = game_screen.player_gold
        game_state = self.analyzer.analyze(game_world, current_gold)
        self.last_game_state = game_state
        
        # ====================================
        # STEP 2: Make decision
        # ====================================
        
        decision = self.decision_engine.decide(game_state, current_gold)
        self.last_decision = decision
        
        # ====================================
        # STEP 3: Execute commands
        # ====================================
        
        commands = self.commander.execute_decision(decision, current_gold)
        
        # ====================================
        # STEP 4: Send commands to server
        # ====================================
        
        self._send_commands(commands)
        
        # ====================================
        # STEP 5: Update timing
        # ====================================
        
        self.last_decision_time = current_time_ms
        self.decision_count += 1
        
        return True

    def _send_commands(self, commands: list) -> None:
        """
        Send commands to server via network
        
        Args:
            commands: List of command dicts from UnitCommander (already formatted by JSON_Manager)
        """
        if not commands:
            return
        
        for cmd in commands:
            cmd_type = cmd.get("type")
            
            try:
                if cmd_type == "BUY_UNIT":
                    self._send_build_command(cmd)
                elif cmd_type == "MOVE_ORDER":
                    self._send_move_command(cmd)
                elif cmd_type == "ATTACK":
                    self._send_attack_command(cmd)
                else:
                    print(f"Warning: Unknown command type '{cmd_type}'")
            except Exception as e:
                print(f"Error sending command {cmd_type}: {e}")

    def _send_build_command(self, cmd: Dict[str, Any]) -> None:
        """
        Send build unit command via network
        
        Args:
            cmd: Command dict from JSON_Manager.get_unit_attacker() or get_unit_recolectors()
                Format: {"type": "BUY_UNIT", "payload": {"unit_type": "Attacker", "quantity": 1}}
        """
        try:
            self.network.send_json(cmd)
            print(f"[BotAI] Sent build command: {cmd.get('payload', {}).get('unit_type')}")
        except Exception as e:
            print(f"[BotAI] Error sending build command: {e}")

    def _send_move_command(self, cmd: Dict[str, Any]) -> None:
        """
        Send move order command via network
        
        Args:
            cmd: Command dict from JSON_Manager.get_moveorder()
                Format: {"type": "MOVE_ORDER", "payload": {"unit_id": ..., "target_x": ..., "target_y": ...}}
        """
        try:
            self.network.send_json(cmd)
            unit_id = cmd.get("payload", {}).get("unit_id")
            print(f"[BotAI] Sent move command for unit {unit_id}")
        except Exception as e:
            print(f"[BotAI] Error sending move command: {e}")

    def _send_attack_command(self, cmd: Dict[str, Any]) -> None:
        """
        Send attack command via network
        
        Args:
            cmd: Command dict from JSON_Manager.attack()
                Format: {"type": "ATTACK", "payload": {"attacker_id": ..., "target_id": ...}}
        """
        try:
            self.network.send_json(cmd)
            payload = cmd.get("payload", {})
            print(f"[BotAI] Sent attack command: attacker {payload.get('attacker_id')} → target {payload.get('target_id')}")
        except Exception as e:
            print(f"[BotAI] Error sending attack command: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get bot statistics for debugging
        
        Returns:
            Dict with performance metrics
        """
        return {
            "player_id": self.player_id,
            "difficulty": self.difficulty,
            "decision_count": self.decision_count,
            "decision_cycle_ms": self.decision_cycle_ms,
            "last_game_state": self.last_game_state,
            "last_decision": self.last_decision
        }
