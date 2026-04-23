# 🤖 Plan de Implementación del Sistema de Bot — Sharp-Blaze

## 1. Dónde vive el bot en el proyecto

```
src/client/
├── ia/
│   ├── __init__.py
│   ├── bot_controller.py     ← Clase base + orquestador principal
│   ├── bot_state.py          ← Estado del juego desde la perspectiva del bot
│   ├── bot_network.py        ← Wrapper headless del NetworkManager
│   ├── easy_bot.py           ← Dificultad fácil  (reactivo simple)
│   ├── medium_bot.py         ← Dificultad media  (LP + combate básico)
│   └── hard_bot.py           ← Dificultad alta   (LP agresivo + A*)
```

> [!NOTE]
> El bot NO usa Pygame. Es Python puro que corre en un hilo de fondo y se comunica con el servidor igual que cualquier cliente. El archivo `main_screen.py` ya tiene el botón "Bot Match" (`btn_bot`) que solo necesita ser conectado.

---

## 2. Paso 1 — `bot_network.py`: El puente con el servidor

Este módulo es el `NetworkManager` del bot, pero sin Pygame. Reutiliza toda la lógica TCP/UDP existente. La diferencia clave es que el bot no tiene `OFFLINE_DEBUG_MODE`.

```python
# src/client/ia/bot_network.py
import socket, json, struct, threading, time
from utils.config import Config

class BotNetworkBridge:
    """
    Versión headless del NetworkManager para el bot.
    Sin Pygame, sin modo offline. Solo red real.
    """
    def __init__(self):
        self.client_tcp = None
        self.connected = False
        self.receive_buffer = ""
        self.pending_messages = []
        self._lock = threading.Lock()

        # UDP
        self.client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_udp.bind(("0.0.0.0", 0))  # puerto aleatorio libre
        self.latest_positions = {}
        self._udp_running = False
        self.cell_size = 50  # igual que en network.py original

    # ---- TCP ----
    def connect(self, nickname: str) -> bool:
        """Bloquea hasta conectarse o fallar. Devuelve True si éxito."""
        payload = json.dumps({
            "type": "INITIAL_CONNECT",
            "payload": {"player_id": nickname, "client_version": "0.0.1", "is_ready": True}
        }) + "\n"
        try:
            self.client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_tcp.settimeout(5.0)
            self.client_tcp.connect((Config.SERVER_IP, Config.TCP_PORT_SERVER))
            self.client_tcp.send(payload.encode("utf-8"))
            self.client_tcp.settimeout(None)
            self.client_tcp.setblocking(False)
            self.connected = True
            return True
        except Exception as e:
            print(f"[BOT] Error de conexión TCP: {e}")
            return False

    def send_json(self, data: dict):
        if not self.connected: return
        try:
            msg = json.dumps(data) + "\n"
            self.client_tcp.send(msg.encode("utf-8"))
        except Exception as e:
            print(f"[BOT] Error TCP send: {e}")

    def receive_json(self) -> dict | None:
        """Non-blocking. Devuelve None si no hay mensaje."""
        with self._lock:
            if self.pending_messages:
                return self.pending_messages.pop(0)
        if not self.connected: return None
        try:
            data = self.client_tcp.recv(4096).decode("utf-8")
            if data:
                self.receive_buffer += data
                while "\n" in self.receive_buffer:
                    line, self.receive_buffer = self.receive_buffer.split("\n", 1)
                    if line.strip():
                        try:
                            with self._lock:
                                self.pending_messages.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            with self._lock:
                if self.pending_messages:
                    return self.pending_messages.pop(0)
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"[BOT] Error TCP recv: {e}")
            self.connected = False
        return None

    # ---- UDP ----
    def init_udp(self, session_id: int, player_id: int):
        header = struct.pack("!ii", session_id, player_id)
        checksum = 0
        for b in header: checksum ^= b
        packet = header + struct.pack("!I", checksum)
        self.client_udp.sendto(packet, (Config.SERVER_IP, 5556))
        self._udp_running = True
        threading.Thread(target=self._udp_loop, daemon=True).start()

    def _udp_loop(self):
        while self._udp_running:
            try:
                raw, _ = self.client_udp.recvfrom(1024)
                if len(raw) == 12:
                    entity_id, gx, gy = struct.unpack("<iff", raw)
                    wx = (gx * self.cell_size) + (self.cell_size // 2)
                    wy = (gy * self.cell_size) + (self.cell_size // 2)
                    self.latest_positions[entity_id] = (wx, wy)
            except OSError:
                break
            except Exception as e:
                print(f"[BOT UDP] {e}")

    def get_positions(self) -> dict:
        return dict(self.latest_positions)

    def disconnect(self):
        self._udp_running = False
        self.connected = False
        if self.client_tcp: self.client_tcp.close()
        if self.client_udp: self.client_udp.close()
```

