# ia/bot_controller.py
# CAPA DE SERVICIO (Service Layer)
# Responsabilidad: gestionar el ciclo de vida completo del bot.
#   1. Conexion TCP al servidor
#   2. Espera del emparejamiento (MATCH_FOUND)
#   3. Confirmacion de inicio (START_GAME)
#   4. Apertura del canal UDP
#   5. Loop de decision periodica
#
# Las subclases (EasyBot, MediumBot, HardBot) solo implementan think().
# Este archivo NO contiene logica de estrategia.

import threading
import time

from ia.bot_network import BotNetworkBridge
from ia.bot_state   import BotState
from utils.json     import JSON_Manager


class BotController:
    """
    Clase base para todos los bots del juego.

    Ciclo de vida:
        start() → hilo de fondo → _run() → connect → matchmaking
                → start_game → udp → decision loop → stop()

    Subclases deben implementar:
        think(self) -> None
    """

    # Intervalo entre decisiones en segundos. Las subclases pueden
    # sobreescribir este valor para cambiar la velocidad de reaccion.
    DECISION_INTERVAL_S: float = 1.0

    def __init__(self, nickname: str):
        self.nickname = nickname
        self.net      = BotNetworkBridge()
        self.state    = BotState()

        self._running        = False
        self._thread: threading.Thread | None = None

        print(f"[BotController] Bot creado con nickname='{nickname}'")

    # ─────────────────────────────────────────────────────────
    #  API publica
    # ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Inicia el bot en un hilo de fondo (no bloqueante).
        El hilo es daemon=True: muere automaticamente si el proceso
        principal (Pygame) termina.
        """
        if self._running:
            print("[BotController][WARN] start() llamado pero el bot ya corre.")
            return

        self._running = True
        self._thread  = threading.Thread(
            target=self._run,
            name=f"BotThread-{self.nickname}",
            daemon=True,
        )
        self._thread.start()
        print(f"[BotController] Hilo del bot iniciado: {self._thread.name}")

    def stop(self) -> None:
        """Detiene el bot y cierra todas las conexiones."""
        print("[BotController] Deteniendo bot...")
        self._running = False
        self.net.disconnect()
        print("[BotController] Bot detenido.")

    # ─────────────────────────────────────────────────────────
    #  Ciclo de vida interno
    # ─────────────────────────────────────────────────────────

    def _run(self) -> None:
        """
        Loop principal del bot. Corre en el hilo de fondo.
        Secuencia: conectar → match → start → udp → decisiones.
        """
        print(f"[BotController] === Iniciando bot '{self.nickname}' ===")

        # FASE 1: Conexion TCP
        if not self.net.connect(self.nickname):
            print("[BotController][ERROR] No se pudo conectar. Bot abortando.")
            self._running = False
            return

        # FASE 2: Esperar emparejamiento
        if not self._wait_for_match():
            print("[BotController][ERROR] No se encontro partida. Bot abortando.")
            self._running = False
            return

        # FASE 3: Confirmar que el bot esta listo para jugar
        # El servidor espera START_GAME con start=false de ambos jugadores.
        print("[BotController] Enviando confirmacion de inicio (START_GAME)...")
        self.net.send_json(JSON_Manager.get_startgame())

        # FASE 4: Esperar que el servidor inicie la partida
        if not self._wait_for_game_start():
            print("[BotController][ERROR] El servidor no inicio la partida. Bot abortando.")
            self._running = False
            return

        # FASE 5: Abrir canal UDP para recibir posiciones
        self.net.init_udp(self._session_id, self._player_id)

        # FASE 6: Loop de decision
        print("[BotController] === Entrando al loop de decision ===")
        self._decision_loop()

        print(f"[BotController] === Bot '{self.nickname}' finalizado ===")

    def _wait_for_match(self, timeout_s: float = 120.0) -> bool:
        """
        Bloquea hasta recibir MATCH_FOUND del servidor o timeout.
        Guarda session_id y player_id cuando llega el match.

        Returns:
            True si se encontro partida, False si timeout.
        """
        print(f"[BotController] Esperando MATCH_FOUND (timeout={timeout_s}s)...")
        deadline = time.time() + timeout_s

        while self._running and time.time() < deadline:
            msg = self.net.receive_json()
            if msg:
                msg_type = msg.get("type", "")

                if msg_type == "MATCH_FOUND":
                    payload          = msg.get("payload", {})
                    self._session_id = int(payload.get("session_id", 0))
                    self._player_id  = int(payload.get("global_player_id", 2))
                    opponent         = payload.get("opponent", "?")

                    print(f"[BotController] MATCH_FOUND recibido.")
                    print(f"  session_id = {self._session_id}")
                    print(f"  player_id  = {self._player_id}")
                    print(f"  rival      = '{opponent}'")
                    return True

                # Ignorar mensajes de cola mientras esperamos el match
                elif msg_type == "QUEUE_STATUS":
                    waiting = msg.get("payload", {}).get("players_waiting", "?")
                    print(f"[BotController] En cola. Jugadores esperando: {waiting}")

            time.sleep(0.1)

        print("[BotController][WARN] Timeout esperando MATCH_FOUND.")
        return False

    def _wait_for_game_start(self, timeout_s: float = 60.0) -> bool:
        """
        Bloquea hasta recibir START_GAME con start=true del servidor.
        Cuando llega, carga el estado inicial en BotState.

        Returns:
            True si la partida inicio, False si timeout.
        """
        print(f"[BotController] Esperando START_GAME (timeout={timeout_s}s)...")
        deadline = time.time() + timeout_s

        while self._running and time.time() < deadline:
            msg = self.net.receive_json()
            if msg:
                if msg.get("type") == "START_GAME" and msg.get("payload", {}).get("start"):
                    self.state.apply_start_game(msg["payload"])
                    print("[BotController] Partida iniciada. Estado del mapa cargado.")
                    return True

            time.sleep(0.1)

        print("[BotController][WARN] Timeout esperando START_GAME.")
        return False

    def _decision_loop(self) -> None:
        """
        Loop principal de juego.

        Cada iteracion:
          1. Lee todos los mensajes TCP pendientes → actualiza BotState
          2. Lee snapshot UDP de posiciones → actualiza BotState
          3. Cada DECISION_INTERVAL_S segundos → llama a think()

        El intervalo de think() es configurable por subclase.
        """
        last_decision_time = time.time()
        last_summary_time  = time.time()

        while self._running and self.net.connected:

            # ── 1. Procesar mensajes TCP ──────────────────────────
            msg = self.net.receive_json()
            while msg:
                self.state.apply_tcp_message(msg)

                # Detectar fin de partida
                if msg.get("type") == "GAME_OVER":
                    print("[BotController] GAME_OVER recibido. Saliendo del loop.")
                    self._running = False
                    return

                msg = self.net.receive_json()

            # ── 2. Actualizar posiciones UDP ──────────────────────
            positions = self.net.get_positions()
            if positions:
                self.state.apply_positions(positions)

            # ── 3. Llamar a think() periodicamente ───────────────
            now = time.time()
            if now - last_decision_time >= self.DECISION_INTERVAL_S:
                self.think()
                last_decision_time = now

            # ── 4. Log de estado cada 10 segundos ────────────────
            if now - last_summary_time >= 10.0:
                print(f"[BotController] Estado: {self.state.summary()}")
                last_summary_time = now

            # Ceder CPU al resto del sistema (no quemar el procesador)
            time.sleep(0.05)   # ~20 iteraciones por segundo

    # ─────────────────────────────────────────────────────────
    #  Interfaz para subclases
    # ─────────────────────────────────────────────────────────

    def think(self) -> None:
        """
        Implementar en cada dificultad.
        Se llama cada DECISION_INTERVAL_S segundos durante la partida.
        Tiene acceso a:
            self.state  → BotState (el modelo del mundo)
            self.net    → BotNetworkBridge (para enviar comandos)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} debe implementar think()"
        )
