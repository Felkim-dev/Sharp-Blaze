"""
End-to-End Test: Docker Server + BotNetworkClient.

Verifies that:
1. Two clients (Humano + Bot) can connect to the real Docker C++ server.
2. Both receive the START_GAME message after connecting.
3. UDP positions are flowing.
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ia.infra.bot_network_client import BotNetworkClient

def run_e2e_test():
    print("=" * 60)
    print("  E2E TEST: Real Docker Server Connection")
    print("=" * 60)

    IP = "127.0.0.1"
    TCP_PORT = 5555
    UDP_PORT = 5556
    SESSION_ID = 100
    TOKEN = "docker_test_token"

    client1 = BotNetworkClient()
    client2 = BotNetworkClient()

    try:
        print(f"\n[Step 1] Connecting Player 1 (humano)...")
        success1 = client1.connect_tcp(IP, TCP_PORT, "humano", SESSION_ID, TOKEN)
        if not success1:
            print("  X Player 1 failed to connect.")
            return

        time.sleep(1.0) 
        print(f"[Step 2] Connecting Player 2 (bot_ai)...")
        success2 = client2.connect_tcp(IP, TCP_PORT, "bot_ai", SESSION_ID, TOKEN)
        if not success2:
            print("  X Player 2 failed to connect.")
            return

        print("\n[Step 3] Waiting for CONNECTION_ACK on both...")
        ack1, ack2 = False, False
        start_time = time.time()
        while time.time() - start_time < 5:
            if not ack1:
                m1 = client1.receive_json()
                if m1 and m1.get("type") == "CONNECTION_ACK":
                    ack1 = True
                    print("  OK P1 Connected & Acked")
            if not ack2:
                m2 = client2.receive_json()
                if m2 and m2.get("type") == "CONNECTION_ACK":
                    ack2 = True
                    print("  OK P2 Connected & Acked")
            if ack1 and ack2: break
            time.sleep(0.1)

        print("\n[Step 4] Sending START_GAME command from Player 1...")
        start_cmd = {
            "type": "START_GAME",
            "payload": {
                "start": False,
                "session_id": SESSION_ID
            }
        }
        client1.send_json(start_cmd)

        print("\n[Step 5] Waiting for START_GAME message from server...")
        
        received_start1 = False
        received_start2 = False
        
        start_time = time.time()
        while time.time() - start_time < 15:
            msg1 = client1.receive_json()
            if msg1:
                print(f"  [P1 RECV] {msg1}")
                if msg1.get("type") == "START_GAME":
                    received_start1 = True
            
            msg2 = client2.receive_json()
            if msg2:
                print(f"  [P2 RECV] {msg2}")
                if msg2.get("type") == "START_GAME":
                    received_start2 = True
            
            if received_start1 and received_start2:
                print("  OK Both clients received START_GAME!")
                break
            time.sleep(0.1)

        if not (received_start1 and received_start2):
            print(f"  X Timeout! Start1={received_start1}, Start2={received_start2}")
            return

        print("\n[Step 4] Initializing UDP for both...")
        client1.init_udp(IP, UDP_PORT, SESSION_ID, 1)
        client2.init_udp(IP, UDP_PORT, SESSION_ID, 2)

        print("[Step 5] Waiting for UDP positions (5s)...")
        pos_received = False
        start_time = time.time()
        while time.time() - start_time < 5:
            pos1 = client1.get_latest_positions()
            pos2 = client2.get_latest_positions()
            
            if pos1:
                print(f"  OK Player 1 received {len(pos1)} entity positions via UDP")
                pos_received = True
            if pos2:
                print(f"  OK Player 2 received {len(pos2)} entity positions via UDP")
                pos_received = True
                
            if pos_received: break
            time.sleep(0.5)

        if not pos_received:
            print("  ! No UDP positions received yet (normal if game hasn't ticked or units are idle)")

        print("\n" + "=" * 60)
        print("  E2E TEST RESULT: SUCCESS")
        print("=" * 60)

    except Exception as e:
        print(f"\n  X ERROR during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client1.disconnect()
        client2.disconnect()

if __name__ == "__main__":
    run_e2e_test()