---

## 3. Paso 2 — `bot_state.py`: El cerebro de información

El bot necesita mantener su propio modelo del mundo. Este objeto se actualiza con cada mensaje TCP y cada snapshot UDP.

```python
# src/client/ia/bot_state.py

class BotState:
    """
    Estado del juego desde la perspectiva del bot.
    Se actualiza en cada tick del loop de decisión.
    """
    def __init__(self, player_id: int):
        self.player_id = player_id   # 1 o 2

        # Recursos
        self.gold = 500

        # Unidades propias (entity_id → (x, y))
        self.my_units: dict[int, tuple] = {}
        # Unidades enemigas (entity_id → (x, y))
        self.enemy_units: dict[int, tuple] = {}

        # Estructuras del mapa (entity_id → (x, y))
        self.structures: dict[int, tuple] = {}

        # Shop y minas (entity_id → (x, y))
        self.shops: dict[int, tuple] = {}
        self.mines: dict[int, tuple] = {}

        # ¿Tenemos autorización del shop?
        self.shop_authorized = False
        self.shop_unit_id = -1  # qué unidad está en el shop

    def apply_start_game(self, payload: dict):
        """Carga el estado inicial desde el mensaje START_GAME."""
        self.gold = payload.get("gold", 500)
        for str_id, pos in payload.get("units", {}).items():
            entity_id = int(str_id)
            self._classify_and_store(entity_id, pos[0], pos[1])
        for str_id, pos in payload.get("structures", {}).items():
            entity_id = int(str_id)
            self._classify_and_store(entity_id, pos[0], pos[1])

    def apply_tcp_message(self, msg: dict):
        """Aplica cualquier mensaje TCP entrante al estado."""
        t = msg.get("type")
        p = msg.get("payload", {})

        if t == "RESOURCES":
            self.gold = p.get("new_balance", self.gold)

        elif t == "BUY_UNIT_RESULT" and msg.get("status") == "accepted":
            uid = p["unit_id"]
            self.my_units[uid] = (p["spawn_x"], p["spawn_y"])
            self.gold = p["new_balance"]

        elif t == "UNIT_SPAWNED":
            uid = p["unit_id"]
            owner = p.get("owner_player", -1)
            if owner == self.player_id:
                self.my_units.setdefault(uid, (0, 0))
            else:
                self.enemy_units.setdefault(uid, (0, 0))

        elif t == "SHOP_AUTORIZATION":
            self.shop_authorized = p.get("authorized", False)
            self.shop_unit_id = p.get("unit_id", -1)

        elif t == "UNIT_DESTROYED":
            uid = p.get("unit_id", -1)
            self.my_units.pop(uid, None)
            self.enemy_units.pop(uid, None)

    def apply_positions(self, positions: dict):
        """Actualiza posiciones desde el snapshot UDP."""
        for entity_id, (x, y) in positions.items():
            if entity_id in self.my_units:
                self.my_units[entity_id] = (x, y)
            elif entity_id in self.enemy_units:
                self.enemy_units[entity_id] = (x, y)

    def _classify_and_store(self, entity_id: int, x: float, y: float):
        """Clasifica una entidad por su ID y la guarda en el dict correcto."""
        # Rangos de IDs (igual que GameTypes.h)
        if 0 <= entity_id <= 4999:       # P1: estructuras + unidades
            if entity_id < 1000:
                self.structures[entity_id] = (x, y)
            else:
                if self.player_id == 1:
                    self.my_units[entity_id] = (x, y)
                else:
                    self.enemy_units[entity_id] = (x, y)
        elif 5000 <= entity_id <= 9999:  # P2: estructuras + unidades
            if entity_id < 6000:
                self.structures[entity_id] = (x, y)
            else:
                if self.player_id == 2:
                    self.my_units[entity_id] = (x, y)
                else:
                    self.enemy_units[entity_id] = (x, y)
        elif 10000 <= entity_id <= 10999:
            self.mines[entity_id] = (x, y)
        elif 11000 <= entity_id <= 11999:
            self.shops[entity_id] = (x, y)
```

