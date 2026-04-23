# ia/bot_state.py
# CAPA DE DOMINIO (Service Layer)
# Responsabilidad: mantener el modelo del mundo del juego
#                  desde la perspectiva del bot.
#
# Fuentes de datos:
#   - TCP: eventos discretos (RESOURCES, BUY_UNIT_RESULT, UNIT_SPAWNED...)
#   - UDP: posiciones continuas de todas las entidades
#
# El bot SIEMPRE es player_id = 2 (se conecta segundo).
# IDs de entidades del servidor (GameTypes.h):
#   Player 1 (humano):  estructuras 0-999 | attackers 1000-2999 | collectors 3000-4999
#   Player 2 (bot):     estructuras 5000-5999 | attackers 6000-7999 | collectors 8000-9999
#   Minas de oro:       10000-10999
#   Shops:              11000-11999

BOT_PLAYER_ID = 2

# ─── Rangos de IDs (igual que GameTypes.h) ───────────────────
HUMAN_STRUCTURES = (0,    999)
HUMAN_ATTACKERS  = (1000, 2999)
HUMAN_COLLECTORS = (3000, 4999)

BOT_STRUCTURES   = (5000, 5999)
BOT_ATTACKERS    = (6000, 7999)
BOT_COLLECTORS   = (8000, 9999)

MINES            = (10000, 10999)
SHOPS            = (11000, 11999)


def _in_range(entity_id: int, rng: tuple) -> bool:
    return rng[0] <= entity_id <= rng[1]


def classify_entity(entity_id: int) -> str:
    """
    Devuelve una etiqueta legible para el tipo de entidad según su ID.
    Útil para logs de debug.
    """
    if _in_range(entity_id, HUMAN_STRUCTURES):  return "human_structure"
    if _in_range(entity_id, HUMAN_ATTACKERS):   return "human_attacker"
    if _in_range(entity_id, HUMAN_COLLECTORS):  return "human_collector"
    if _in_range(entity_id, BOT_STRUCTURES):    return "bot_structure"
    if _in_range(entity_id, BOT_ATTACKERS):     return "bot_attacker"
    if _in_range(entity_id, BOT_COLLECTORS):    return "bot_collector"
    if _in_range(entity_id, MINES):             return "mine"
    if _in_range(entity_id, SHOPS):             return "shop"
    return "unknown"


