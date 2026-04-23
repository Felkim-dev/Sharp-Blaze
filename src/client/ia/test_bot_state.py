# ia/test_bot_state.py
# Script de prueba para BotState.
# No requiere servidor. Simula los mensajes REALES del servidor
# segun clientProtocol.cpp.
#
# Ejecutar desde la raiz del proyecto:
#   python src/client/ia/test_bot_state.py

import sys
sys.path.insert(0, "src/client")

from ia.bot_state import BotState, classify_entity


def separator(title=""):
    print()
    print("=" * 50)
    if title:
        print(f"  {title}")
        print("=" * 50)


# ─── TEST 1: Clasificacion de IDs ─────────────────────────
separator("TEST 1: Clasificacion de IDs")

casos = [
    (100,   "human_structure"),
    (1500,  "human_attacker"),
    (3500,  "human_collector"),
    (5000,  "bot_structure"),
    (6500,  "bot_attacker"),
    (8500,  "bot_collector"),
    (10000, "mine"),
    (11000, "shop"),
    (99999, "unknown"),
]

todos_ok = True
for entity_id, esperado in casos:
    resultado = classify_entity(entity_id)
    ok = resultado == esperado
    todos_ok = todos_ok and ok
    estado = "[OK]" if ok else "[FALLO]"
    print(f"  {estado} ID {entity_id:6d} -> '{resultado}' (esperado: '{esperado}')")

assert todos_ok, "Fallo en clasificacion de IDs"
print("[TEST 1] PASO [OK]")


# ─── TEST 2: apply_start_game ─────────────────────────────
separator("TEST 2: Carga del estado inicial (START_GAME)")

state = BotState()

# Simulamos el payload real que envia BuildMatchStartResponse() del servidor
# Nota: el servidor envia coordenadas en espacio de GRID (no world)
fake_start_game = {
    "gold": 500,
    "units": {
        # Unidades del humano (player 1)
        "1000": [9, 91],    # human_attacker  (grid coords)
        "3002": [7, 89],    # human_collector
        # Unidades del bot (player 2)
        "6000": [91, 9],    # bot_attacker
        "8002": [93, 11],   # bot_collector
    },
    "structures": {
        "100":   [6, 94],   # human_structure (base humano)
        "5000":  [94, 6],   # bot_structure   (base bot)
        "10000": [40, 20],  # mine
        "10001": [20, 40],  # mine
        "11000": [50, 50],  # shop
    }
}

state.apply_start_game(fake_start_game)

assert state.gold == 500,                              "FALLO: oro incorrecto"
assert 6000 in state.my_units,                         "FALLO: bot_attacker no registrado"
assert 8002 in state.my_units,                         "FALLO: bot_collector no registrado"
assert 1000 in state.enemy_units,                      "FALLO: human_attacker no registrado"
assert 3002 in state.enemy_units,                      "FALLO: human_collector no registrado"
assert state.my_base is not None,                      "FALLO: base del bot no encontrada"
assert state.enemy_base is not None,                   "FALLO: base del humano no encontrada"
assert len(state.mines) == 2,                          "FALLO: deberia haber 2 minas"
assert len(state.shops) == 1,                          "FALLO: deberia haber 1 shop"

print("[TEST 2] PASO [OK]")


# ─── TEST 3: Mensajes TCP del servidor (protocolo real) ───
separator("TEST 3: Mensajes TCP reales del servidor")

# RESOURCES — BuildResourcesResponse() linea 267 de clientProtocol.cpp
state.apply_tcp_message({"type": "RESOURCES", "payload": {"new_balance": 650}})
assert state.gold == 650, "FALLO: oro no actualizado"
print("  [OK] RESOURCES: oro actualizado a 650")

# SHOP_AUTHORIZATION — BuildShopAuthorizationResponse() linea 250
# Nota: el servidor envia "SHOP_AUTHORIZATION" (con Z)
state.apply_tcp_message({
    "type": "SHOP_AUTHORIZATION",
    "payload": {
        "player_id":  2,
        "authorized": True,
        "shop_id":    11000,
        "unit_id":    6000
    }
})
assert state.shop_authorized == True, "FALLO: shop no autorizado"
assert state.shop_unit_id == 6000,    "FALLO: unit_id del shop incorrecto"
print("  [OK] SHOP_AUTHORIZATION: autorizado con unidad 6000")

