import pygame

from ui.component import Button, Text,TextBox,CloseButton

import threading
import time
import shutil

try:
    import docker
    DOCKER_SDK_AVAILABLE = True
except Exception:
    docker = None
    DOCKER_SDK_AVAILABLE = False

from utils.config import Config
from utils.json import JSON_Manager
from ia.bot_game_loop import BotGameLoop
from utils.audio import AudioManager
class LobbyScreen:
    def __init__(self, screen_manager, screen):

        # SCREEN FROM THE MAIN GAME LOOP
        self.screen_manager = screen_manager
        self.screen = screen

        # SCALE FACTORS relative to base resolution 1280x720
        BASE_W, BASE_H = 1280, 720
        sx = self.screen.get_width() / BASE_W
        sy = self.screen.get_height() / BASE_H

        # COLORS
        # PRINCIPAL BG
        self.MAINDARK = (19, 23, 34)

        self.WHITE = (255, 255, 255)
        self.GRAY = (112, 112, 112)
        self.BLACK = (0, 0, 0)

        # PLAYER BOX SIZE (scaled)
        TEXT_WH = (int(300 * sx), int(50 * sy))

        # BUTTON SIZE (scaled)
        BUTTON_WH = (int(350 * sx), int(50 * sy))

        # TEXT SIZE
        TEXT_SIZE = BUTTON_WH[1]//2

        # EXIT MAIN MENU BUTTON
        width_screen = self.screen.get_width()
        button_size = int(30 * sy)
        margin = int(50 * sx)
        # POS CALCULATION
        pos_x = width_screen - button_size - margin
        pos_y = margin  

        # CLOSE BUTTON INSTANCE
        self.btn_close = CloseButton(pos_x, pos_y, button_size)

        # Positioning COMPONENTS
        # START BUTTON
        width_button = BUTTON_WH[0]
        center_x_button = self.screen.get_rect().centerx - (width_button // 2)

        # TEXT BOX
        width_text = TEXT_WH[0]
        center_x_text_player1 = self.screen.get_rect().centerx - width_text * 1.5
        center_x_text_player2 = self.screen.get_rect().centerx + width_text//2

        init_y = (self.screen.get_height() // 3) + int(50 * sy)

        # Button creation
        self.btn_Start = Button((center_x_button, init_y + int(100 * sy)),BUTTON_WH,self.GRAY,"START GAME",self.BLACK,TEXT_SIZE,)

        # TEXT BOX CREATION
        size_text_boxes = int(25 * sy)
        self.textbox_nickname1 = TextBox((center_x_text_player1, init_y),TEXT_WH,self.BLACK,"USER1",self.WHITE,size_text_boxes)
        self.textbox_nickname2 = TextBox((center_x_text_player2, init_y),TEXT_WH,self.BLACK,"USER2",self.WHITE,size_text_boxes)

        # Player text CREATION
        posx_text_player1 = center_x_text_player1 + width_text//2
        posy_text_player1 = init_y - int(40 * sy)
        self.text_player1 = Text((posx_text_player1, posy_text_player1), "YOU", TEXT_WH[1] // 2, self.WHITE)

        posx_text_player2 = center_x_text_player2 + width_text // 2
        posy_text_player2 = init_y - int(40 * sy)
        self.text_player2 = Text((posx_text_player2, posy_text_player2), "OPPONENT", TEXT_WH[1] // 2, self.WHITE)
        
        # Match state attributes (initialized for both broker and bot match flows)
        self.player_id = None
        self.local_player_id = None
        self.enemy_player_id = None
        self.session_id = None
        
        # Bot game loop state
        self.bot_game_loop = None
        self.bot_game_loop_started = False

    def handle_events(self, events, keys):
        """where screen manages the events of their buttons and input boxes"""
        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos

                    if self.textbox_nickname2.text != "WAITING..." and self.btn_Start.button_rectangle.collidepoint(mouse_pos):
                        AudioManager().play_click()

                        # If this is a bot match (bot instance present), spawn local server and connect both
                        if self.screen_manager.bot_instance and not Config.OFFLINE_DEBUG_MODE:
                            self._spawn_local_server_and_connect()

                        elif Config.OFFLINE_DEBUG_MODE: # DEBUG MODE
                            units = {
                                1000: (450, 4550),
                                1001: (550, 4450),
                                3002: (350, 4450),

                                6000: (4550,450),
                                6001: (4450,550),
                                8002: (4650,550)
                            }

                            structures = {
                                100: (300, 4700),
                                5000: (4700, 300),
                                # Neutral entity in the exact center of a 5000x5000 map
                                11000: (2500, 2500),
                                10000: (2000, 1000),
                                10001: (1000, 2000),
                            }

                            game_screen = self.screen_manager.screens["GAME"]
                            game_screen.load_initial_state(units,structures)
                            self.screen_manager.change_screen("GAME")

                        else:
                            # Send START_GAME with session_id if available (dedicated session)
                            session_id = getattr(self, 'session_id', None)
                            self.screen_manager.network.send_json(JSON_Manager.get_startgame(session_id))

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.textbox_nickname2.text != "WAITING...":
                    AudioManager().play_click()
                    if Config.OFFLINE_DEBUG_MODE:
                        units = {
                        1000: (450, 4550),
                        1001: (550, 4450),
                        3002: (350, 4450),
                        6000: (4550,450),
                        6001: (4450,550),
                        8002: (4650,550)
                            }

                        structures = {
                            100: (300, 4700),
                            5000: (4700, 300),
                            11000: (2500, 2500),
                            10000: (2000, 1000),
                            10001: (1000, 2000),
                        }

                        game_screen = self.screen_manager.screens["GAME"]
                        game_screen.load_initial_state(units,structures)
                        self.screen_manager.change_screen("GAME")
                    else:
                        session_id = getattr(self, 'session_id', None)
                        self.screen_manager.network.send_json(JSON_Manager.get_startgame(session_id))

            if self.btn_close.handle_event(event):
                AudioManager().play_click()
                self.screen_manager.network.disconnect()
                self.screen_manager.change_screen("MAIN")

            elif event.type == pygame.MOUSEMOTION:

                # MOUSE ON BUTTON DETECTION
                mouse_pos = event.pos

                if self.textbox_nickname2.text != "WAITING...":
                    self.btn_Start.check_hover(mouse_pos)

    def update(self):

        if not Config.OFFLINE_DEBUG_MODE:
            data = self.screen_manager.network.receive_json()

            if data:

                print(data)

                message_type = data.get("type") or data.get("action")

                if message_type == "QUEUE_STATUS":
                    self.textbox_nickname1.text = data["payload"]["you"]
                    self.textbox_nickname2.text = "WAITING..."
                    self.textbox_nickname2.text_color = (84, 84, 84)

                elif message_type == "BROKER_MATCH_FOUND":

                    self.local_player_id = data["payload"]["you"]
                    self.enemy_player_id = data["payload"]["opponent"]

                    self.session_id = data["payload"]["session_id"]
                    self.player_id = data["payload"]["global_player_id"]

                    self.textbox_nickname1.text = self.local_player_id
                    self.textbox_nickname2.text = self.enemy_player_id

                    self.textbox_nickname2.text_color = self.WHITE

                    self.screen_manager.network.connect_to_game_server(data["payload"])

                if message_type == "START_GAME" and data["payload"]["start"]:

                    units = data["payload"]["units"]

                    structures = data["payload"]["structures"]

                    gold = data["payload"]["gold"]

                    obstacles = data["payload"]["obstacles"]

                    game_screen = self.screen_manager.screens["GAME"]

                    game_screen.load_initial_state(gold,units,structures, self.player_id,obstacles,self.local_player_id,self.enemy_player_id)

                    self.screen_manager.network.init_udp_connection(self.session_id,self.player_id)
                    
                    # Initialize bot game loop if this is a bot match
                    if self.screen_manager.bot_instance and not self.bot_game_loop_started:
                        print("[LOBBY] Starting bot game loop...")
                        bot_instance = self.screen_manager.bot_instance
                        
                        # Manually initialize bot with initial game state if needed
                        # (Bot receives its own START_GAME over TCP so it will populate its own state)
                        print(f"[LOBBY] Bot game loop will be started.")
                        
                        # Use player_id 2 for bot (player is 1)
                        bot_player_id = getattr(bot_instance, 'player_id', None) or 2
                        self.bot_game_loop = BotGameLoop(
                            bot_player=bot_instance,
                            session_id=self.session_id,
                            player_id=bot_player_id,
                            local_player_id=bot_instance.local_player_id,
                            enemy_player_id=bot_instance.enemy_player_id,
                            difficulty="normal",
                            tick_rate_ms=500
                        )
                        if self.bot_game_loop.start():
                            self.bot_game_loop_started = True
                            self.screen_manager.bot_game_loop = self.bot_game_loop
                            print("[LOBBY] Bot game loop started successfully")
                        else:
                            print("[LOBBY] Failed to start bot game loop")

                    self.screen_manager.change_screen("GAME")

        else:
            # ======================= DEBUG MODE =======================
            self.textbox_nickname1.text = "Player1"
            self.textbox_nickname2.text = "Player2"

    def _spawn_local_server_and_connect(self):
        """Spawn a local Docker container for the server and connect both player and bot to it."""
        print("[LOBBY] Spawning local server container...")

        if not DOCKER_SDK_AVAILABLE:
            print("[LOBBY] Python docker SDK not available. Install 'docker' python package.")
            return

        image_name = "sharp-blaze-server:latest"
        container_name = "sharp_blaze_local_server"

        try:
            client = docker.from_env()
        except Exception as e:
            print(f"[LOBBY] Failed to create docker client: {e}")
            return

        try:
            # Ensure image exists (will raise if missing)
            try:
                client.images.get(image_name)
            except Exception:
                print(f"[LOBBY] Image {image_name} not found locally. Attempting to pull...")
                try:
                    client.images.pull(image_name)
                except Exception as e:
                    print(f"[LOBBY] Failed to pull image: {e}")
                    return

            # If a container with the same name exists, remove it first to avoid conflict
            existing = client.containers.list(all=True, filters={"name": container_name})
            for c in existing:
                try:
                    print(f"[LOBBY] Removing existing container {c.id} with name {container_name}")
                    c.remove(force=True)
                except Exception as e:
                    print(f"[LOBBY] Failed to remove existing container {c.id}: {e}")

            # Run container detached and publish ports
            ports = {
                f"{Config.TCP_PORT_SERVER}/tcp": Config.TCP_PORT_SERVER,
                f"{Config.GAME_SERVER_UDP_PORT}/udp": Config.GAME_SERVER_UDP_PORT,
            }

            container = client.containers.run(
                image_name,
                detach=True,
                name=container_name,
                ports=ports,
                remove=True,
            )

            print(f"[LOBBY] Docker container started: {container.id}")

            # Save container handle in screen manager for later cleanup
            self.screen_manager.local_server_container = container

            # Verify container is running and get logs if something is wrong
            try:
                container.reload()
                print(f"[LOBBY] Container status: {container.status}")
                if container.status != "running":
                    logs = container.logs(tail=20).decode('utf-8', errors='ignore')
                    print(f"[LOBBY] Warning: Container not running. Logs:\n{logs}")
            except Exception as e:
                print(f"[LOBBY] Failed to check container status: {e}")

            # Wait until server TCP port is accepting connections and responding (timeout 15s)
            import socket as _socket
            start = time.time()
            timeout = 15.0
            server_ready = False
            attempt = 0
            while time.time() - start < timeout:
                attempt += 1
                try:
                    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
                    s.settimeout(2.0)
                    result = s.connect_ex(("127.0.0.1", Config.TCP_PORT_SERVER))
                    if result == 0:
                        print(f"[LOBBY] Server TCP port ready on attempt {attempt}")
                        s.close()
                        server_ready = True
                        break
                    else:
                        s.close()
                except Exception as e:
                    print(f"[LOBBY] Readiness check attempt {attempt} failed: {e}")
                
                if not server_ready:
                    time.sleep(0.8)

            if not server_ready:
                print(f"[LOBBY] Error: server TCP port did not become ready after {timeout}s and {attempt} attempts")
                # Try to get container logs to diagnose the issue
                try:
                    container.reload()
                    logs = container.logs(tail=50).decode('utf-8', errors='ignore')
                    print(f"[LOBBY] Container logs for diagnosis:\n{logs}")
                    if container.status != "running":
                        print(f"[LOBBY] Container is not running! Status: {container.status}")
                except Exception as e:
                    print(f"[LOBBY] Could not retrieve container logs: {e}")
                # Continue anyway and let connections fail naturally
            else:
                print(f"[LOBBY] Server ready in {time.time() - start:.1f}s")

            # Build a synthetic match payload so NetworkManager can connect directly
            player_name = self.textbox_nickname1.text or "Player"
            bot_name = self.textbox_nickname2.text or "BOT"

            match_payload = {
                "ip": "127.0.0.1",
                "port": Config.TCP_PORT_SERVER,
                "udp_port": Config.GAME_SERVER_UDP_PORT,
                "session_id": 1,
                "token": "",
                "you": player_name,
                "opponent": bot_name,
                "global_player_id": 1,
            }

            # Initialize lobby screen match state from synthetic payload
            self.player_id = match_payload.get("global_player_id", 1)
            self.local_player_id = match_payload.get("you", player_name)
            self.enemy_player_id = match_payload.get("opponent", bot_name)
            self.session_id = match_payload.get("session_id", 1)

            # Connect player (network)
            print(f"[LOBBY] Connecting player '{player_name}' to local server...")
            self.screen_manager.network.connect_to_game_server(match_payload)

            # Set bot player ID to 2 (since player is 1)
            if self.screen_manager.bot_instance:
                bot = self.screen_manager.bot_instance
                bot.player_id = 2
                bot.player_slot = 2  # Critical: bot needs to know which team it is
                bot.local_player_id = bot_name  # Bot's own name
                bot.enemy_player_id = player_name  # Player's name is the enemy
                bot.session_id = self.session_id  # Link to the dedicated session

            # Wait a bit for player to connect before bot attempts
            time.sleep(0.8)

            # Connect bot in background thread
            def connect_bot():
                bot = self.screen_manager.bot_instance
                if bot:
                    # Ensure bot is configured to use the local server endpoint
                    bot.server_ip = "127.0.0.1"
                    bot.tcp_port_server = Config.TCP_PORT_SERVER
                    print(f"[LOBBY] Bot '{bot.bot_name}' connecting to local server at 127.0.0.1:{Config.TCP_PORT_SERVER}...")
                    if bot.connect():
                        print(f"[LOBBY] Bot connected successfully at {time.time()}")
                        # Wait for server to register bot in the session
                        print("[LOBBY] Waiting 2.0s for server to register bot in session...")
                        time.sleep(2.0)
                        print("[LOBBY] Sending START_GAME to server...")
                        try:
                            start_msg = JSON_Manager.get_startgame(session_id=1)
                            self.screen_manager.network.send_json(start_msg)
                        except Exception as e:
                            print(f"[LOBBY] Error sending START_GAME: {e}")
                    else:
                        print("[LOBBY] Bot failed to connect")

            t = threading.Thread(target=connect_bot, daemon=True)
            t.start()

        except Exception as e:
            print(f"[LOBBY] Exception while spawning local server: {e}")

    def draw(self):
        # SCREEN DRAW
        self.screen.fill((self.MAINDARK))

        # COMPONENTS DRAW
        self.btn_Start.draw(self.screen)

        self.textbox_nickname1.draw(self.screen)
        self.textbox_nickname2.draw(self.screen)

        # TEXT
        self.text_player1.draw(self.screen)
        self.text_player2.draw(self.screen)

        # EXIT BUTTON
        self.btn_close.draw(self.screen)
