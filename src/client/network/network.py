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
        self.client_udp.bind(("0.0.0.0",Config.UDP_PORT_CLIENT))
        self.udp_port_server = None
        self.server_ip = None

        self.latest_positions = {}  
        self.is_udp_listening = False

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

        welcome_message = header + struct.pack("!I", checksum)

        print(f"Session_id {local_session_id}, player_id {local_player_id}, checksum {checksum}")
        print(f"Connecting to UDP server: {self.server_ip}:{self.udp_port_server}")
        try:
            max_retries = 20
            for attempt in range(max_retries):
                self.client_udp.sendto(welcome_message,(self.server_ip,self.udp_port_server))
                print(f"UDP_HELLO sent(attempt: {attempt+1}) Waiting for positions...")
                time.sleep(0.1)
                
                # If we've received at least one position, assume endpoint was registered
                if self.latest_positions:
                    print("UDP endpoint confirmed (received positions).")
                    break

            self.start_udp_thread()
        except Exception as e:
            print(f"Error at moment of UDP channel openning: {e}")

    def start_udp_thread(self):
        """Runs the secondary thread that hears the network"""
        if not self.is_udp_listening:
            self.is_udp_listening = True
            thread = threading.Thread(target=self._udp_listen_loop, daemon=True)
            thread.start()

    def _udp_listen_loop(self):
        """Bucle infinito del hilo secundario. Desempaqueta y guarda."""
        while self.is_udp_listening:
            try:
                # Este hilo se quedará esperando aquí hasta que llegue un paquete
                raw_data, origin_directions = self.client_udp.recvfrom(1024)

                # Asumiendo tu paquete de 12 bytes (<iff)
                if len(raw_data) == 12:
                    entity_id, indx_x, indx_y = struct.unpack("<iff", raw_data)
                    # Guardamos las coordenadas limpias en el buzón

                    x,y =self.grid_to_world(indx_x,indx_y)

                    if entity_id not in self.latest_positions:
                        self.latest_positions[entity_id] = []

                    # Agregamos la nueva coordenada al final de su lista
                    self.latest_positions[entity_id].append((x, y))

            except OSError:
                # Ocurre si cerramos el socket al desconectar
                break
            except Exception as e:
                print(f"[ERROR UDP Thread] {e}")

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
                print(f"Mensaje de salida TCP: {message}")
            except Exception as e:
                print(f"Error in: {e}")

    def receive_json(self):

        if self.pending_messages:
            return self.pending_messages.pop(0)

        if self.connected:
            try:
                data = self.client_tcp.recv(4096).decode("utf-8")
                if not data:
                    print("[NETWORK] Servidor TCP cerró la conexión.")
                    self._close_tcp_socket()
                    return {"type": "DISCONNECTED"}
                print(f"Mensaje de entrada TCP: {data}")
                if data:
                    self.receive_buffer += data
                    if "\n" in self.receive_buffer:
                        partes = self.receive_buffer.split("\n")
                        self.receive_buffer = partes.pop()

                        # Ahora 'partes' solo tiene paquetes JSON completos y perfectos
                        for json_packet in partes:
                            if json_packet.strip():  # Ignorar líneas en blanco
                                try:
                                    # Convertimos a diccionario y lo formamos en la fila
                                    json_valido = json.loads(json_packet)
                                    self.pending_messages.append(json_valido)
                                except json.JSONDecodeError as e:
                                    print(
                                        f"Error encountered while reading JSON: {json_packet} -> {e}"
                                    )

                        # Si logramos procesar algo, devolvemos el primer mensaje de la fila
                        if self.pending_messages:
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

        if self.client_udp is not None:
            try:
                self.client_udp.close()
            except Exception as e:
                print(f"Error cerrando el socket UDP: {e}")

        self.client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        print("Disconnection complete and network restarted.")

    def calculate_rtt(self, sent_timestamp):
        """Called when the UDP thread receives a ping echo from the C++ server."""
        current_time = time.time()
        # Time difference in seconds * 1000 = milliseconds
        self.current_rtt = (current_time - sent_timestamp) * 1000
