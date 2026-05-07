import threading
import time
import traceback

from .bot_match_spawner import BotMatchSpawner
from .bot_network_client import BotNetworkClient
from .bot_game_world import BotGameWorld
from .bot_game_screen import BotGameScreen
from ..core.arcade_bot_ai import ArcadeBotAI
from ..core.arcade_decision_engine import ArcadeDecisionEngine
from ..core.arcade_game_state_analyzer import ArcadeGameStateAnalyzer

class ArcadeMatchController:
    def __init__(self, difficulty, human_network, screen_manager):
        self.difficulty = difficulty
        self.human_network = human_network
        self.screen_manager = screen_manager
        self.spawner = None
        self.bot_network = None
        self.bot_game_world = BotGameWorld()
        self.bot_game_screen = BotGameScreen()
        self.bot_ai = None
        self.bot_thread = None
        self.is_running = False

    def start_match(self):
        threading.Thread(target=self._start_sequence, daemon=True).start()

    def _start_sequence(self):
        try:
            print(f"[ArcadeController] Starting arcade match with difficulty: {self.difficulty}")

            self.spawner = BotMatchSpawner()
            self.server_info = self.spawner.spawn()

            if not self.spawner.wait_for_server_ready():
                print("[ArcadeController] Server failed to start.")
                self.screen_manager.network.connection_status = "ERROR"
                return

            time.sleep(1.0)

            match_payload = {
                "type": "BROKER_MATCH_FOUND",
                "payload": {
                    "ip": self.server_info["ip"],
                    "port": self.server_info["tcp_port"],
                    "udp_port": self.server_info["udp_port"],
                    "session_id": self.server_info["session_id"],
                    "token": self.server_info["token"],
                    "you": "human_player",
                    "opponent": "bot_ai",
                    "global_player_id": 1,
                }
            }
            self.human_network.pending_messages.append(match_payload)

            print("[ArcadeController] Waiting for human client to connect (Player 1)...")
            human_connect_timeout = 8.0
            human_connect_deadline = time.time() + human_connect_timeout
            while time.time() < human_connect_deadline:
                if self.human_network.connected:
                    print("[ArcadeController] Human connected successfully as Player 1.")
                    break
                time.sleep(0.1)
            else:
                print("[ArcadeController] WARNING: Human did not connect in time.")

            time.sleep(0.3)

            print("[ArcadeController] Connecting Bot as Player 2...")
            self.bot_network = BotNetworkClient()
            success = self.bot_network.connect_tcp(
                self.server_info["ip"],
                self.server_info["tcp_port"],
                "bot_ai",
                self.server_info["session_id"],
                self.server_info["token"]
            )

            if not success:
                print("[ArcadeController] Bot failed to connect.")
                self.screen_manager.network.connection_status = "ERROR"
                return

            self.is_running = True
            self.bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
            self.bot_thread.start()

        except Exception as e:
            print(f"[ArcadeController] Error during sequence: {e}")
            traceback.print_exc()
            self.screen_manager.network.connection_status = "ERROR"
            self.stop()

    def _bot_loop(self):
        print("[ArcadeController] Bot loop started.")
        bot_started = False

        while self.is_running:
            data = self.bot_network.receive_json()
            if data:
                self.bot_game_screen.process_tcp_message(data, self.bot_game_world)

                if data.get("type") == "START_GAME":
                    bot_started = True
                    payload = data.get("payload", {})
                    self.bot_game_world.load_initial_state(payload.get("units", {}), payload.get("structures", {}))

                    analyzer = ArcadeGameStateAnalyzer(payload["player_id"])
                    decision_engine = ArcadeDecisionEngine()

                    self.bot_ai = ArcadeBotAI(
                        player_id=payload["player_id"],
                        difficulty=self.difficulty,
                        game_state_analyzer=analyzer,
                        decision_engine=decision_engine,
                        network=self.bot_network
                    )

                    self.bot_network.init_udp(
                        self.server_info["ip"],
                        self.server_info["udp_port"],
                        payload["session_id"],
                        payload["player_id"]
                    )
                elif data.get("type") == "DISCONNECTED":
                    print("[ArcadeController] Server disconnected.")
                    self.stop()
                    break

            if bot_started:
                positions = self.bot_network.get_latest_positions()
                if positions:
                    self.bot_game_world.update_positions(positions)

                if self.bot_ai:
                    try:
                        self.bot_ai.update(self.bot_game_world, self.bot_game_screen)
                    except Exception as e:
                        print(f"[ArcadeController] Error during bot_ai.update: {e}")
                        traceback.print_exc()

            time.sleep(0.016)

    def stop(self):
        print("[ArcadeController] Stopping match...")
        self.is_running = False
        if self.bot_network:
            self.bot_network.disconnect()
        if self.spawner:
            self.spawner.cleanup()