---

## 4. Paso 3 — `bot_controller.py`: El orquestador

Esta es la clase base de la que heredan Easy/Medium/Hard. Contiene el ciclo de vida completo del bot.

```python
# src/client/ia/bot_controller.py
import threading, time
from ia.bot_network import BotNetworkBridge
from ia.bot_state import BotState
from utils.json import JSON_Manager

class BotController:
    """
    Clase base para todos los bots.
    Gestiona: conexión, matchmaking, inicio de partida, loop de decisión.
    Las subclases solo implementan `think()`.
    """
    DECISION_INTERVAL_S = 1.0  # overrideable por subclases

    def __init__(self, nickname: str):
        self.nickname = nickname
        self.net = BotNetworkBridge()
        self.state: BotState | None = None
        self.session_id: int = -1
        self.player_id: int = -1
        self._running = False

    # ---- Lifecycle ----

    def start(self):
        """Lanza el bot en un hilo de fondo."""
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._running = False
        self.net.disconnect()

    def _run(self):
        """Loop principal del bot."""
        print(f"[BOT] Iniciando como '{self.nickname}'")

        if not self.net.connect(self.nickname):
            print("[BOT] No se pudo conectar. Abortando.")
            return

        # Fase 1: Matchmaking
        if not self._wait_for_match():
            return

        # Fase 2: Confirmar inicio
        self.net.send_json(JSON_Manager.get_startgame())
        if not self._wait_for_game_start():
            return

        # Fase 3: Abrir UDP
        self.net.init_udp(self.session_id, self.player_id)

        # Fase 4: Loop de decisión
        self._decision_loop()

    def _wait_for_match(self, timeout_s=120) -> bool:
        deadline = time.time() + timeout_s
        while self._running and time.time() < deadline:
            msg = self.net.receive_json()
            if msg:
                if msg.get("type") == "MATCH_FOUND":
                    payload = msg["payload"]
                    raw_session = payload.get("session_id", "session_0")
                    # session_id puede venir como "session_1" → extraer el número
                    self.session_id = int(str(raw_session).replace("session_", ""))
                    self.player_id = int(payload.get("global_player_id", 1))
                    self.state = BotState(self.player_id)
                    print(f"[BOT] Match encontrado. Session={self.session_id} PlayerId={self.player_id}")
                    return True
            time.sleep(0.1)
        print("[BOT] Timeout esperando MATCH_FOUND.")
        return False

    def _wait_for_game_start(self, timeout_s=60) -> bool:
        deadline = time.time() + timeout_s
        while self._running and time.time() < deadline:
            msg = self.net.receive_json()
            if msg:
                if msg.get("type") == "START_GAME" and msg["payload"].get("start"):
                    self.state.apply_start_game(msg["payload"])
                    print(f"[BOT] Partida iniciada. Oro inicial: {self.state.gold}")
                    return True
            time.sleep(0.1)
        print("[BOT] Timeout esperando START_GAME.")
        return False

    def _decision_loop(self):
        last_decision = time.time()
        while self._running and self.net.connected:
            # Actualizar estado con mensajes TCP
            msg = self.net.receive_json()
            if msg:
                self.state.apply_tcp_message(msg)

            # Actualizar posiciones UDP
            positions = self.net.get_positions()
            if positions:
                self.state.apply_positions(positions)

            # Decisión periódica
            now = time.time()
            if now - last_decision >= self.DECISION_INTERVAL_S:
                self.think()
                last_decision = now

            time.sleep(0.05)  # ~20 iteraciones/s para no saturar la CPU

    # ---- Interface para subclases ----

    def think(self):
        """Implementar en cada dificultad."""
        raise NotImplementedError
```

