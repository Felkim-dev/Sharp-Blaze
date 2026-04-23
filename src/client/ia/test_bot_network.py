# ia/test_bot_network.py
# Script de prueba aislado para BotNetworkBridge.
# Ejecutar desde la raiz del proyecto:
#   .\sharp_blaze_venv\Scripts\python.exe src/client/ia/test_bot_network.py
#
# Requiere: servidor C++ corriendo en Config.SERVER_IP:Config.TCP_PORT_SERVER
# Si el servidor NO esta corriendo, el test fallara con [ERROR] de conexion
# y te lo dira claramente.

import sys
import time

# Agregar src/client al path para poder importar los modulos del proyecto
sys.path.insert(0, "src/client")

from ia.bot_network import BotNetworkBridge
from utils.config import Config

# ─────────────────────────────────────────
#  CONFIGURACION DEL TEST
# ─────────────────────────────────────────
BOT_NICKNAME   = "BOT_TEST"
WAIT_SECONDS   = 5    # Cuantos segundos esperar mensajes del servidor


def separator(title=""):
    print()
    print("=" * 50)
    if title:
        print(f"  {title}")
        print("=" * 50)


def test_nivel_1_sin_servidor():
    """Prueba que no necesita el servidor."""
    separator("NIVEL 1: Sin servidor")

    bridge = BotNetworkBridge()

    assert bridge.connected == False,      "FALLO: connected deberia ser False"
    assert bridge._udp_running == False,   "FALLO: udp_running deberia ser False"
    assert bridge.get_positions() == {},   "FALLO: positions deberia estar vacio"
    assert bridge.receive_json() is None,  "FALLO: receive_json deberia ser None"

    bridge.disconnect()  # No debe explotar aunque no hay conexion

    print()
    print("[TEST NIVEL 1] PASO [OK]")


def test_nivel_2_con_servidor():
    """
    Prueba que requiere el servidor C++ corriendo.
    Intenta conectarse, espera mensajes, y desconecta.
    """
    separator("NIVEL 2: Con servidor")
    print(f"  Servidor objetivo: {Config.SERVER_IP}:{Config.TCP_PORT_SERVER}")
    print(f"  Nickname del bot:  {BOT_NICKNAME}")
    print()

    bridge = BotNetworkBridge()

    # ── TEST 2.1: Conexion TCP ────────────────────────────────
    print("--- TEST 2.1: Intentando conexion TCP ---")
    success = bridge.connect(BOT_NICKNAME)

    if not success:
        print()
        print("[TEST NIVEL 2] NO PASO - No se pudo conectar al servidor.")
        print("  Verifica que el servidor C++ este corriendo en:")
        print(f"  {Config.SERVER_IP}:{Config.TCP_PORT_SERVER}")
        return

    print(f"  bridge.connected = {bridge.connected}")
    assert bridge.connected == True, "FALLO: deberia estar conectado"
    print("[TEST 2.1] PASO [OK]")

    # ── TEST 2.2: Recibir mensajes del servidor ───────────────
    print()
    print(f"--- TEST 2.2: Esperando mensajes del servidor ({WAIT_SECONDS}s) ---")
    print("  (El servidor deberia enviar QUEUE_STATUS o CONNECTION_ACK)")

    deadline = time.time() + WAIT_SECONDS
    messages_received = []

    while time.time() < deadline:
        msg = bridge.receive_json()
        if msg:
            messages_received.append(msg)
            print(f"  >> Mensaje recibido: type='{msg.get('type')}'")
        time.sleep(0.1)

    print(f"  Total mensajes recibidos: {len(messages_received)}")

    if messages_received:
        print("[TEST 2.2] PASO [OK] - El servidor respondio")
    else:
        print("[TEST 2.2] ADVERTENCIA - No llegaron mensajes en", WAIT_SECONDS, "segundos")
        print("  Esto puede ser normal si el servidor requiere")
        print("  que haya 2 jugadores antes de responder.")

    # ── TEST 2.3: Desconexion limpia ─────────────────────────
    print()
    print("--- TEST 2.3: Desconexion ---")
    bridge.disconnect()
    assert bridge.connected == False, "FALLO: deberia estar desconectado"
    print("[TEST 2.3] PASO [OK]")

    separator("RESUMEN NIVEL 2")
    print(f"  Mensajes recibidos: {len(messages_received)}")
    for i, m in enumerate(messages_received):
        print(f"  [{i+1}] {m}")


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    separator("INICIO DE TESTS - bot_network.py")
    print(f"  Python: {sys.version}")

    test_nivel_1_sin_servidor()
    test_nivel_2_con_servidor()

    separator("FIN DE TESTS")
