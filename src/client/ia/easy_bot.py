# ia/easy_bot.py
# DIFICULTAD FACIL
# Hereda de BotController e implementa think().
#
# Estrategia (reglas de prioridad, sin LP):
#   1. Si hay autorizacion del shop → comprar Collector
#   2. Si hay oro suficiente y no hay auth → mover unidad al shop
#   3. Cada N ticks → mover collectors hacia la mina mas cercana
#
# El bot NUNCA ataca. Solo recolecta.
# Toma una decision cada 1 segundo.

import math

from ia.bot_controller import BotController
from utils.json        import JSON_Manager


class EasyBot(BotController):
    """
    Bot de dificultad facil.

    Comportamiento:
    - Compra Collectors cuando tiene oro y autorizacion del shop.
    - Mueve una unidad al shop para obtener autorizacion.
    - Manda los Collectors a la mina mas cercana para recolectar.
    - No ataca nunca.

    Costo de unidades:
    - Collector: 100 de oro
    - Attacker:  200 de oro (no usado en Easy)
    """

    DECISION_INTERVAL_S = 1.0     # una decision por segundo
    COLLECTOR_COST      = 100

    def __init__(self, nickname: str = "BOT_EASY"):
        super().__init__(nickname)
        self._tick = 0            # contador de decisiones tomadas
        print("[EasyBot] Instanciado. Estrategia: solo recolectar.")

    # ─────────────────────────────────────────────────────────
    #  Estrategia principal
    # ─────────────────────────────────────────────────────────

    def think(self) -> None:
        """
        Logica de decision del bot facil.
        Llamada cada DECISION_INTERVAL_S segundos por BotController.
        """
        self._tick += 1
        state = self.state

        # Sin unidades propias no hay nada que hacer todavia
        if not state.my_units:
            print(f"[EasyBot] Tick {self._tick}: sin unidades, esperando...")
            return

        print(f"[EasyBot] Tick {self._tick} | {state.summary()}")

        # ── PRIORIDAD 1: Comprar si el shop nos autorizo ──────
        if state.shop_authorized and state.gold >= self.COLLECTOR_COST:
            print(f"[EasyBot] ACCION: Comprando Collector (oro={state.gold})")
            self.net.send_json(JSON_Manager.get_unit_recolectors())
            return

        # ── PRIORIDAD 2: Ir al shop si tenemos oro pero sin auth
        if state.gold >= self.COLLECTOR_COST and not state.shop_authorized and state.shops:
            shop_pos = next(iter(state.shops.values()))  # primer shop
            unit_id  = self._closest_unit_to(shop_pos, state.my_units)

            if unit_id is not None:
                tx, ty = int(shop_pos[0]), int(shop_pos[1])
                print(f"[EasyBot] ACCION: Moviendo unidad {unit_id} al shop {(tx, ty)}")
                self.net.send_json(JSON_Manager.get_moveorder(unit_id, tx, ty))
            return

        # ── PRIORIDAD 3: Mover collectors a minas cada 3 ticks
        if self._tick % 3 == 0 and state.mines:
            collectors = state.get_my_collectors()
            if not collectors:
                return

            for uid, upos in collectors.items():
                mine_pos = state.get_nearest_mine(from_pos=upos)
                if mine_pos:
                    tx, ty = int(mine_pos[0]), int(mine_pos[1])
                    print(f"[EasyBot] ACCION: Moviendo collector {uid} a mina {(tx, ty)}")
                    self.net.send_json(JSON_Manager.get_moveorder(uid, tx, ty))

    # ─────────────────────────────────────────────────────────
    #  Helpers internos
    # ─────────────────────────────────────────────────────────

    def _closest_unit_to(
        self,
        target_pos: tuple,
        units: dict,
    ) -> int | None:
        """
        Devuelve el entity_id de la unidad propia mas cercana a target_pos.
        Usa distancia euclidiana sobre coordenadas de grid.

        Returns:
            entity_id de la unidad mas cercana, o None si units esta vacio.
        """
        if not units:
            return None

        best_id   = None
        best_dist = float("inf")

        for uid, pos in units.items():
            dist = math.hypot(pos[0] - target_pos[0], pos[1] - target_pos[1])
            if dist < best_dist:
                best_dist = dist
                best_id   = uid

        return best_id
