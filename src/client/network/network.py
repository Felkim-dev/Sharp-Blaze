import socket
import json
import threading
import struct
import time

from utils.config import Config
from utils.json import JSON_Manager

class NetworkManager:
    """Class that manages all the connections"""

    def __init__(self):
        """INITIAL STATES"""

        self.current_rtt = 0
        self.rtt_ema = 0
        self.rtt_alpha = 0.3
        self._last_tcp_send_time = 0
        self.tcp_messages_sent = 0
        self.tcp_messages_received = 0

        self.udp_packets_received = 0
        self.udp_timeouts = 0
        self.udp_window_start = time.time()
        self.udp_window_packets = 0
        self.udp_rate = 0
        self.udp_loss_window = 0
        self.udp_loss_rate = 0

        self.cell_size = 50
        # -------------------- TCP INTIAL STATES -------------------
        self.client_tcp = None
        self.connected = False
        self.connection_status = "IDLE"
        self.receive_buffer = ""
        self.pending_messages = []
        self.current_player_name = None
        self.current_match = None
        self.tcp_port_server = None

        # ------------------- UDP INITIAL STATES -------------------
        self.client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_udp.settimeout(1.0)  # Timeout to allow clean thread shutdown
        self.client_udp.bind(("0.0.0.0",Config.UDP_PORT_CLIENT))
        self.udp_port_server = None
        self.server_ip = None
        self.udp_keepalive_active = False
        self.udp_keepalive_thread = None
        self.udp_hello_message = None
        self.udp_endpoint_registered = False

        self.latest_positions = {}  
        self.is_udp_listening = False

        # UDP Keep-Alive
        self.udp_session_id = None
        self.udp_player_id = None
        self.is_udp_keep_alive_running = False

        self.is_ping_running = False
        self._ping_start_time = 0

    # --------------------------- UDP Methods -------------------------------------
    def init_udp_connection(self,session_id,player_id):
        """It is called when the Lobby Start button is clicked"""
        # Use the endpoint from the broker match, fall back to config if not available
        if self.current_match:
            self.server_ip = self.current_match.get("ip", Config.SERVER_IP)
            self.udp_port_server = int(self.current_match.get("udp_port", 5556))
        else:
            self.server_ip = Config.SERVER_IP
            self.udp_port_server = Config.GAME_SERVER_UDP_PORT

        local_session_id = int(session_id)
        local_player_id = int(player_id)

        header = struct.pack("!ii", session_id,player_id)
        checksum = 0
        for b in header:
            checksum ^= b

        self._udp_hello_msg = header + struct.pack("!I", checksum)
        self._udp_hello_target = (self.server_ip, self.udp_port_server)
        self._udp_hello_confirmed = False

        print(f"Session_id {local_session_id}, player_id {local_player_id}, checksum {checksum}")
        print(f"Connecting to UDP server: {self.server_ip}:{self.udp_port_server}")
        print(f"UDP socket bound to: {self.client_udp.getsockname()}")

        try:
            # Store session and player IDs for keep-alive
            self.udp_session_id = session_id
            self.udp_player_id = player_id
            
            print("UDP Channel open. Waiting for positions")
            print("Starting UDP listener thread...")

            self.start_udp_thread()

            # Start keepalive early so the NAT mapping stays alive while we wait for the session.
            if self.udp_keepalive_thread is None or not self.udp_keepalive_thread.is_alive():
                self.udp_keepalive_active = True
                self.udp_keepalive_thread = threading.Thread(
                    target=self._udp_keepalive_loop,
                    daemon=True,
                )
                self.udp_keepalive_thread.start()

            max_retries = 20
            for attempt in range(max_retries):
                self.client_udp.sendto(self._udp_hello_msg,(self.server_ip,self.udp_port_server))
                print(f"UDP_HELLO sent(attempt: {attempt+1}) Waiting for positions...")
                time.sleep(0.1)
                
                # If we've received at least one valid UDP packet, assume the endpoint was registered.
                if self.udp_endpoint_registered:
                    print("UDP endpoint confirmed (received packet from server).")
                    break
        except Exception as e:
            print(f"Error at moment of UDP channel openning: {e}")

    def start_udp_thread(self):
        """Runs the secondary thread that hears the network"""
        if not self.is_udp_listening:
            self.is_udp_listening = True
            thread = threading.Thread(target=self._udp_listen_loop, daemon=True)
            thread.start()

    def start_udp_keep_alive(self):
        """Starts a thread that periodically sends UDP_HELLO to keep endpoint alive"""
        if not self.is_udp_keep_alive_running:
            self.is_udp_keep_alive_running = True
            thread = threading.Thread(target=self._udp_keep_alive_loop, daemon=True)
            thread.start()

    def start_ping_thread(self):
        if not self.is_ping_running:
            self.is_ping_running = True
            thread = threading.Thread(target=self._ping_loop, daemon=True)
            thread.start()

    def _ping_loop(self):
        # The server does not implement a PING message; avoid sending unsupported messages.
        # Keep this loop so that RTT bookkeeping remains compatible, but do not send unknown types.
        while self.is_ping_running:
            try:
                if self.connected and self.client_tcp:
                    
                    ping_msg = json.dumps({"type": "PING", "payload": {}}) + "\n"
                    self.client_tcp.send(ping_msg.encode("utf-8"))
                    self._ping_start_time = time.time()
                time.sleep(0.5)
            except Exception:
                break

    def _udp_keep_alive_loop(self):
        """Periodic UDP_HELLO rebroadcast to ensure server has our endpoint registered"""
        while self.is_udp_keep_alive_running:
            try:
                if self.udp_session_id is not None and self.udp_player_id is not None:
                    header = struct.pack("!ii", self.udp_session_id, self.udp_player_id)
                    checksum = 0
                    for b in header:
                        checksum ^= b
                    
                    welcome_message = header + struct.pack("!I", checksum)
                    self.client_udp.sendto(self._udp_hello_msg, self._udp_hello_target)
                    print("[UDP Keep-Alive] Resending UDP_HELLO to server")
                
                time.sleep(1)  # Reenviar cada 1 segundo
            except Exception as e:
                if self.is_udp_keep_alive_running:
                    print(f"[ERROR UDP Keep-Alive] {e}")
                break

    def _udp_keepalive_loop(self):
        """Periodically send udp_hello to keep NAT mapping alive"""
        print("[UDP] Keepalive thread started")
        keepalive_interval = 5
        while self.udp_keepalive_active:
            try:
                time.sleep(keepalive_interval)
                if not self.udp_keepalive_active:
                    break
                if self.udp_hello_message is None or self.server_ip is None or self.udp_port_server is None:
                    continue
                self.client_udp.sendto(self.udp_hello_message,(self.server_ip,self.udp_port_server))
                print(f"[UDP] Keepalive sent(session = {self.udp_session_id}, player = {self.udp_player_id})") 
            except Exception as e:
                print(f"[UDP] Keepalive error: {e}")
                break
        print("[UDP] Keepalive thread stopped")
    
    def _udp_listen_loop(self):
        """Bucle infinito del hilo secundario. Desempaqueta y guarda."""
        print(f"[UDP] Listener starting, listening on {self.client_udp.getsockname()}")
        last_hello_time = time.time()
        hello_retry_interval = 2.0  # Retry Hello every 2 seconds until confirmed
        packet_count = 0

        while self.is_udp_listening:
            try:
                # Este hilo se quedará esperando aquí hasta que llegue un paquete
                # Socket has a 1-second timeout so we periodically check is_udp_listening
                raw_data, origin_directions = self.client_udp.recvfrom(1024)
                packet_count += 1
                self.udp_packets_received += 1
                self.udp_window_packets += 1
                now = time.time()
                if now - self.udp_window_start >= 1.0:
                    self.udp_rate = min(100, self.udp_window_packets)
                    self.udp_loss_rate = min(100, self.udp_loss_window)
                    self.udp_window_packets = 0
                    self.udp_loss_window = 0
                    self.udp_window_start = now

                if len(raw_data) == 12:
                    entity_id, indx_x, indx_y = struct.unpack("<iff", raw_data)

                    # First position received = Hello was successful
                    if not self._udp_hello_confirmed:
                        self._udp_hello_confirmed = True
                        print("[UDP] Hello confirmed! Receiving positions.")

                    # Guardamos las coordenadas limpias en el buz�n
                    x,y =self.grid_to_world(indx_x,indx_y)

                    if entity_id not in self.latest_positions:
                        self.latest_positions[entity_id] = []

                    # Agregamos la nueva coordenada al final de su lista
                    self.latest_positions[entity_id].append((x, y))
                    self.udp_endpoint_registered = True

            except socket.timeout:
                self.udp_timeouts += 1
                self.udp_loss_window += 1
                now = time.time()
                if now - self.udp_window_start >= 1.0:
                    self.udp_rate = min(100, self.udp_window_packets)
                    self.udp_loss_rate = min(100, self.udp_loss_window)
                    self.udp_window_packets = 0
                    self.udp_loss_window = 0
                    self.udp_window_start = now
                if not self._udp_hello_confirmed and hasattr(self, '_udp_hello_msg'):
                    now = time.time()
                    if now - last_hello_time >= hello_retry_interval:
                        try:
                            bytes_sent = self.client_udp.sendto(self._udp_hello_msg, self._udp_hello_target)
                            last_hello_time = now
                            print(f"[UDP] Retrying Hello to {self._udp_hello_target} (no positions received yet, session={self.udp_session_id}, player={self.udp_player_id}, bytes_sent={bytes_sent})")
                        except Exception as e:
                            print(f"[UDP] Hello retry failed: {e}")
                continue
            except OSError:
                # Ocurre si cerramos el socket al desconectar
                break
            except Exception as e:
                print(f"[ERROR UDP Thread] {e}")
        print("[UDP] Listener thread exited cleanly.")

    def grid_to_world(self, grid_x, grid_y):
        """Convert the indexes the grid to world."""
        world_x = (grid_x * self.cell_size) + (self.cell_size // 2)
        world_y = (grid_y * self.cell_size) + (self.cell_size // 2)
        return world_x, world_y

    def get_latest_positions(self):
        """Pygame llama a esto para recuperar las colas y vaciar el buzón."""
        buzon_actual = self.latest_positions
        self.latest_positions = {}
        return buzon_actual

    def clear_entity_buffer(self, entity_id):
        """Elimina paquetes UDP retrasados de una ruta cancelada."""
        if entity_id in self.latest_positions:
            # Vaciamos la lista de puntos de esa unidad
            self.latest_positions[entity_id] = []

    # ------------------------------- TCP methods ------------------------------------------------------
    def connect(self, datos_iniciales):

        if isinstance(datos_iniciales, dict) and datos_iniciales.get("action") == "queue":
            self.connect_to_broker(datos_iniciales["player_id"])
            return

        raise ValueError("connect() now expects a broker queue payload")

    def connect_to_broker(self, player_name):

        if self.connection_status == "CONNECTING":
            return

        self.current_player_name = player_name
        self.connection_status = "CONNECTING"

        thread = threading.Thread(
            target=self.connection_thread,
            args=(Config.BROKER_IP, Config.BROKER_PORT, JSON_Manager.get_queue_request(player_name), False),
        )
        thread.daemon = True
        thread.start()

    def connect_to_game_server(self, match_payload):
        if self.connection_status == "CONNECTING":
            return

        self.current_match = match_payload
        self.server_ip = match_payload.get("ip", Config.SERVER_IP)
        self.tcp_port_server = int(match_payload.get("port", Config.TCP_PORT_SERVER))
        self.udp_port_server = int(match_payload.get("udp_port", Config.GAME_SERVER_UDP_PORT))

        self._close_tcp_socket()
        self.connection_status = "CONNECTING"

        player_id = self.current_player_name or match_payload.get("you") or match_payload.get("player_id")
        thread = threading.Thread(
            target=self.connection_thread,
            args=(
                self.server_ip,
                self.tcp_port_server,
                JSON_Manager.get_initial_connect(
                    player_id,
                    match_payload.get("session_id"),
                    match_payload.get("token"),
                    match_payload.get("global_player_id"),
                ),
                False,
            ),
        )
        thread.daemon = True
        thread.start()

    def connection_thread(self, ip, port, datos_iniciales, auto_start_game=False):
        self.client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.client_tcp.settimeout(3.0)
        try:
            self.client_tcp.connect((ip, port))

            mensaje = json.dumps(datos_iniciales) + "\n"
            self.client_tcp.send(mensaje.encode("utf-8"))

            if auto_start_game:
                start_message = json.dumps(JSON_Manager.get_startgame()) + "\n"
                self.client_tcp.send(start_message.encode("utf-8"))

            self.client_tcp.settimeout(None)
            self.client_tcp.setblocking(False)

            self.connected = True
            self.connection_status = "IDLE"
            self.start_ping_thread()

        except socket.timeout:
            print("Timeout.")
            self.connected = False
            self.connection_status = "ERROR"
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            self.connection_status = "ERROR"

    def _close_tcp_socket(self):
        if self.client_tcp is not None:
            try:
                self.client_tcp.close()
            except Exception as e:
                print(f"Error forcing the socket to close: {e}")

        self.client_tcp = None
        self.connected = False
        self.receive_buffer = ""
        self.pending_messages.clear()

    def send_json(self, data_dictionary):
        if self.connected:
            try:
                message = json.dumps(data_dictionary) + "\n"
                self.client_tcp.send(message.encode("utf-8"))
                self.tcp_messages_sent += 1
                self._last_tcp_send_time = time.time()
                print(f"Mensaje de salida TCP: {message}")
            except Exception as e:
                print(f"Error in: {e}")

    def _update_rtt(self):
        if self._ping_start_time > 0:
            rtt = (time.time() - self._ping_start_time) * 1000
            self._ping_start_time = 0
            if self.rtt_ema == 0:
                self.rtt_ema = rtt
            else:
                self.rtt_ema = self.rtt_alpha * rtt + (1 - self.rtt_alpha) * self.rtt_ema
            self.current_rtt = self.rtt_ema

    def receive_json(self):

        if self.pending_messages:
            self.tcp_messages_received += 1
            self._update_rtt()
            return self.pending_messages.pop(0)

        if self.connected:
            try:
                data = self.client_tcp.recv(4096).decode("utf-8")
                if not data:
                    print("[NETWORK] Servidor TCP cerró la conexión.")
                    self._close_tcp_socket()
                    return {"type": "DISCONNECTED"}
                if data:
                    self.receive_buffer += data
                    if "\n" in self.receive_buffer:
                        partes = self.receive_buffer.split("\n")
                        self.receive_buffer = partes.pop()

                        for json_packet in partes:
                            if json_packet.strip():
                                try:
                                    json_valido = json.loads(json_packet)
                                    if json_valido.get("type") == "OK":
                                        self._update_rtt()
                                        continue
                                    self.pending_messages.append(json_valido)
                                except json.JSONDecodeError as e:
                                    print(
                                        f"Error encountered while reading JSON: {json_packet} -> {e}"
                                    )

                        if self.pending_messages:
                            self.tcp_messages_received += 1
                            self._update_rtt()
                            return self.pending_messages.pop(0)
            except BlockingIOError:
                pass
            except Exception as e:
                print(f"Error to receive: {e}")
                self._close_tcp_socket()
                return {"type": "DISCONNECTED"}

        return None

    def disconnect(self):
        self.is_udp_listening = False
        self.udp_keepalive_active = False
        self.udp_endpoint_registered = False
        self.is_ping_running = False

        # Wait for the UDP keepalive thread to fully exit before touching the socket
        if self.udp_keepalive_thread is not None and self.udp_keepalive_thread.is_alive():
            self.udp_keepalive_thread.join(timeout=3.0)
            if self.udp_keepalive_thread.is_alive():
                print("[WARNING] UDP keepalive thread did not exit in time during disconnect")
        self.udp_keepalive_thread = None
        self.udp_session_id = None
        self.udp_player_id = None

        if self.client_udp is not None:
            try:
                self.client_udp.close()
            except Exception as e:
                print(f"Error cerrando el socket UDP: {e}")

        self.client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_udp.settimeout(1.0)  # Timeout for clean thread shutdown
        try:
            self.client_udp.bind(("0.0.0.0", Config.UDP_PORT_CLIENT))
        except Exception as e:
            print(f"Advertencia al re-bindear UDP: {e}")

        self._close_tcp_socket()

        # RESTARTING VARIBLES TO THE INITIAL STATE
        self.connection_status = "IDLE"
        self.current_player_name = None
        self.current_match = None

        # Estados UDP
        self.server_ip = None
        self.udp_port_server = None
        self.latest_positions.clear()
        self.current_rtt = 0
        self.rtt_ema = 0
        self._last_tcp_send_time = 0
        self._ping_start_time = 0
        self.udp_packets_received = 0
        self.udp_timeouts = 0
        self.udp_window_start = time.time()
        self.udp_window_packets = 0
        self.udp_rate = 0
        self.udp_loss_window = 0
        self.udp_loss_rate = 0
        self.tcp_messages_sent = 0
        self.tcp_messages_received = 0
        print("Disconnection complete and network restarted.")

    def calculate_rtt(self, sent_timestamp):
        """Called when the UDP thread receives a ping echo from the C++ server."""
        current_time = time.time()
        # Time difference in seconds * 1000 = milliseconds
        self.current_rtt = (current_time - sent_timestamp) * 1000