---

## 5. Paso 4 — `easy_bot.py`: Dificultad Fácil

**Estrategia:** Reactiva, sin LP. Reglas simples de prioridad:
1. Si no tiene unidades → no puede hacer nada (espera a tener al menos 1)
2. Si tiene oro ≥ 100 y no tiene Shop Auth → mover unidad más cercana al Shop
3. Si tiene Shop Auth → comprar 1 Collector
4. Cada 5 decisiones → mover todos los Collectors hacia la mina más cercana

```python
# src/client/ia/easy_bot.py
import math
from ia.bot_controller import BotController
from utils.json import JSON_Manager

class EasyBot(BotController):
    """
    Bot de dificultad fácil.
    - Toma decisiones cada 1 segundo.
    - Solo compra Collectors.
    - No ataca.
    - Mueve unidades al Shop para comprar, luego a la mina.
    """
    DECISION_INTERVAL_S = 1.0

    def __init__(self, nickname="BOT_EASY"):
        super().__init__(nickname)
        self._tick = 0
        self.COLLECTOR_COST = 100
        self.ATTACKER_COST = 200

    def think(self):
        self._tick += 1
        state = self.state

        if not state.my_units:
            return  # No hay unidades aún, esperar

        # --- PRIORIDAD 1: Comprar si tenemos autorización ---
        if state.shop_authorized and state.gold >= self.COLLECTOR_COST:
            print("[EASY] Comprando Collector")
            self.net.send_json(JSON_Manager.get_unit_recolectors())
            return

        # --- PRIORIDAD 2: Mover unidad al Shop si tenemos oro pero no auth ---
        if state.gold >= self.COLLECTOR_COST and not state.shop_authorized and state.shops:
            shop_pos = next(iter(state.shops.values()))  # primer shop
            unit_id, unit_pos = self._closest_unit_to(shop_pos, state.my_units)
            if unit_id is not None:
                print(f"[EASY] Moviendo unidad {unit_id} al Shop {shop_pos}")
                self.net.send_json(JSON_Manager.get_moveorder(unit_id, shop_pos[0], shop_pos[1]))
            return

        # --- PRIORIDAD 3: Cada 5 ticks mover Collectors hacia minas ---
        if self._tick % 5 == 0 and state.mines:
            mine_pos = next(iter(state.mines.values()))  # mina más cercana (simple)
            for uid, upos in list(state.my_units.items()):
                # Solo mover Collectors (IDs 3000-4999 para P1, 8000-9999 para P2)
                if self._is_collector(uid):
                    print(f"[EASY] Moviendo collector {uid} a mina {mine_pos}")
                    self.net.send_json(JSON_Manager.get_moveorder(uid, mine_pos[0], mine_pos[1]))

    # ---- Helpers ----

    def _closest_unit_to(self, target_pos, units: dict):
        """Devuelve (unit_id, pos) de la unidad propia más cercana al target."""
        best_id, best_dist = None, float("inf")
        for uid, pos in units.items():
            d = math.hypot(pos[0] - target_pos[0], pos[1] - target_pos[1])
            if d < best_dist:
                best_dist = d
                best_id = uid
        return best_id, units.get(best_id)

    def _is_collector(self, entity_id: int) -> bool:
        return (3000 <= entity_id <= 4999) or (8000 <= entity_id <= 9999)

    def _is_attacker(self, entity_id: int) -> bool:
        return (1000 <= entity_id <= 2999) or (6000 <= entity_id <= 7999)
```

