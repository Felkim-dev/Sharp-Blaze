# ia/bot_network.py
# CAPA DE ACCESO A DATOS (Capa más baja del Service Layer)
# Responsabilidad única: comunicación TCP/UDP con el servidor.
# No sabe nada de estrategia ni de estado del juego.

import socket
import json
import struct
import threading

from utils.config import Config

# ─────────────────────────────────────────────────────────────
#  Constantes de protocolo (igual que el servidor C++)
# ─────────────────────────────────────────────────────────────
_UDP_SERVER_PORT  = 5556      # Puerto UDP del servidor
_UDP_PACKET_SIZE  = 12        # Bytes por paquete de posición: <iff (id, x, y)
_GRID_CELL_SIZE   = 50        # Tamaño de celda para convertir grid → world


class BotNetworkBridge:
    """
    Cliente de red headless para el bot.

    Equivalente al NetworkManager del cliente Pygame, pero sin
    dependencias de UI. Se conecta al servidor como un jugador normal.

    Uso básico:
        bridge = BotNetworkBridge()
        bridge.connect("BOT_EASY")      # TCP: INITIAL_CONNECT
        bridge.send_json({...})          # TCP: enviar comando
        msg = bridge.receive_json()     # TCP: leer respuesta (non-blocking)
        bridge.init_udp(session, player) # UDP: abrir canal de posiciones
        pos = bridge.get_positions()    # UDP: leer últimas posiciones
        bridge.disconnect()
    """

    def __init__(self):
        print("[BotNetwork] Inicializando BotNetworkBridge...")

        # ── TCP ──────────────────────────────────────────────
        self._tcp_socket: socket.socket | None = None
        self.connected: bool = False
        self._recv_buffer: str = ""
        self._pending_messages: list[dict] = []
        self._tcp_lock = threading.Lock()  # protege acceso concurrente al buffer

        # ── UDP ──────────────────────────────────────────────
        self._udp_socket: socket.socket | None = None
        self._udp_running: bool = False
        self._udp_thread: threading.Thread | None = None
        self._positions: dict[int, tuple[float, float]] = {}
        self._pos_lock = threading.Lock()  # protege el dict de posiciones

        print("[BotNetwork] Bridge listo. Esperando llamada a connect().")

    # ─────────────────────────────────────────────────────────
    #  TCP — Conexión
    # ─────────────────────────────────────────────────────────

    def connect(self, nickname: str) -> bool:
        """
        Abre socket TCP y envía INITIAL_CONNECT al servidor.
        Bloqueante — espera hasta conectar o fallar (timeout 5s).

        Returns:
            True si la conexión fue exitosa, False si falló.
        """
        server_ip   = Config.SERVER_IP
        server_port = Config.TCP_PORT_SERVER

        print(f"[BotNetwork] Conectando a {server_ip}:{server_port} como '{nickname}'...")

        payload = {
            "type": "INITIAL_CONNECT",
            "payload": {
                "player_id":      nickname,
                "client_version": "0.0.1",
                "is_ready":       True,
            },
        }

        try:
            self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._tcp_socket.settimeout(5.0)
            self._tcp_socket.connect((server_ip, server_port))

            # Enviar INITIAL_CONNECT inmediatamente al conectar (igual que el cliente Pygame)
            message = json.dumps(payload) + "\n"
            self._tcp_socket.send(message.encode("utf-8"))
            print(f"[BotNetwork] INITIAL_CONNECT enviado para '{nickname}'.")

            # Cambiar a modo no-bloqueante para receive_json()
            self._tcp_socket.settimeout(None)
            self._tcp_socket.setblocking(False)

            self.connected = True
            print("[BotNetwork] Conexion TCP establecida. [OK]")
            return True

        except socket.timeout:
            print(f"[BotNetwork][ERROR] Timeout al conectar a {server_ip}:{server_port}")
            self._cleanup_tcp()
            return False
        except ConnectionRefusedError:
            print(f"[BotNetwork][ERROR] Conexión rechazada. ¿Está corriendo el servidor?")
            self._cleanup_tcp()
            return False
        except Exception as e:
            print(f"[BotNetwork][ERROR] Error inesperado al conectar: {e}")
            self._cleanup_tcp()
            return False

    # ─────────────────────────────────────────────────────────
    #  TCP — Envío
    # ─────────────────────────────────────────────────────────

    def send_json(self, data: dict) -> bool:
        """
        Serializa `data` como JSON y lo envía por TCP al servidor.
        El protocolo requiere que cada mensaje termine en '\\n'.

        Returns:
            True si el envío fue exitoso, False si hubo error.
        """
        if not self.connected or self._tcp_socket is None:
            print("[BotNetwork][WARN] send_json() llamado pero no hay conexión TCP.")
            return False
        try:
            message = json.dumps(data) + "\n"
            self._tcp_socket.send(message.encode("utf-8"))
            print(f"[BotNetwork][TCP OUT] {message.strip()}")
            return True
        except Exception as e:
            print(f"[BotNetwork][ERROR] send_json() falló: {e}")
            self.connected = False
            return False

    # ─────────────────────────────────────────────────────────
    #  TCP — Recepción
    # ─────────────────────────────────────────────────────────

    def receive_json(self) -> dict | None:
        """
        Lee el próximo mensaje JSON disponible del servidor (non-blocking).

        El servidor puede enviar múltiples JSONs en un mismo chunk TCP.
        Esta función los separa por '\\n' y los encola internamente.

        Returns:
            Un dict con el mensaje, o None si no hay nada disponible.
        """
        # Si ya hay mensajes encolados de lecturas anteriores, devolver el primero
        with self._tcp_lock:
            if self._pending_messages:
                return self._pending_messages.pop(0)

        if not self.connected or self._tcp_socket is None:
            return None

        try:
            raw = self._tcp_socket.recv(4096).decode("utf-8")
            if raw:
                self._recv_buffer += raw

                # Separar por '\n' para aislar mensajes completos
                while "\n" in self._recv_buffer:
                    line, self._recv_buffer = self._recv_buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            parsed = json.loads(line)
                            print(f"[BotNetwork][TCP IN] {line}")
                            with self._tcp_lock:
                                self._pending_messages.append(parsed)
                        except json.JSONDecodeError as e:
                            print(f"[BotNetwork][WARN] JSON inválido ignorado: {line} → {e}")

                with self._tcp_lock:
                    if self._pending_messages:
                        return self._pending_messages.pop(0)

        except BlockingIOError:
            # Normal en modo non-blocking: no hay datos disponibles aún
            pass
        except Exception as e:
            print(f"[BotNetwork][ERROR] receive_json() falló: {e}")
            self.connected = False

        return None

    # ─────────────────────────────────────────────────────────
    #  UDP — Canal de posiciones
    # ─────────────────────────────────────────────────────────

    def init_udp(self, session_id: int, player_id: int) -> None:
        """
        Abre el canal UDP enviando el paquete UDP_HELLO al servidor.
        Después lanza el hilo de escucha de posiciones.

        El servidor necesita este mensaje para saber a qué IP/puerto
        mandar los paquetes de posición de las unidades.

        Args:
            session_id: ID numérico de la sesión (extraído de MATCH_FOUND)
            player_id:  ID interno del jugador (1 o 2)
        """
        print(f"[BotNetwork] Abriendo canal UDP (session={session_id}, player={player_id})...")

        # Construir paquete UDP_HELLO: [session_id(4B)][player_id(4B)][checksum(4B)]
        header   = struct.pack("!ii", session_id, player_id)
        checksum = 0
        for byte in header:
            checksum ^= byte
        packet = header + struct.pack("!I", checksum)

        try:
            self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp_socket.bind(("0.0.0.0", 0))  # Puerto libre asignado por el OS
            local_port = self._udp_socket.getsockname()[1]
            print(f"[BotNetwork] Socket UDP creado en puerto local {local_port}.")

            self._udp_socket.sendto(packet, (Config.SERVER_IP, _UDP_SERVER_PORT))
            print(f"[BotNetwork] UDP_HELLO enviado a {Config.SERVER_IP}:{_UDP_SERVER_PORT}. [OK]")

            # Lanzar hilo de escucha en background (daemon=True → muere con el proceso)
            self._udp_running = True
            self._udp_thread = threading.Thread(
                target=self._udp_listen_loop,
                name="BotUDPListener",
                daemon=True,
            )
            self._udp_thread.start()
            print("[BotNetwork] Hilo UDP de escucha iniciado. [OK]")

        except Exception as e:
            print(f"[BotNetwork][ERROR] init_udp() falló: {e}")

    def _udp_listen_loop(self) -> None:
        """
        Hilo de fondo: recibe paquetes UDP de posición del servidor.

        Cada paquete es de 12 bytes con formato '<iff':
            entity_id (int32)  → ID de la entidad
            grid_x    (float)  → posición X en coordenadas de grid
            grid_y    (float)  → posición Y en coordenadas de grid

        Las coordenadas vienen en espacio de grid y se convierten
        a coordenadas del mundo multiplicando por GRID_CELL_SIZE.
        """
        print("[BotNetwork][UDP] Hilo de escucha arrancado.")
        packets_received = 0

        while self._udp_running and self._udp_socket:
            try:
                raw, _ = self._udp_socket.recvfrom(1024)

                if len(raw) == _UDP_PACKET_SIZE:
                    entity_id, grid_x, grid_y = struct.unpack("<iff", raw)

                    with self._pos_lock:
                        self._positions[entity_id] = (grid_x, grid_y)

                    packets_received += 1
                    # Log cada 300 paquetes para no saturar la consola (~5s a 60Hz)
                    if packets_received % 300 == 0:
                        print(f"[BotNetwork][UDP] {packets_received} paquetes recibidos. "
                              f"Entidades rastreadas: {len(self._positions)}")
                else:
                    print(f"[BotNetwork][UDP][WARN] Paquete de tamaño inesperado: {len(raw)}B")

            except OSError:
                # El socket fue cerrado (disconnect llamado)
                print("[BotNetwork][UDP] Socket cerrado. Hilo de escucha terminando.")
                break
            except Exception as e:
                print(f"[BotNetwork][UDP][ERROR] {e}")

    def get_positions(self) -> dict[int, tuple[float, float]]:
        """
        Devuelve una copia del snapshot actual de posiciones UDP.
        Thread-safe: usa lock para evitar condiciones de carrera.

        Returns:
            dict {entity_id: (world_x, world_y)}
        """
        with self._pos_lock:
            return dict(self._positions)

    # ─────────────────────────────────────────────────────────
    #  Desconexión
    # ─────────────────────────────────────────────────────────

    def disconnect(self) -> None:
        """Cierra todos los sockets y detiene los hilos."""
        print("[BotNetwork] Desconectando...")
        self._udp_running = False
        self.connected = False
        self._cleanup_tcp()
        self._cleanup_udp()
        print("[BotNetwork] Desconectado. [OK]")

    def _cleanup_tcp(self) -> None:
        if self._tcp_socket:
            try:
                self._tcp_socket.close()
            except Exception:
                pass
            self._tcp_socket = None

    def _cleanup_udp(self) -> None:
        if self._udp_socket:
            try:
                self._udp_socket.close()
            except Exception:
                pass
            self._udp_socket = None
