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
    ATTACKER_COST       = 200
    MAX_COLLECTORS      = 15
    MAX_UNITS           = 50

    def __init__(self, nickname: str = "BOT_EASY"):
        super().__init__(nickname)
        self._tick = 0            # contador de decisiones tomadas
        
        # FSM de recolectores: uid -> estado ("TO_MINE", "WAIT_MINE", "TO_BASE", "WAIT_BASE")
        self.collector_state = {}
        self.wait_ticks = {}
        
        # Cooldowns y asignaciones
        self.last_purchase_tick = 0
        self.shop_unit_id = None
        self.attacking = False
        
        print("[EasyBot] Instanciado. Estrategia: equilibrada (recolectar y atacar).")

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

        total_units = len(state.my_units)
        collectors = state.get_my_collectors()
        num_collectors = len(collectors)
        attackers = state.get_my_attackers()

        # ── 1. GESTION DEL SHOP ──
        # El bot facil necesita una unidad permanente en el shop para poder comprar.
        if not state.shop_authorized and state.shops:
            if self.shop_unit_id is None or self.shop_unit_id not in state.my_units:
                shop_pos = next(iter(state.shops.values()))
                self.shop_unit_id = self._closest_unit_to(shop_pos, state.my_units)
            
            if self.shop_unit_id and self._tick % 5 == 0: # Enviar periodicamente
                shop_pos = next(iter(state.shops.values()))
                tx, ty = int(shop_pos[0]), int(shop_pos[1])
                print(f"[EasyBot] ACCION: Moviendo unidad {self.shop_unit_id} al shop")
                self.net.send_json(JSON_Manager.get_moveorder(self.shop_unit_id, tx, ty))

        # ── 2. COMPRAS (con cooldown) ──
        can_buy = (self._tick - self.last_purchase_tick) >= 15  # Comprar una unidad cada 15 segundos
        if state.shop_authorized and can_buy and total_units < self.MAX_UNITS:
            if num_collectors < self.MAX_COLLECTORS and state.gold >= self.COLLECTOR_COST:
                print(f"[EasyBot] ACCION: Comprando Collector (oro={state.gold})")
                self.net.send_json(JSON_Manager.get_unit_recolectors())
                self.last_purchase_tick = self._tick
            elif num_collectors >= self.MAX_COLLECTORS and state.gold >= self.ATTACKER_COST:
                print(f"[EasyBot] ACCION: Comprando Attacker (oro={state.gold})")
                self.net.send_json(JSON_Manager.get_unit_attacker())
                self.last_purchase_tick = self._tick

        # ── 3. RECOLECCION (FSM) ──
        if state.mines and state.my_base:
            for uid, upos in collectors.items():
                if uid == self.shop_unit_id:
                    continue  # No mover a la unidad que mantiene el shop
                
                cstate = self.collector_state.get(uid, "TO_MINE")
                mine_pos = state.get_nearest_mine(from_pos=upos)
                base_pos = state.my_base
                
                if cstate == "TO_MINE":
                    if mine_pos:
                        dist_to_mine = math.hypot(upos[0] - mine_pos[0], upos[1] - mine_pos[1])
                        if dist_to_mine < 8.0:
                            self.collector_state[uid] = "WAIT_MINE"
                            self.wait_ticks[uid] = 2
                        elif self._tick % 5 == 0:
                            import random
                            ox = random.randint(-4, 4)
                            oy = random.randint(-4, 4)
                            self.net.send_json(JSON_Manager.get_moveorder(uid, int(mine_pos[0]) + ox, int(mine_pos[1]) + oy))
                
                elif cstate == "WAIT_MINE":
                    self.wait_ticks[uid] = self.wait_ticks.get(uid, 0) - 1
                    if self.wait_ticks[uid] <= 0:
                        self.collector_state[uid] = "TO_BASE"
                        
                elif cstate == "TO_BASE":
                    dist_to_base = math.hypot(upos[0] - base_pos[0], upos[1] - base_pos[1])
                    if dist_to_base < 15.0:
                        self.collector_state[uid] = "WAIT_BASE"
                        self.wait_ticks[uid] = 1
                    elif self._tick % 5 == 0:
                        import random
                        ox = random.randint(-6, 6)
                        oy = random.randint(-6, 6)
                        self.net.send_json(JSON_Manager.get_moveorder(uid, int(base_pos[0]) + ox, int(base_pos[1]) + oy))
                        
                elif cstate == "WAIT_BASE":
                    self.wait_ticks[uid] = self.wait_ticks.get(uid, 0) - 1
                    if self.wait_ticks[uid] <= 0:
                        self.collector_state[uid] = "TO_MINE"

        # ── 4. ATAQUE ──
        # Acumular guerreros en la base y enviar ataque al tener 5
        if attackers:
            if not getattr(self, 'attacking', False):
                if len(attackers) >= 5:
                    self.attacking = True
                    print(f"[EasyBot] ACCION: Ejercito listo! Iniciando asedio con {len(attackers)} unidades.")
            else:
                if len(attackers) == 0:
                    self.attacking = False
                    print(f"[EasyBot] ACCION: Ejercito aniquilado. Retirada tactica.")

            if getattr(self, 'attacking', False) and state.enemy_base_id is not None and state.enemy_base:
                enemy_base_pos = state.enemy_base
                target_id = state.enemy_base_id
                
                for uid in attackers:
                    if uid == self.shop_unit_id:
                        continue
                        
                    upos = state.my_units[uid]
                    dist = math.hypot(upos[0] - enemy_base_pos[0], upos[1] - enemy_base_pos[1])
                    
                    if dist < 15.0:
                        # Si esta cerca de la base, le damos la orden de ATAQUE (repetidamente)
                        self.net.send_json(JSON_Manager.attack(target_id, uid))
                    elif self._tick % 10 == 0:
                        # Si esta lejos, actualizamos su ruta de acercamiento cada 10s
                        import random
                        ox = random.randint(-4, 4)
                        oy = random.randint(-4, 4)
                        tx, ty = int(enemy_base_pos[0]) + ox, int(enemy_base_pos[1]) + oy
                        self.net.send_json(JSON_Manager.get_moveorder(uid, tx, ty))
            else:
                # Si no estamos atacando, distribuirlos un poco alrededor de la base para que no se apilen
                if self._tick % 10 == 0 and state.my_base:
                    import random
                    for uid in attackers:
                        if uid == self.shop_unit_id:
                            continue
                        ox = random.randint(-3, 3)
                        oy = random.randint(-3, 3)
                        tx, ty = int(state.my_base[0]) + ox, int(state.my_base[1]) + oy
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