# ENTITY_DESTROYED — BuildEntityDestroyedResponse() linea 332
# Nota: campo es "entity_id", no "unit_id"
state.apply_tcp_message({
    "type": "ENTITY_DESTROYED",
    "payload": {
        "session_id":        1,
        "entity_id":         1000,   # humano destruido
        "owner_player_id":   1,
        "attacker_player_id": 2
    }
})
assert 1000 not in state.enemy_units, "FALLO: entidad enemiga no fue eliminada"
print("  [OK] ENTITY_DESTROYED: entidad 1000 eliminada de enemy_units")

# UNIT_DAMAGED — BuildUnitDamagedResponse() linea 306
state.apply_tcp_message({
    "type": "UNIT_DAMAGED",
    "payload": {
        "session_id":         1,
        "target_player_id":   2,
        "target_entity_id":   6000,
        "attacker_player_id": 1,
        "attacker_entity_id": 3002,
        "current_hp":         50,
    }
})
print("  [OK] UNIT_DAMAGED: procesado sin error")

# GAME_OVER — BuildGameOverResponse() linea 351
state.apply_tcp_message({
    "type": "GAME_OVER",
    "payload": {
        "session_id":       1,
        "winner_player_id": 2,
        "reason":           "base_destroyed"
    }
})
print("  [OK] GAME_OVER: procesado sin error")

print("[TEST 3] PASO [OK]")


# ─── TEST 4: Deteccion de unidades via UDP ────────────────
separator("TEST 4: Deteccion de unidades nuevas via UDP")

# El servidor NO envia BUY_UNIT_RESULT ni UNIT_SPAWNED.
# Las unidades nuevas simplemente APARECEN en el stream UDP.
# apply_positions() las detecta por su ID y las registra.

posiciones_udp = {
    6000: (1000.0, 500.0),   # bot_attacker conocido → actualizar posicion
    8002: (2000.0, 1000.0),  # bot_collector conocido → actualizar posicion
    3002: (300.0, 4500.0),   # human_collector conocido → actualizar posicion
    8003: (2500.0, 2000.0),  # bot_collector NUEVO (recien comprado) → registrar
    6001: (4600.0, 350.0),   # bot_attacker NUEVO → registrar
    1001: (400.0, 4400.0),   # human_attacker NUEVO → registrar como enemigo
}

state.apply_positions(posiciones_udp)

assert state.my_units[6000]    == (1000.0, 500.0),   "FALLO: posicion bot_attacker incorrecta"
assert state.my_units[8002]    == (2000.0, 1000.0),  "FALLO: posicion bot_collector incorrecta"
assert state.enemy_units[3002] == (300.0, 4500.0),   "FALLO: posicion human_collector incorrecta"
assert 8003 in state.my_units,                        "FALLO: bot_collector nuevo no detectado"
assert 6001 in state.my_units,                        "FALLO: bot_attacker nuevo no detectado"
assert 1001 in state.enemy_units,                     "FALLO: human_attacker nuevo no detectado"

print("  [OK] Posiciones actualizadas y nuevas unidades detectadas")
print("[TEST 4] PASO [OK]")


# ─── TEST 5: Helpers de consulta ──────────────────────────
separator("TEST 5: Helpers de consulta")

collectors = state.get_my_collectors()
attackers  = state.get_my_attackers()

print(f"  Collectors del bot: {list(collectors.keys())}")
print(f"  Attackers del bot:  {list(attackers.keys())}")

assert 8002 in collectors, "FALLO: collector 8002 no encontrado"
assert 8003 in collectors, "FALLO: collector 8003 no encontrado"
assert 6000 in attackers,  "FALLO: attacker 6000 no encontrado"
assert 6001 in attackers,  "FALLO: attacker 6001 no encontrado"

mine_cercana = state.get_nearest_mine(from_pos=state.my_base)
assert mine_cercana is not None, "FALLO: no encontro mina cercana a la base"
print(f"  Mina mas cercana a la base del bot {state.my_base}: {mine_cercana}")

print("[TEST 5] PASO [OK]")


# ─── RESUMEN FINAL ────────────────────────────────────────
separator("RESUMEN FINAL")
print(state.summary())
print()
print("TODOS LOS TESTS PASARON [OK]")
