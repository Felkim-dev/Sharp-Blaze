"""
Test suite for BotNetworkClient.

Tests the bot network client against a mock TCP/UDP server to verify:
1. TCP connection + INITIAL_CONNECT message format
2. TCP send_json (newline-delimited JSON)
3. TCP receive_json (buffer + newline split)
4. UDP hello message format (12-byte binary)
5. UDP position packet reception (12-byte <iff)
6. Grid-to-world coordinate conversion
7. Disconnect / cleanup
"""

import sys
import os
import socket
import json
import struct
import threading
import time

# Add paths so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from bot_network_client import BotNetworkClient


# ====================================================================
#  MOCK SERVERS
# ====================================================================

class MockTCPServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", 0))
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(1)
        self.client_conn = None
        self.received_data = ""

    def accept_one(self, timeout=3.0):
        self.server_socket.settimeout(timeout)
        self.client_conn, addr = self.server_socket.accept()
        return addr

    def read_message(self, timeout=2.0) -> dict:
        self.client_conn.settimeout(timeout)
        data = self.client_conn.recv(4096).decode("utf-8")
        self.received_data += data
        if "\n" in self.received_data:
            line, self.received_data = self.received_data.split("\n", 1)
            return json.loads(line)
        return None

    def send_message(self, data: dict):
        message = json.dumps(data) + "\n"
        self.client_conn.send(message.encode("utf-8"))

    def close(self):
        if self.client_conn:
            self.client_conn.close()
        self.server_socket.close()


class MockUDPServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(("127.0.0.1", 0))
        self.port = self.server_socket.getsockname()[1]
        self.last_hello_from = None

    def receive_hello(self, timeout=3.0) -> tuple:
        self.server_socket.settimeout(timeout)
        data, addr = self.server_socket.recvfrom(1024)
        self.last_hello_from = addr
        if len(data) == 12:
            session_id, player_id = struct.unpack("!ii", data[:8])
            checksum = struct.unpack("!I", data[8:12])[0]
            return session_id, player_id, checksum, addr
        return None

    def send_position(self, entity_id: int, grid_x: float, grid_y: float, addr=None):
        target = addr or self.last_hello_from
        packet = struct.pack("<iff", entity_id, grid_x, grid_y)
        self.server_socket.sendto(packet, target)

    def close(self):
        self.server_socket.close()


# ====================================================================
#  TESTS
# ====================================================================

def test_tcp_connect_and_initial_message():
    print("\n--- Test 1: TCP Connect + INITIAL_CONNECT ---")
    
    server = MockTCPServer()
    bot = BotNetworkClient()

    connect_thread = threading.Thread(
        target=bot.connect_tcp,
        args=("127.0.0.1", server.port, "test_bot", 42, "abc123"),
    )
    connect_thread.start()
    server.accept_one()
    msg = server.read_message()
    connect_thread.join(timeout=3)

    assert bot.connected, "Bot should be connected"
    assert bot.connection_status == "IDLE", f"Expected IDLE, got {bot.connection_status}"
    assert msg is not None, "Should have received a message"
    assert msg["type"] == "INITIAL_CONNECT", f"Expected INITIAL_CONNECT, got {msg['type']}"
    assert msg["payload"]["player_id"] == "test_bot"
    assert msg["payload"]["session_id"] == 42
    assert msg["payload"]["match_token"] == "abc123"
    assert msg["payload"]["client_version"] == "0.0.1"
    assert msg["payload"]["is_ready"] == True

    print("  OK TCP connected successfully")
    print(f"  OK INITIAL_CONNECT format correct: {json.dumps(msg, indent=2)}")

    bot.disconnect()
    server.close()


def test_tcp_send_json():
    print("\n--- Test 2: TCP send_json ---")
    
    server = MockTCPServer()
    bot = BotNetworkClient()

    t = threading.Thread(target=bot.connect_tcp,
                         args=("127.0.0.1", server.port, "bot", 1, "tok"))
    t.start()
    server.accept_one()
    server.read_message()
    t.join(timeout=3)

    buy_cmd = {
        "type": "BUY_UNIT",
        "payload": {"unit_type": "Attacker", "quantity": 1}
    }
    bot.send_json(buy_cmd)
    msg = server.read_message()
    assert msg["type"] == "BUY_UNIT"
    assert msg["payload"]["unit_type"] == "Attacker"
    print(f"  OK BUY_UNIT sent correctly: {msg}")

    move_cmd = {
        "type": "MOVE_ORDER",
        "payload": {"unit_id": 1000, "target_x": 50, "target_y": 80}
    }
    bot.send_json(move_cmd)
    msg = server.read_message()
    assert msg["type"] == "MOVE_ORDER"
    assert msg["payload"]["unit_id"] == 1000
    print(f"  OK MOVE_ORDER sent correctly: {msg}")

    bot.disconnect()
    server.close()


def test_tcp_receive_json():
    print("\n--- Test 3: TCP receive_json ---")
    
    server = MockTCPServer()
    bot = BotNetworkClient()

    t = threading.Thread(target=bot.connect_tcp,
                         args=("127.0.0.1", server.port, "bot", 1, "tok"))
    t.start()
    server.accept_one()
    server.read_message()
    t.join(timeout=3)

    server.send_message({
        "type": "BUY_UNIT_RESULT",
        "status": "accepted",
        "payload": {"unit_id": 1000, "spawn_x": 300, "spawn_y": 4700, "new_balance": 400}
    })
    time.sleep(0.1)

    msg = bot.receive_json()
    assert msg is not None, "Should have received a message"
    assert msg["type"] == "BUY_UNIT_RESULT"
    assert msg["status"] == "accepted"
    assert msg["payload"]["unit_id"] == 1000
    print(f"  OK BUY_UNIT_RESULT received correctly: {msg}")

    server.send_message({"type": "RESOURCES", "payload": {"new_balance": 350}})
    server.send_message({"type": "UNIT_SPAWNED", "payload": {"unit_id": 6000}})
    time.sleep(0.1)

    msg1 = bot.receive_json()
    msg2 = bot.receive_json()
    assert msg1["type"] == "RESOURCES", f"Expected RESOURCES, got {msg1}"
    assert msg2["type"] == "UNIT_SPAWNED", f"Expected UNIT_SPAWNED, got {msg2}"
    print(f"  OK Batched messages received: {msg1['type']}, {msg2['type']}")

    bot.disconnect()
    server.close()