---

## 6. Paso 5 — `medium_bot.py` y `hard_bot.py`: Bosquejo

Estos son los próximos pasos, pero la estructura ya está definida. Solo hay que implementar `think()`.

```python
# src/client/ia/medium_bot.py
from scipy.optimize import linprog
from ia.bot_controller import BotController

class MediumBot(BotController):
    """
    - Decisión cada 500ms.
    - LP para decidir cuántos Collectors y Attackers comprar.
    - Attackers atacan unidades enemigas si las detectan cerca.
    """
    DECISION_INTERVAL_S = 0.5

    def think(self):
        # Usar LP para decidir producción
        # x = [x_collectors, x_attackers]
        # Maximizar: 0.7*x_c + 0.7*x_a
        # Sujeto a: 100*x_c + 200*x_a <= gold
        #           x_c + x_a <= 50 - len(my_units)
        pass  # TODO: implementar


# src/client/ia/hard_bot.py
from ia.bot_controller import BotController

class HardBot(BotController):
    """
    - Decisión cada 200ms.
    - LP agresivo: prioriza Attackers.
    - Detecta y persigue unidades enemigas.
    - Ataca base enemiga directamente.
    """
    DECISION_INTERVAL_S = 0.2

    def think(self):
        pass  # TODO: implementar
```

---

## 7. Paso 6 — Integrar en `main_screen.py`

El botón "Bot Match" ya existe en la pantalla principal. Solo necesita conectarse:

```python
# En main_screen.py, handle_events():
elif self.btn_bot.button_rectangle.collidepoint(mouse_pos):
    from ia.easy_bot import EasyBot   # o MediumBot / HardBot
    bot = EasyBot(nickname="BOT_EASY")
    bot.start()   # corre en hilo de fondo, no bloquea Pygame
    self.screen_manager.change_screen("JOIN")  # el humano va al lobby normalmente
```

> [!IMPORTANT]
> El bot corre en su propio hilo de fondo. No interfiere con el loop de Pygame del jugador humano. Ambos se conectan independientemente al mismo servidor.

---

## 8. Orden de implementación recomendado

| Paso | Archivo | Descripción | Prioridad |
|---|---|---|---|
| 1 | `bot_network.py` | Crear el puente de red headless | 🔴 Alta |
| 2 | `bot_state.py` | Modelo del estado del juego | 🔴 Alta |
| 3 | `bot_controller.py` | Loop base: conexión + matchmaking + decisión | 🔴 Alta |
| 4 | `easy_bot.py` | Implementar `think()` reactivo simple | 🔴 Alta |
| 5 | Integrar en `main_screen.py` | Conectar el botón "Bot Match" | 🟡 Media |
| 6 | `medium_bot.py` | LP de producción + combate básico | 🟡 Media |
| 7 | `hard_bot.py` | LP agresivo + persecución de enemigos | 🟢 Baja |

---

## 9. Variables clave que el bot necesita monitorear

| Variable | Fuente | Uso en la decisión |
|---|---|---|
| `state.gold` | TCP `RESOURCES` | Decidir si puede comprar |
| `state.my_units` | TCP `BUY_UNIT_RESULT` + UDP | Mover, enviar al Shop |
| `state.shops` | TCP `START_GAME` | Destino para autorización |
| `state.mines` | TCP `START_GAME` | Destino para Collectors |
| `state.shop_authorized` | TCP `SHOP_AUTHORIZATION` | Trigger para comprar |
| `state.enemy_units` | TCP `UNIT_SPAWNED` + UDP | Combate (Medium/Hard) |