class BotState:
    """
    Modelo del mundo del juego desde la perspectiva del bot.

    Atributos principales:
        gold              : Oro actual del bot
        my_units          : {entity_id: (x, y)} — unidades propias del bot
        enemy_units       : {entity_id: (x, y)} — unidades del humano
        my_base           : (x, y) de la base del bot (estructura propia)
        enemy_base        : (x, y) de la base del humano
        mines             : {entity_id: (x, y)} de minas de oro
        shops             : {entity_id: (x, y)} de tiendas
        shop_authorized   : True si alguna unidad del bot está cerca del shop
        shop_unit_id      : ID de la unidad que activó la autorización
    """

    def __init__(self):
        print("[BotState] Inicializando estado del bot (player_id=2 fijo)...")

        self.gold: int = 0

        # Unidades propias y enemigas: {entity_id: (x, y)}
        self.my_units:    dict[int, tuple] = {}
        self.enemy_units: dict[int, tuple] = {}

        # Estructuras fijas del mapa
        self.my_base:    tuple | None = None   # (x, y) base del bot
        self.my_base_id: int | None   = None
        self.enemy_base: tuple | None = None   # (x, y) base del humano
        self.enemy_base_id: int | None = None
        self.mines: dict[int, tuple]  = {}     # minas de oro
        self.shops: dict[int, tuple]  = {}     # tiendas

        # Estado de autorización del shop
        self.shop_authorized: bool = False
        self.shop_unit_id:    int  = -1

        print("[BotState] Estado inicial listo.")

    # ─────────────────────────────────────────────────────────
    #  Carga del estado inicial (mensaje START_GAME)
    # ─────────────────────────────────────────────────────────

    def apply_start_game(self, payload: dict) -> None:
        """
        Carga el estado inicial recibido en el mensaje START_GAME del servidor.
        Este mensaje llega una sola vez al inicio de la partida y contiene:
          - gold: oro inicial de ambos jugadores (igual para los dos)
          - units: posiciones iniciales de todas las unidades
          - structures: posiciones de bases, minas y shops

        Args:
            payload: el dict dentro de data["payload"] del mensaje START_GAME
        """
        self.gold = payload.get("gold", 500)
        print(f"[BotState] START_GAME recibido. Oro inicial: {self.gold}")

        # Clasificar unidades iniciales
        for str_id, pos in payload.get("units", {}).items():
            entity_id = int(str_id)
            x, y = float(pos[0]), float(pos[1])
            self._classify_and_store(entity_id, x, y)

        # Clasificar estructuras (bases, minas, shops)
        for str_id, pos in payload.get("structures", {}).items():
            entity_id = int(str_id)
            x, y = float(pos[0]), float(pos[1])
            self._classify_and_store(entity_id, x, y)

        print(f"[BotState] Mapa cargado:")
        print(f"  Unidades propias:   {list(self.my_units.keys())}")
        print(f"  Unidades enemigas:  {list(self.enemy_units.keys())}")
        print(f"  Minas:              {list(self.mines.keys())}")
        print(f"  Shops:              {list(self.shops.keys())}")
        print(f"  Mi base:            {self.my_base}")
        print(f"  Base enemiga:       {self.enemy_base}")

    # ─────────────────────────────────────────────────────────
    #  Actualización por mensajes TCP entrantes
    # ─────────────────────────────────────────────────────────

    def apply_tcp_message(self, msg: dict) -> None:
        """
        Aplica un mensaje TCP del servidor al estado del bot.
        Debe llamarse cada vez que receive_json() devuelve algo.

        Mensajes que modifican el estado:
          RESOURCES         → actualiza el oro del bot
          BUY_UNIT_RESULT   → registra la nueva unidad comprada
          UNIT_SPAWNED      → registra unidad nueva (propia o enemiga)
          SHOP_AUTORIZATION → actualiza si podemos comprar o no
          UNIT_DESTROYED    → elimina una unidad del estado
        """
        msg_type = msg.get("type", "")
        payload  = msg.get("payload", {})

        if msg_type == "RESOURCES":
            old_gold = self.gold
            self.gold = payload.get("new_balance", self.gold)
            print(f"[BotState] Oro actualizado: {old_gold} -> {self.gold}")

        elif msg_type == "SHOP_AUTHORIZATION":  # servidor: clientProtocol.cpp linea 255
            self.shop_authorized = payload.get("authorized", False)
            self.shop_unit_id    = int(payload.get("unit_id", -1))
            status = "AUTORIZADO" if self.shop_authorized else "no autorizado"
            print(f"[BotState] Shop: {status} (unit={self.shop_unit_id})")

        elif msg_type == "ENTITY_DESTROYED":    # servidor: clientProtocol.cpp linea 332
            uid = int(payload.get("entity_id", -1))
            removed_from = None
            if uid in self.my_units:
                del self.my_units[uid]
                removed_from = "propias"
            elif uid in self.enemy_units:
                del self.enemy_units[uid]
                removed_from = "enemigas"
            if removed_from:
                print(f"[BotState] Entidad {uid} destruida (era de {removed_from})")

        elif msg_type == "UNIT_DAMAGED":        # servidor: clientProtocol.cpp linea 306
            uid = int(payload.get("target_entity_id", -1))
            hp  = int(payload.get("current_hp", -1))
            if uid >= 0:
                print(f"[BotState] Entidad {uid} danada. HP actual: {hp}")

        elif msg_type == "GAME_OVER":           # servidor: clientProtocol.cpp linea 351
            winner = int(payload.get("winner_player_id", -1))
            if winner == BOT_PLAYER_ID:
                print("[BotState] GAME_OVER: el bot GANO")
            else:
                print("[BotState] GAME_OVER: el bot PERDIO")

    # ─────────────────────────────────────────────────────────
    #  Actualización por posiciones UDP
    # ─────────────────────────────────────────────────────────

    def apply_positions(self, positions: dict[int, tuple]) -> None:
        """
        Actualiza las posiciones de las unidades con el snapshot UDP.
        Llamar a esto despues de cada get_positions() del BotNetworkBridge.

        IMPORTANTE: Las unidades nuevas (recien compradas) llegan PRIMERO
        por UDP con un entity_id desconocido. Este metodo las registra
        automaticamente en my_units o enemy_units segun su ID.

        Args:
            positions: {entity_id: (world_x, world_y)} del snapshot UDP
        """
        for entity_id, (x, y) in positions.items():
            if entity_id in self.my_units:
                # Actualizar posicion de unidad propia conocida
                self.my_units[entity_id] = (x, y)
            elif entity_id in self.enemy_units:
                # Actualizar posicion de unidad enemiga conocida
                self.enemy_units[entity_id] = (x, y)
            else:
                # Entidad desconocida: clasificarla por su ID
                label = classify_entity(entity_id)
                if label in ("bot_attacker", "bot_collector"):
                    self.my_units[entity_id] = (x, y)
                    print(f"[BotState] Nueva unidad propia detectada via UDP: id={entity_id} ({label})")
                elif label in ("human_attacker", "human_collector"):
                    self.enemy_units[entity_id] = (x, y)
                    print(f"[BotState] Nueva unidad enemiga detectada via UDP: id={entity_id} ({label})")
                # Estructuras estaticas (bases, minas, shops) se ignoran

    # ─────────────────────────────────────────────────────────
    #  Helpers de consulta para la capa de estrategia
    # ─────────────────────────────────────────────────────────

    def get_my_collectors(self) -> dict[int, tuple]:
        """Devuelve solo las unidades recolectoras del bot."""
        return {uid: pos for uid, pos in self.my_units.items()
                if _in_range(uid, BOT_COLLECTORS)}

    def get_my_attackers(self) -> dict[int, tuple]:
        """Devuelve solo las unidades atacantes del bot."""
        return {uid: pos for uid, pos in self.my_units.items()
                if _in_range(uid, BOT_ATTACKERS)}

    def get_nearest_mine(self, from_pos: tuple) -> tuple | None:
        """
        Devuelve la posición (x, y) de la mina más cercana a from_pos.
        Devuelve None si no hay minas en el estado.
        """
        if not self.mines:
            return None
        import math
        return min(
            self.mines.values(),
            key=lambda mine_pos: math.hypot(
                mine_pos[0] - from_pos[0],
                mine_pos[1] - from_pos[1]
            )
        )

    def summary(self) -> str:
        """Devuelve un resumen del estado actual. Útil para logs periódicos."""
        return (
            f"Oro={self.gold} | "
            f"Mis unidades={len(self.my_units)} "
            f"(col={len(self.get_my_collectors())}, atk={len(self.get_my_attackers())}) | "
            f"Enemigas={len(self.enemy_units)} | "
            f"ShopAuth={self.shop_authorized}"
        )

    # ─────────────────────────────────────────────────────────
    #  Clasificación interna de entidades por ID
    # ─────────────────────────────────────────────────────────

    def _classify_and_store(self, entity_id: int, x: float, y: float) -> None:
        """
        Dado un ID y posición, guarda la entidad en el dict correcto.
        Usa los rangos definidos en GameTypes.h del servidor C++.
        """
        label = classify_entity(entity_id)

        if label in ("bot_attacker", "bot_collector"):
            self.my_units[entity_id] = (x, y)

        elif label in ("human_attacker", "human_collector"):
            self.enemy_units[entity_id] = (x, y)

        elif label == "bot_structure":
            self.my_base = (x, y)
            self.my_base_id = entity_id

        elif label == "human_structure":
            self.enemy_base = (x, y)
            self.enemy_base_id = entity_id

        elif label == "mine":
            self.mines[entity_id] = (x, y)

        elif label == "shop":
            self.shops[entity_id] = (x, y)