def test_udp_hello_format():
    print("\n--- Test 4: UDP Hello Format ---")
    
    udp_server = MockUDPServer()
    bot = BotNetworkClient()

    t = threading.Thread(
        target=bot.init_udp,
        args=("127.0.0.1", udp_server.port, 42, 2),
    )
    t.start()
    result = udp_server.receive_hello()
    assert result is not None, "Should have received hello"
    
    session_id, player_id, checksum, addr = result
    assert session_id == 42, f"Expected session_id=42, got {session_id}"
    assert player_id == 2, f"Expected player_id=2, got {player_id}"

    header = struct.pack("!ii", 42, 2)
    expected_checksum = 0
    for b in header:
        expected_checksum ^= b
    assert checksum == expected_checksum, f"Checksum mismatch: {checksum} != {expected_checksum}"

    print(f"  OK Hello format correct: session={session_id}, player={player_id}, checksum={checksum}")

    udp_server.send_position(1000, 5.0, 90.0, addr)
    t.join(timeout=5)

    bot.disconnect()
    udp_server.close()


def test_udp_position_reception():
    print("\n--- Test 5: UDP Position Reception ---")
    
    udp_server = MockUDPServer()
    bot = BotNetworkClient()

    t = threading.Thread(
        target=bot.init_udp,
        args=("127.0.0.1", udp_server.port, 1, 2),
    )
    t.start()
    result = udp_server.receive_hello()
    addr = result[3]

    udp_server.send_position(1000, 5.0, 90.0, addr)
    udp_server.send_position(3002, 10.0, 85.0, addr)
    udp_server.send_position(6000, 90.0, 5.0, addr)

    time.sleep(0.5)
    t.join(timeout=5)

    positions = bot.get_latest_positions()
    assert 1000 in positions, "Should have entity 1000"
    assert 3002 in positions, "Should have entity 3002"
    assert 6000 in positions, "Should have entity 6000"

    wx, wy = positions[1000][0]
    expected_x = (5.0 * 50) + 25
    expected_y = (90.0 * 50) + 25
    assert wx == expected_x, f"Expected x={expected_x}, got {wx}"
    assert wy == expected_y, f"Expected y={expected_y}, got {wy}"
    print(f"  OK Entity 1000: grid(5,90) -> world({wx},{wy})")

    wx2, wy2 = positions[6000][0]
    expected_x2 = (90.0 * 50) + 25
    expected_y2 = (5.0 * 50) + 25
    assert wx2 == expected_x2
    assert wy2 == expected_y2
    print(f"  OK Entity 6000: grid(90,5) -> world({wx2},{wy2})")

    positions2 = bot.get_latest_positions()
    assert len(positions2) == 0, "Buffer should be empty after get_latest_positions()"
    print("  OK Position buffer cleared after retrieval")

    bot.disconnect()
    udp_server.close()


def test_grid_to_world():
    print("\n--- Test 6: Grid-to-World Conversion ---")
    
    bot = BotNetworkClient()

    test_cases = [
        (0.0, 0.0, 25, 25),
        (5.0, 90.0, 275, 4525),
        (90.0, 5.0, 4525, 275),
        (50.0, 50.0, 2525, 2525),
        (99.0, 99.0, 4975, 4975),
    ]

    for grid_x, grid_y, exp_x, exp_y in test_cases:
        wx, wy = bot._grid_to_world(grid_x, grid_y)
        assert wx == exp_x and wy == exp_y, \
            f"grid({grid_x},{grid_y}) -> expected({exp_x},{exp_y}), got({wx},{wy})"
        print(f"  OK grid({grid_x},{grid_y}) -> world({wx},{wy})")

    bot.disconnect()


def test_disconnect_cleanup():
    print("\n--- Test 7: Disconnect Cleanup ---")
    
    bot = BotNetworkClient()

    bot.connected = True
    bot.connection_status = "IDLE"
    bot.latest_positions = {1000: [(100, 200)]}
    bot.udp_hello_message = b"test"
    bot.udp_session_id = 42
    bot.udp_player_id = 2

    bot.disconnect()

    assert not bot.connected, "Should be disconnected"
    assert bot.connection_status == "IDLE"
    assert len(bot.latest_positions) == 0, "Positions should be cleared"
    assert bot.server_ip is None
    assert bot.udp_port_server is None
    assert bot.udp_hello_message is None
    assert bot.udp_session_id is None
    assert bot.udp_player_id is None
    print("  OK All state cleaned up after disconnect")

    bot.disconnect()
    print("  OK Double disconnect is safe")


if __name__ == "__main__":
    print("=" * 60)
    print("  BotNetworkClient - Test Suite")
    print("=" * 60)

    tests = [
        test_tcp_connect_and_initial_message,
        test_tcp_send_json,
        test_tcp_receive_json,
        test_udp_hello_format,
        test_udp_position_reception,
        test_grid_to_world,
        test_disconnect_cleanup,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n  X FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
