"""
BotMatchController — Orchestrates a Player vs Bot match.

Responsibilities:
1. Spawns Docker game server (BotMatchSpawner)
2. Connects human player (existing NetworkManager)
3. Connects bot player (BotNetworkClient)
4. Synchronizes connections and sends START_GAME
5. Runs bot AI loop in a background thread
"""

import threading
import time
import traceback

from .bot_match_spawner import BotMatchSpawner
from .bot_network_client import BotNetworkClient
from .bot_game_world import BotGameWorld
from .bot_game_screen import BotGameScreen
from ..core.bot_ai import BotAI
from ..core.decision_engine import DecisionEngine
from ..core.game_state_analyzer import GameStateAnalyzer
from ..core.unit_commander import UnitCommander
from utils.json import JSON_Manager

class BotMatchController:
    def __init__(self, difficulty: str, human_network, screen_manager):
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
        """
        Full sequence to start the match in a separate thread so UI doesn't block.
        """
        # Start the sequence in a background thread
        threading.Thread(target=self._start_sequence, daemon=True).start()

    def _start_sequence(self):
        try:
            print(f"[BotController] Starting match with difficulty: {self.difficulty}")
            
            # Step 1: Spawn server
            self.spawner = BotMatchSpawner()
            self.server_info = self.spawner.spawn()
            
            # Wait for the server to be ready
            if not self.spawner.wait_for_server_ready():
                print("[BotController] Server failed to start.")
                self.screen_manager.network.connection_status = "ERROR"
                return

            time.sleep(1.0) # Give it a little more time to settle

            # Step 2: Inform human UI — human must connect FIRST to get Player 1.
            # The bot connects SECOND so the server assigns it Player 2.
            print("[BotController] Informing Human UI of Match...")
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
                    "global_player_id": 1,  # Human is always Player 1
                }
            }
            # Inject into the pending messages of the human network.
            # The LobbyScreen will process this in the main thread and connect.
            self.human_network.pending_messages.append(match_payload)

            # Wait for the human TCP connection to be established before the bot connects.
            # This guarantees that the server assigns Player 1 to the human and Player 2 to the bot.
            print("[BotController] Waiting for human client to connect (Player 1)...")
            human_connect_timeout = 8.0  # seconds
            human_connect_deadline = time.time() + human_connect_timeout
            while time.time() < human_connect_deadline:
                if self.human_network.connected:
                    print("[BotController] Human connected successfully as Player 1.")
                    break
                time.sleep(0.1)
            else:
                print("[BotController] WARNING: Human did not connect in time. "
                      "Bot may get Player 1 instead.")

            # Small extra delay to let the server fully register the human connection
            time.sleep(0.3)

            # Step 3: Connect Bot (always after human → becomes Player 2)
            print("[BotController] Connecting Bot as Player 2...")
            self.bot_network = BotNetworkClient()
            success = self.bot_network.connect_tcp(
                self.server_info["ip"],
                self.server_info["tcp_port"],
                "bot_ai",
                self.server_info["session_id"],
                self.server_info["token"]
            )
            
            if not success:
                print("[BotController] Bot failed to connect.")
                self.screen_manager.network.connection_status = "ERROR"
                return

            # Start bot loop thread to wait for START_GAME
            self.is_running = True
            self.bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
            self.bot_thread.start()

        except Exception as e:
            print(f"[BotController] Error during sequence: {e}")
            traceback.print_exc()
            self.screen_manager.network.connection_status = "ERROR"
            self.stop()

    def _bot_loop(self):
        """Background thread: runs bot AI decisions"""
        print("[BotController] Bot loop started.")
        bot_started = False
        
        while self.is_running:
            # Process incoming TCP messages
            data = self.bot_network.receive_json()
            if data:
                # Do not print every message if it's spammy, but for debugging it's ok
                # print(f"[BotNet RECV] {data.get('type')}")
                
                # Let screen handle resources/deaths/spawns
                self.bot_game_screen.process_tcp_message(data, self.bot_game_world)
                
                if data.get("type") == "START_GAME":
                    bot_started = True
                    payload = data.get("payload", {})
                    
                    # Init world
                    self.bot_game_world.load_initial_state(payload.get("units", {}), payload.get("structures", {}))
                    
                    # ====================================
                    # Extract and register shops & mines from structures
                    # ====================================
                    structures = payload.get("structures", {})
                    shops = {}
                    mines = {}
                    
                    for struct_id_str, pos in structures.items():
                        struct_id = int(struct_id_str)
                        # Shops: IDs 11000-11999
                        if 11000 <= struct_id < 12000:
                            shops[struct_id] = pos
                        # Mines: IDs 10000-10999
                        elif 10000 <= struct_id < 11000:
                            mines[struct_id] = pos
                    
                    if shops:
                        self.bot_game_world.register_shops(shops)
                    if mines:
                        self.bot_game_world.register_mines(mines)
                    
                    # Init AI
                    analyzer = GameStateAnalyzer(payload["player_id"])
                    decision_engine = DecisionEngine(self.difficulty)
                    commander = UnitCommander(
                        self.bot_game_world,
                        self.bot_network,
                        payload["player_id"],
                        self.difficulty,
                    )
                    
                    self.bot_ai = BotAI(
                        player_id=payload["player_id"],
                        difficulty=self.difficulty,
                        game_state_analyzer=analyzer,
                        decision_engine=decision_engine,
                        unit_commander=commander,
                        network=self.bot_network
                    )
                    
                    # Init UDP for bot
                    self.bot_network.init_udp(
                        self.server_info["ip"],
                        self.server_info["udp_port"],
                        payload["session_id"],
                        payload["player_id"]
                    )
                elif data.get("type") == "DISCONNECTED":
                    print("[BotController] Server disconnected.")
                    self.stop()
                    break

            if bot_started:
                # Update bot game world via UDP
                positions = self.bot_network.get_latest_positions()
                if positions:
                    self.bot_game_world.update_positions(positions)
                
                # Run AI update
                if self.bot_ai:
                    try:
                        self.bot_ai.update(self.bot_game_world, self.bot_game_screen)
                    except Exception as e:
                        print(f"[BotController] Error during bot_ai.update: {e}")
                        import traceback
                        traceback.print_exc()
            
            time.sleep(0.016)

    def stop(self):
        """Clean shutdown"""
        print("[BotController] Stopping match...")
        self.is_running = False
        if self.bot_network:
            self.bot_network.disconnect()
        if self.spawner:
            self.spawner.cleanup()