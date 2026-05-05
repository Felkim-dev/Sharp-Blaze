"""
BotNetworkClient — Headless network client for the Bot AI.

Replicates the exact same TCP + UDP protocol used by the human player's
NetworkManager (src/client/network/network.py), but with zero Pygame
dependency.  This allows the bot to act as a second client connecting
to the same Game Server container.

Protocol summary
────────────────
TCP (port 5555 by default):
  → Client sends newline-delimited JSON commands:
      INITIAL_CONNECT, START_GAME, BUY_UNIT, MOVE_ORDER, ATTACK
  ← Server replies with newline-delimited JSON:
      START_GAME, BUY_UNIT_RESULT, UNIT_SPAWNED, RESOURCES,
      UNIT_DAMAGED, ENTITY_DESTROYED, GAME_OVER, DISCONNECTED

UDP (port 5556 by default):
  → Client sends a 12-byte hello: pack("!ii", session_id, player_id) + pack("!I", checksum)
  ← Server sends 12-byte position packets: pack("<iff", entity_id, grid_x, grid_y)
     The client converts grid coordinates to world pixels using cell_size=50.
"""

import socket
import json
import struct
import threading
import time
from typing import Optional, Dict, Any, List


class BotNetworkClient:
    """
    Lightweight TCP + UDP client for the bot AI.

    Lifecycle
    ---------
    1. connect_tcp(ip, port, player_id, session_id, token)
       → opens TCP, sends INITIAL_CONNECT
    2. init_udp(ip, udp_port, session_id, player_id)
       → opens UDP listener + keepalive
    3. send_json(data)  — send commands to the game server (TCP)
    4. receive_json()   — poll for TCP responses (non-blocking)
    5. get_latest_positions() — consume buffered UDP positions
    6. disconnect()     — clean shutdown
    """

    # ────────────────────────────────────────────────────────────
    #  INITIALIZATION
    # ────────────────────────────────────────────────────────────

    def __init__(self):
        """Initialize all state variables to their defaults."""

        # ── TCP state ──
        self.client_tcp: Optional[socket.socket] = None
        self.connected: bool = False
        self.connection_status: str = "IDLE"  # IDLE | CONNECTING | ERROR
        self.receive_buffer: str = ""
        self.pending_messages: List[Dict[str, Any]] = []

        # ── UDP state ──
        # Bind to port 0 → OS picks a free ephemeral port.
        # This avoids colliding with the human player's UDP socket.
        self.client_udp: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_udp.settimeout(1.0)  # Timeout so recvfrom() doesn't block forever
        self.client_udp.bind(("0.0.0.0", 0))

        self.server_ip: Optional[str] = None
        self.udp_port_server: Optional[int] = None
        self.udp_hello_message: Optional[bytes] = None
        self.udp_session_id: Optional[int] = None
        self.udp_player_id: Optional[int] = None
        self.udp_endpoint_registered: bool = False
        self.udp_keepalive_active: bool = False
        self.udp_keepalive_thread: Optional[threading.Thread] = None

        self.latest_positions: Dict[int, List[tuple]] = {}
        self.is_udp_listening: bool = False

        # ── Grid constants (must match server & human client) ──
        self.cell_size: int = 50

    # ────────────────────────────────────────────────────────────
    #  TCP — Connection
    # ────────────────────────────────────────────────────────────

    def connect_tcp(self, ip: str, port: int, player_id: str,
                    session_id: int, token: str, timeout: float = 5.0) -> bool:
        """
        Connect to the Game Server via TCP and send INITIAL_CONNECT.

        This is the bot equivalent of:
            NetworkManager.connect_to_game_server(match_payload)

        Args:
            ip:         Server IP (e.g. "127.0.0.1")
            port:       Server TCP port (e.g. 5555 or Docker-mapped port)
            player_id:  Bot's player name (e.g. "bot_ai")
            session_id: Session ID from the spawner
            token:      Auth token from the spawner
            timeout:    Seconds to wait for the connection

        Returns:
            True if connection succeeded, False otherwise.
        """
        if self.connection_status == "CONNECTING":
            return False

        self.server_ip = ip
        self.connection_status = "CONNECTING"

        # Build INITIAL_CONNECT payload
        # (same format as JSON_Manager.get_initial_connect)
        initial_connect = {
            "type": "INITIAL_CONNECT",
            "payload": {
                "player_id": player_id,
                "client_version": "0.0.1",
                "is_ready": True,
                "session_id": session_id,
                "match_token": token,
            },
        }

        # Create TCP socket
        self.client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_tcp.settimeout(timeout)

        try:
            self.client_tcp.connect((ip, port))

            # Send INITIAL_CONNECT (newline-delimited JSON)
            message = json.dumps(initial_connect) + "\n"
            self.client_tcp.send(message.encode("utf-8"))

            # Switch to non-blocking for subsequent recv() calls
            self.client_tcp.settimeout(None)
            self.client_tcp.setblocking(False)

            self.connected = True
            self.connection_status = "IDLE"
            print(f"[BotNet] TCP connected to {ip}:{port} as '{player_id}'")
            return True

        except socket.timeout:
            print(f"[BotNet] TCP connection timeout to {ip}:{port}")
            self.connected = False
            self.connection_status = "ERROR"
            return False

        except Exception as e:
            print(f"[BotNet] TCP connection error: {e}")
            self.connected = False
            self.connection_status = "ERROR"
            return False

    # ────────────────────────────────────────────────────────────
    #  TCP — Send
    # ────────────────────────────────────────────────────────────

    def send_json(self, data_dictionary: Dict[str, Any]) -> None:
        """
        Send a JSON command to the Game Server over TCP.

        The protocol is newline-delimited JSON, identical to
        NetworkManager.send_json().

        Args:
            data_dictionary: Command dict (e.g. BUY_UNIT, MOVE_ORDER, ATTACK)
        """
        if not self.connected:
            return

        try:
            message = json.dumps(data_dictionary) + "\n"
            self.client_tcp.send(message.encode("utf-8"))
            print(f"[BotNet] TCP out: {message.strip()}")
        except Exception as e:
            print(f"[BotNet] TCP send error: {e}")

    # ────────────────────────────────────────────────────────────
    #  TCP — Receive
    # ────────────────────────────────────────────────────────────

    def receive_json(self) -> Optional[Dict[str, Any]]:
        """
        Poll for a single TCP message from the Game Server (non-blocking).

        Uses the same buffer + newline-split strategy as
        NetworkManager.receive_json().

        Returns:
            A parsed JSON dict, or None if nothing is available.
            Returns {"type": "DISCONNECTED"} if the server closed the connection.
        """
        # Return queued messages first
        if self.pending_messages:
            return self.pending_messages.pop(0)

        if not self.connected:
            return None

        try:
            data = self.client_tcp.recv(4096).decode("utf-8")

            if not data:
                # Server closed the connection gracefully
                print("[BotNet] Server closed TCP connection.")
                self._close_tcp_socket()
                return {"type": "DISCONNECTED"}

            # Accumulate into buffer and split by newline
            self.receive_buffer += data

            if "\n" in self.receive_buffer:
                parts = self.receive_buffer.split("\n")
                # Last element is the incomplete tail (may be empty)
                self.receive_buffer = parts.pop()

                for json_packet in parts:
                    if json_packet.strip():
                        try:
                            parsed = json.loads(json_packet)
                            self.pending_messages.append(parsed)
                        except json.JSONDecodeError as e:
                            print(f"[BotNet] Bad JSON: {json_packet} -> {e}")

                if self.pending_messages:
                    return self.pending_messages.pop(0)

        except BlockingIOError:
            # No data available right now (non-blocking socket)
            pass

        except Exception as e:
            print(f"[BotNet] TCP recv error: {e}")
            self._close_tcp_socket()
            return {"type": "DISCONNECTED"}

        return None

    # ────────────────────────────────────────────────────────────
    #  UDP — Initialization
    # ────────────────────────────────────────────────────────────

    def init_udp(self, ip: str, udp_port: int,
                 session_id: int, player_id: int) -> None:
        """
        Initialize UDP channel to receive unit position updates.

        Sends the same 12-byte hello message as the human client:
            header  = struct.pack("!ii", session_id, player_id)  — 8 bytes
            checksum = XOR of all bytes in header                — 4 bytes (pack "!I")
            hello   = header + checksum

        Then starts a listener thread and a keepalive thread.

        Args:
            ip:         Server IP
            udp_port:   Server UDP port
            session_id: Session ID (int)
            player_id:  Player ID (1 or 2)
        """
        self.server_ip = ip
        self.udp_port_server = udp_port
        self.udp_session_id = session_id
        self.udp_player_id = player_id

        # Build hello message — same binary format as NetworkManager
        header = struct.pack("!ii", session_id, player_id)
        checksum = 0
        for b in header:
            checksum ^= b
        hello_message = header + struct.pack("!I", checksum)
        self.udp_hello_message = hello_message

        self.udp_keepalive_active = True
        self.udp_endpoint_registered = False

        print(f"[BotNet] UDP init: session={session_id}, player={player_id}, "
              f"checksum={checksum}, target={ip}:{udp_port}")

        try:
            # Start listener thread
            self._start_udp_listener()

            # Start keepalive thread
            if self.udp_keepalive_thread is None or not self.udp_keepalive_thread.is_alive():
                self.udp_keepalive_active = True
                self.udp_keepalive_thread = threading.Thread(
                    target=self._udp_keepalive_loop,
                    daemon=True,
                )
                self.udp_keepalive_thread.start()

            # Send hello with retries until server acknowledges
            max_retries = 20
            for attempt in range(max_retries):
                self.client_udp.sendto(hello_message, (ip, udp_port))
                print(f"[BotNet] UDP_HELLO sent (attempt {attempt + 1})")
                time.sleep(0.1)

                if self.udp_endpoint_registered:
                    print("[BotNet] UDP endpoint confirmed (received packet from server).")
                    break

        except Exception as e:
            print(f"[BotNet] UDP init error: {e}")

    # ────────────────────────────────────────────────────────────
    #  UDP — Listener Thread
    # ────────────────────────────────────────────────────────────

    def _start_udp_listener(self) -> None:
        """Start the background thread that receives UDP position packets."""
        if not self.is_udp_listening:
            self.is_udp_listening = True
            thread = threading.Thread(target=self._udp_listen_loop, daemon=True)
            thread.start()

    def _udp_listen_loop(self) -> None:
        """
        Infinite loop that unpacks 12-byte UDP position packets.

        Packet format (from server):
            struct.pack("<iff", entity_id, grid_x, grid_y)
            - entity_id: int32  (unit/structure ID)
            - grid_x:    float  (grid column index)
            - grid_y:    float  (grid row index)

        Grid coordinates are converted to world pixels using:
            world_x = (grid_x * cell_size) + (cell_size // 2)
            world_y = (grid_y * cell_size) + (cell_size // 2)
        """
        last_hello_time = time.time()
        hello_retry_interval = 2.0  # Retry Hello every 2s until confirmed

        while self.is_udp_listening:
            try:
                raw_data, addr = self.client_udp.recvfrom(1024)

                if len(raw_data) == 12:
                    entity_id, grid_x, grid_y = struct.unpack("<iff", raw_data)

                    # Convert grid indexes to world pixel coordinates
                    world_x, world_y = self._grid_to_world(grid_x, grid_y)

                    if entity_id not in self.latest_positions:
                        self.latest_positions[entity_id] = []

                    self.latest_positions[entity_id].append((world_x, world_y))

                    if not self.udp_endpoint_registered:
                        self.udp_endpoint_registered = True
                        print("[BotNet] UDP endpoint confirmed (received packet from server).")

            except socket.timeout:
                # Retry hello if we haven't gotten any position data yet
                if not self.udp_endpoint_registered and self.udp_hello_message is not None:
                    now = time.time()
                    if now - last_hello_time >= hello_retry_interval:
                        try:
                            self.client_udp.sendto(
                                self.udp_hello_message,
                                (self.server_ip, self.udp_port_server)
                            )
                            last_hello_time = now
                            print("[BotNet] UDP retrying Hello (no positions received yet)")
                        except Exception as e:
                            print(f"[BotNet] UDP hello retry failed: {e}")
                continue
            except OSError:
                # Socket was closed (during disconnect)
                break
            except Exception as e:
                print(f"[BotNet] UDP recv error: {e}")

        print("[BotNet] UDP listener thread exited cleanly.")

    # ────────────────────────────────────────────────────────────
    #  UDP — Keepalive Thread
    # ────────────────────────────────────────────────────────────

    def _udp_keepalive_loop(self) -> None:
        """
        Periodically send the hello message to keep the NAT mapping alive.

        Identical behavior to NetworkManager._udp_keepalive_loop().
        Interval: 5 seconds.
        """
        print("[BotNet] UDP keepalive thread started")
        keepalive_interval = 5

        while self.udp_keepalive_active:
            try:
                time.sleep(keepalive_interval)

                if not self.udp_keepalive_active:
                    break

                if (self.udp_hello_message is None or
                        self.server_ip is None or
                        self.udp_port_server is None):
                    continue

                self.client_udp.sendto(
                    self.udp_hello_message,
                    (self.server_ip, self.udp_port_server),
                )
                print(f"[BotNet] UDP keepalive sent "
                      f"(session={self.udp_session_id}, player={self.udp_player_id})")

            except Exception as e:
                print(f"[BotNet] UDP keepalive error: {e}")
                break

        print("[BotNet] UDP keepalive thread stopped")

    # ────────────────────────────────────────────────────────────
    #  UDP — Position Retrieval
    # ────────────────────────────────────────────────────────────

    def get_latest_positions(self) -> Dict[int, List[tuple]]:
        """
        Consume and return all buffered UDP position updates.

        Returns a dict mapping entity_id -> list of (world_x, world_y) tuples.
        The internal buffer is cleared after each call (same as
        NetworkManager.get_latest_positions()).
        """
        current_buffer = self.latest_positions
        self.latest_positions = {}
        return current_buffer

    def clear_entity_buffer(self, entity_id: int) -> None:
        """Remove queued UDP positions for a specific entity (e.g. dead unit)."""
        if entity_id in self.latest_positions:
            self.latest_positions[entity_id] = []

    # ────────────────────────────────────────────────────────────
    #  COORDINATE HELPERS
    # ────────────────────────────────────────────────────────────

    def _grid_to_world(self, grid_x: float, grid_y: float) -> tuple:
        """
        Convert grid indexes to world pixel coordinates.

        Matches NetworkManager.grid_to_world() and GameWorld.grid_to_world().
        """
        world_x = (grid_x * self.cell_size) + (self.cell_size // 2)
        world_y = (grid_y * self.cell_size) + (self.cell_size // 2)
        return world_x, world_y

    # ────────────────────────────────────────────────────────────
    #  DISCONNECT / CLEANUP
    # ────────────────────────────────────────────────────────────

    def disconnect(self) -> None:
        """
        Clean shutdown of both TCP and UDP connections.

        Stops listener/keepalive threads, closes sockets, and resets state.
        """
        print("[BotNet] Disconnecting...")

        # ── Stop UDP threads ──
        self.is_udp_listening = False
        self.udp_keepalive_active = False
        self.udp_endpoint_registered = False

        if self.client_udp is not None:
            try:
                self.client_udp.close()
            except Exception as e:
                print(f"[BotNet] Error closing UDP socket: {e}")

        # Re-create UDP socket for potential reuse
        self.client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.client_udp.bind(("0.0.0.0", 0))
        except Exception as e:
            print(f"[BotNet] Warning re-binding UDP: {e}")

        # ── Close TCP ──
        self._close_tcp_socket()

        # ── Reset state ──
        self.connection_status = "IDLE"
        self.server_ip = None
        self.udp_port_server = None
        self.latest_positions.clear()
        self.udp_hello_message = None
        self.udp_session_id = None
        self.udp_player_id = None

        print("[BotNet] Disconnect complete.")

    def _close_tcp_socket(self) -> None:
        """Close the TCP socket and reset TCP-related state."""
        if self.client_tcp is not None:
            try:
                self.client_tcp.close()
            except Exception as e:
                print(f"[BotNet] Error closing TCP socket: {e}")

        self.client_tcp = None
        self.connected = False
        self.receive_buffer = ""
        self.pending_messages.clear()