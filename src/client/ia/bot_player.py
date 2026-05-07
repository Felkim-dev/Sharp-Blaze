import socket
import json
import threading
import time
import struct

from utils.config import Config


class BotPlayer:
    """TCP connection handler for the bot player (similar to NetworkManager but simplified)"""

    def __init__(self, bot_name: str, server_ip: str = None, tcp_port: int = None):
        """Initialize bot player connection parameters
        
        Args:
            bot_name (str): Name to identify the bot (e.g., "SharpBlaze_Bot_1")
            server_ip (str): Override default server IP (defaults to Config.SERVER_IP)
            tcp_port (int): Override default TCP port (defaults to Config.TCP_PORT_SERVER)
        """
        self.bot_name = bot_name
        self.server_ip = server_ip if server_ip is not None else Config.SERVER_IP
        self.tcp_port_server = tcp_port if tcp_port is not None else Config.TCP_PORT_SERVER
        
        # Connection state
        self.client_tcp = None
        self.connected = False
        self.connection_status = "IDLE"
        
        # Message handling
        self.receive_buffer = ""
        self.pending_messages = []
        self.receive_lock = threading.Lock()
        
        # Game state
        self.session_id = None
        self.player_id = None
        self.player_slot = None
        self.local_player_id = None
        self.enemy_player_id = None
        
        # Bot state
        self.gold = 0
        self.own_units = {}  # {entity_id: {"type": "Collector"/"Attacker", "x": x, "y": y, "hp": hp}}
        self.enemy_units = {}  # {entity_id: {"type": "...", "x": x, "y": y}}
        self.structures = {}  # {entity_id: {"x": x, "y": y}}
        self.enemy_base_cell = (94, 6)
        self.shop_cell = (50, 50)
        self.resource_cells = [(70, 70), (42, 58), (58, 42), (30, 30)]
        self.shop_authorized = False
        self.shop_id = -1
        self.authorized_unit_id = -1
        self.blacklisted_attackers = set()
        
        # Thread control
        self._listening = False
        self._listen_thread = None

    def connect(self) -> bool:
        """Establish TCP connection to server as a bot player
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.connection_status == "CONNECTING":
            return False
        
        self.connection_status = "CONNECTING"
        self._listen_thread = threading.Thread(
            target=self._connection_thread, 
            daemon=True
        )
        self._listen_thread.start()
        
        # Wait for connection to establish (max 12 seconds, more time for local server startup)
        max_attempts = 120  # 120 * 0.1s = 12s
        for attempt in range(max_attempts):
            if self.connected:
                print(f"[BOT] {self.bot_name} connected to server after {attempt * 0.1:.1f}s")
                return True
            time.sleep(0.1)
        
        print(f"[BOT] {self.bot_name} connection timeout")
        self.connection_status = "ERROR"
        return False

    def _connection_thread(self):
        """Background thread to handle TCP connection and reception"""
        try:
            self.client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_tcp.settimeout(3.0)
            self.client_tcp.connect((self.server_ip, self.tcp_port_server))
            
            # Send initial connection message (matching client protocol)
            initial_message = {
                "type": "INITIAL_CONNECT",
                "payload": {
                    "player_id": self.bot_name,
                    "client_version": "0.0.1",
                    "is_ready": True
                }
            }
            if self.session_id is not None:
                initial_message["payload"]["session_id"] = self.session_id
                
            message = json.dumps(initial_message) + "\n"
            self.client_tcp.send(message.encode("utf-8"))
            
            self.client_tcp.settimeout(None)
            self.client_tcp.setblocking(False)
            
            self.connected = True
            self.connection_status = "IDLE"
            self._listening = True
            
            # Start listening loop
            self._listen_loop()
            
        except socket.timeout:
            print(f"[BOT] {self.bot_name} connection timeout")
            self.connected = False
            self.connection_status = "ERROR"
        except Exception as e:
            print(f"[BOT] {self.bot_name} connection error: {e}")
            self.connected = False
            self.connection_status = "ERROR"

    def _listen_loop(self):
        """Continuous loop to receive messages from server"""
        while self._listening and self.connected:
            try:
                data = self.client_tcp.recv(4096).decode("utf-8")
                
                if data:
                    with self.receive_lock:
                        self.receive_buffer += data
                        
                        # Split by newline and process complete JSON packets
                        if "\n" in self.receive_buffer:
                            parts = self.receive_buffer.split("\n")
                            self.receive_buffer = parts[-1]  # Keep incomplete part
                            
                            for json_packet in parts[:-1]:
                                if json_packet.strip():
                                    try:
                                        parsed = json.loads(json_packet)
                                        self.pending_messages.append(parsed)
                                        self._process_game_state(parsed)
                                    except json.JSONDecodeError as e:
                                        print(f"[BOT] JSON decode error: {e}")
                else:
                    self.connected = False
                    break
                    
            except BlockingIOError:
                time.sleep(0.01)
            except Exception as e:
                print(f"[BOT] Listen loop error: {e}")
                self.connected = False
                break

    def _process_game_state(self, message: dict):
        """Update bot's understanding of game state based on received message
        
        Args:
            message (dict): JSON message from server
        """
        msg_type = message.get("type", "")
        
        if msg_type == "MATCH_FOUND":
            payload = message.get("payload", {})
            self.session_id = payload.get("session_id")
            self.player_id = payload.get("global_player_id")
            if self.player_id in (1, 2):
                self.player_slot = self.player_id
            self.local_player_id = payload.get("you")
            self.enemy_player_id = payload.get("opponent")
            print(f"[BOT] Match found - Session: {self.session_id}, Player: {self.player_id}")
        
        elif msg_type == "START_GAME":
            payload = message.get("payload", {})
            self.gold = payload.get("gold", 500)
            self.enemy_base_cell = (94, 6) if self.player_slot != 2 else (6, 94)
            self.shop_authorized = False
            self.shop_id = -1
            self.authorized_unit_id = -1
            
            # Parse initial units
            units = payload.get("units", {})
            print(f"[BOT DEBUG] START_GAME raw units payload: {units}")
            self.own_units.clear()
            self.enemy_units.clear()
            for unit_id_str, pos in units.items():
                unit_id = int(unit_id_str)
                if self._owns_entity(unit_id):
                    self.own_units[unit_id] = {
                        "type": self._infer_unit_type(unit_id),
                        "x": pos[0] * 50,  # Grid to world
                        "y": pos[1] * 50,
                        "hp": 100  # Default, will be updated
                    }
                elif self._is_player_entity(unit_id):
                    self.enemy_units[unit_id] = {
                        "type": self._infer_unit_type(unit_id),
                        "x": pos[0] * 50,
                        "y": pos[1] * 50,
                        "hp": 100
                    }
            
            structures = payload.get("structures", {})
            self.structures.clear()
            for struct_id_str, pos in structures.items():
                struct_id = int(struct_id_str)
                if self._owns_entity(struct_id):
                    self.structures[struct_id] = {"x": pos[0] * 50, "y": pos[1] * 50}
                elif self._is_player_entity(struct_id):
                    self.enemy_units[struct_id] = {
                        "type": self._infer_unit_type(struct_id),
                        "x": pos[0] * 50,
                        "y": pos[1] * 50,
                        "hp": 1500
                    }
            print(f"[BOT] START_GAME parsed: own={len(self.own_units)} enemy={len(self.enemy_units)}")

        elif msg_type == "SHOP_AUTHORIZATION":
            payload = message.get("payload", {})
            self.shop_authorized = bool(payload.get("authorized", False))
            self.shop_id = int(payload.get("shop_id", -1))
            self.authorized_unit_id = int(payload.get("unit_id", -1))
            print(
                f"[BOT] SHOP_AUTHORIZATION authorized={self.shop_authorized} "
                f"shop_id={self.shop_id} unit_id={self.authorized_unit_id}"
            )
        
        elif msg_type == "RESOURCES":
            payload = message.get("payload", {})
            old_gold = self.gold
            self.gold = payload.get("new_balance", self.gold)
            delta = self.gold - old_gold
            sign = "+" if delta >= 0 else ""
            print(f"[BOT-GOLD] {old_gold} → {self.gold} ({sign}{delta})")
        
        elif msg_type == "UNIT_SPAWNED":
            payload = message.get("payload", {})
            unit_id = payload.get("unit_id")
            owner = payload.get("owner_player")
            unit_type = payload.get("unit_type")
            
            if owner == self.player_id:
                self.own_units[unit_id] = {
                    "type": self._parse_unit_type(unit_type),
                    "x": 75,
                    "y": 75,
                    "hp": 100
                }
            else:
                self.enemy_units[unit_id] = {
                    "type": self._parse_unit_type(unit_type),
                    "x": 75,
                    "y": 75,
                    "hp": 100
                }
        
        elif msg_type == "UNIT_DAMAGED":
            payload = message.get("payload", {})
            target_id = payload.get("target_entity_id")
            current_hp = payload.get("current_hp")
            
            # Determine if it's our unit or enemy
            if target_id in self.own_units:
                self.own_units[target_id]["hp"] = current_hp
                if current_hp <= 0:
                    del self.own_units[target_id]
                    self.blacklisted_attackers.add(target_id)
            elif target_id in self.enemy_units:
                self.enemy_units[target_id]["hp"] = current_hp
                if current_hp <= 0:
                    del self.enemy_units[target_id]

        elif msg_type == "ATTACK_RESULT":
            status = message.get("status", "")
            payload = message.get("payload", {})
            attacker_id = int(payload.get("attacker_id", -1))
            target_id = int(payload.get("target_id", -1))
            reason = payload.get("reason", "")

            if status == "rejected":
                if reason in {
                    "attacker_not_found",
                    "attacker_dead_or_missing",
                    "invalid_attacker_owner_or_type",
                    "invalid_attacker_id_value",
                }:
                    self.blacklisted_attackers.add(attacker_id)
                    if attacker_id in self.own_units:
                        del self.own_units[attacker_id]

                if reason in {"target_not_found", "target_dead_or_missing"}:
                    if target_id in self.enemy_units:
                        del self.enemy_units[target_id]
        
        elif msg_type == "ENTITY_DESTROYED":
            payload = message.get("payload", {})
            entity_id = payload.get("entity_id")
            
            if entity_id in self.own_units:
                del self.own_units[entity_id]
                self.blacklisted_attackers.add(entity_id)
            elif entity_id in self.enemy_units:
                del self.enemy_units[entity_id]

    def _owns_entity(self, entity_id: int) -> bool:
        """Check if entity belongs to the bot (player 1 ranges)
        
        Args:
            entity_id (int): Entity ID to check
            
        Returns:
            bool: True if bot owns the entity
        """
        if self.player_slot == 2:
            return 5000 <= entity_id <= 9999
        return 0 <= entity_id <= 4999

    def _is_player_entity(self, entity_id: int) -> bool:
        return (0 <= entity_id <= 9999)

    def _infer_unit_type(self, entity_id: int) -> str:
        """Infer unit type from entity ID
        
        Args:
            entity_id (int): Entity ID
            
        Returns:
            str: "Collector", "Attacker", or "Structure"
        """
        # Based on server GameTypes.h ranges
        if (1000 <= entity_id <= 2999) or (6000 <= entity_id <= 7999):
            return "Attacker"
        elif (3000 <= entity_id <= 4999) or (8000 <= entity_id <= 9999):
            return "Collector"
        elif (0 <= entity_id <= 999) or (5000 <= entity_id <= 5999):
            return "Structure"
        elif 10000 <= entity_id <= 10999:
            return "ResourceMine"
        elif 11000 <= entity_id <= 11999:
            return "Shop"
        else:
            return "Unknown"

    def _parse_unit_type(self, unit_type: int) -> str:
        """Parse unit type from server integer
        
        Args:
            unit_type (int): Unit type value from server
            
        Returns:
            str: Unit type name
        """
        # EntityType enum: Structure=0, Attacker=1, Collector=2, ResourceMine=3, Shop=4, Unknown=5
        type_map = {0: "Structure", 1: "Attacker", 2: "Collector", 3: "ResourceMine", 4: "Shop"}
        return type_map.get(unit_type, "Unknown")

    def send_buy_unit(self, unit_type: str, quantity: int = 1) -> bool:
        """Send a buy unit command to the server
        
        Args:
            unit_type (str): "Collector" or "Attacker"
            quantity (int): Number of units to buy
            
        Returns:
            bool: True if sent successfully
        """
        if not self.connected:
            return False
        
        message = {
            "type": "BUY_UNIT",
            "payload": {
                "unit_type": unit_type,
                "quantity": quantity
            }
        }
        return self.send_json(message)

    def send_move_unit(self, unit_id: int, target_x: int, target_y: int) -> bool:
        """Send a move unit command
        
        Args:
            unit_id (int): Unit to move
            target_x (int): Target X cell (0-99)
            target_y (int): Target Y cell (0-99)
            
        Returns:
            bool: True if sent successfully
        """
        if not self.connected:
            return False

        target_x = max(0, min(99, int(target_x)))
        target_y = max(0, min(99, int(target_y)))
        
        message = {
            "type": "MOVE_ORDER",
            "payload": {
                "unit_id": unit_id,
                "target_x": target_x,
                "target_y": target_y
            }
        }
        return self.send_json(message)

    def send_attack(self, attacker_id: int, target_id: int) -> bool:
        """Send an attack command
        
        Args:
            attacker_id (int): Unit to attack with
            target_id (int): Target unit ID
            
        Returns:
            bool: True if sent successfully
        """
        if not self.connected:
            return False
        
        message = {
            "type": "ATTACK",
            "payload": {
                "attacker_id": attacker_id,
                "target_id": target_id
            }
        }
        return self.send_json(message)

    def send_ready(self) -> bool:
        """Send ready signal to start the game
        
        Returns:
            bool: True if sent successfully
        """
        if not self.connected:
            return False
        
        message = {
            "type": "READY",
            "payload": {
                "session_id": self.session_id
            }
        }
        return self.send_json(message)

    def send_json(self, data: dict) -> bool:
        """Send a JSON message to the server
        
        Args:
            data (dict): Message to send
            
        Returns:
            bool: True if sent successfully
        """
        if not self.connected or not self.client_tcp:
            return False
        
        try:
            message = json.dumps(data) + "\n"
            self.client_tcp.send(message.encode("utf-8"))
            print(f"[BOT] {self.bot_name} sent: {data.get('type', 'UNKNOWN')}")
            return True
        except Exception as e:
            print(f"[BOT] {self.bot_name} send error: {e}")
            self.connected = False
            return False

    def receive_json(self) -> dict:
        """Receive a JSON message from server
        
        Returns:
            dict: Message or None if no message available
        """
        with self.receive_lock:
            if self.pending_messages:
                return self.pending_messages.pop(0)
        return None

    def disconnect(self):
        """Close connection and cleanup resources"""
        self._listening = False
        self.connected = False
        
        if self.client_tcp:
            try:
                self.client_tcp.close()
            except Exception as e:
                print(f"[BOT] Error closing socket: {e}")
            finally:
                self.client_tcp = None
        
        print(f"[BOT] {self.bot_name} disconnected")

    def get_state(self) -> dict:
        """Get current game state
        
        Returns:
            dict: Current state snapshot
        """
        return {
            "gold": self.gold,
            "own_units": self.own_units.copy(),
            "enemy_units": self.enemy_units.copy(),
            "structures": self.structures.copy(),
            "enemy_base_cell": self.enemy_base_cell,
            "shop_cell": self.shop_cell,
            "resource_cells": list(self.resource_cells),
            "shop_authorized": self.shop_authorized,
            "shop_id": self.shop_id,
            "authorized_unit_id": self.authorized_unit_id,
            "blacklisted_attackers": list(self.blacklisted_attackers),
            "connected": self.connected
        }
