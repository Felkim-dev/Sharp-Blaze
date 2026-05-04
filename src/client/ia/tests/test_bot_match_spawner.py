"""Quick verification that BotMatchSpawner imports and handles missing Docker gracefully."""
import sys
sys.path.insert(0, "src/client/ia")

from bot_match_spawner import BotMatchSpawner

print("[OK] BotMatchSpawner imported successfully")
print(f"[OK] Session counter starts at: {BotMatchSpawner._session_counter}")

print("\nAttempting instantiation (Docker SDK may not be installed):")
try:
    spawner = BotMatchSpawner()
    print(f"[OK] Docker daemon connected!")
    print(f"     Image: {spawner._image}")
    print(f"     Host IP: {spawner._host_ip}")
    print(f"     Internal TCP: {spawner._internal_tcp_port}")
    print(f"     Internal UDP: {spawner._internal_udp_port}")
except RuntimeError as e:
    print(f"[EXPECTED] {e}")

print("\nAll checks passed - module is ready.")
