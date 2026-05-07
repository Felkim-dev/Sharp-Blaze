"""Game loop for bot execution in separate thread"""

import threading
import time
from typing import Optional, Callable
from ia.bot_player import BotPlayer
from ia.bot_ai import BotAI


class BotGameLoop:
    """Manages bot execution in a background thread"""

    def __init__(
        self,
        bot_player: BotPlayer,
        session_id: int,
        player_id: int,
        local_player_id: str,
        enemy_player_id: str,
        difficulty: str = "normal",
        tick_rate_ms: int = 500
    ):
        """Initialize bot game loop
        
        Args:
            bot_player (BotPlayer): Bot connection handler
            session_id (int): Session ID
            player_id (int): Player ID (1 or 2)
            local_player_id (str): Local player name
            enemy_player_id (str): Enemy player name
            difficulty (str): AI difficulty
            tick_rate_ms (int): Update frequency in milliseconds
        """
        self.bot_player = bot_player
        self.session_id = session_id
        self.player_id = player_id
        
        # AI brain
        self.bot_ai = BotAI(
            bot_player,
            session_id,
            player_id,
            local_player_id,
            enemy_player_id,
            difficulty
        )
        
        # Loop control
        self.tick_rate_ms = tick_rate_ms
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Callbacks
        self.on_decision_callback: Optional[Callable[[str], None]] = None
        
        # Statistics
        self.total_ticks = 0
        self.start_time = None
        self.end_time = None

    def start(self) -> bool:
        """Start the bot game loop in a background thread
        
        Returns:
            bool: True if successfully started
        """
        with self._lock:
            if self.running:
                print("[BOT-LOOP] Already running")
                return False
            
            if not self.bot_player.connected:
                print("[BOT-LOOP] Bot not connected")
                return False
            
            self.running = True
            self.start_time = time.time()
            self.total_ticks = 0
            
            self._thread = threading.Thread(
                target=self._game_loop,
                daemon=True,
                name="BotGameLoop"
            )
            self._thread.start()
            print("[BOT-LOOP] Started")
            return True

    def stop(self):
        """Stop the bot game loop
        
        Returns:
            dict: Final statistics
        """
        with self._lock:
            self.running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        self.end_time = time.time()
        print("[BOT-LOOP] Stopped")
        
        return self.get_statistics()

    def _game_loop(self):
        """Main game loop running in background thread"""
        tick_time_seconds = self.tick_rate_ms / 1000.0
        
        try:
            while self.running:
                tick_start = time.time()
                
                # Check if still connected
                if not self.bot_player.connected:
                    print("[BOT-LOOP] Connection lost, stopping")
                    break
                
                # Update AI and get decision
                decision = self.bot_ai.update()
                
                # Invoke callback if decision made
                if decision and self.on_decision_callback:
                    try:
                        self.on_decision_callback(decision)
                    except Exception as e:
                        print(f"[BOT-LOOP] Callback error: {e}")
                
                self.total_ticks += 1
                
                # Maintain tick rate
                elapsed = time.time() - tick_start
                if elapsed < tick_time_seconds:
                    time.sleep(tick_time_seconds - elapsed)
        
        except Exception as e:
            print(f"[BOT-LOOP] Unexpected error: {e}")
        finally:
            self.running = False

    def is_running(self) -> bool:
        """Check if loop is running
        
        Returns:
            bool: True if running
        """
        with self._lock:
            return self.running

    def get_ai_statistics(self) -> dict:
        """Get AI statistics
        
        Returns:
            dict: AI statistics
        """
        return self.bot_ai.get_statistics()

    def get_state_summary(self) -> str:
        """Get current state summary
        
        Returns:
            str: Formatted state
        """
        return self.bot_ai.get_current_state_summary()

    def get_statistics(self) -> dict:
        """Get loop statistics
        
        Returns:
            dict: Statistics about bot execution
        """
        elapsed = (
            (self.end_time or time.time()) - self.start_time
        ) if self.start_time else 0
        
        return {
            "running": self.running,
            "total_ticks": self.total_ticks,
            "elapsed_seconds": elapsed,
            "tick_rate_ms": self.tick_rate_ms,
            "estimated_ticks_per_second": self.total_ticks / elapsed if elapsed > 0 else 0,
            "ai_stats": self.bot_ai.get_statistics()
        }

    def set_decision_callback(self, callback: Callable[[str], None]):
        """Set callback to invoke when bot makes a decision
        
        Args:
            callback: Function to call with decision
        """
        self.on_decision_callback = callback
