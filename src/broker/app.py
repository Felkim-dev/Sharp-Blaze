from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import os
import secrets
from collections import deque
from dataclasses import dataclass

try:
    import docker
except ImportError:  # pragma: no cover - optional dependency for local development
    docker = None


@dataclass
class MatchParticipant:
    player_id: str
    writer: asyncio.StreamWriter
    internal_player_id: int


@dataclass
class MatchEndpoint:
    session_id: int
    token: str
    ip: str
    port: int
    udp_port: int


class MatchSpawner:
    async def spawn(self, left: MatchParticipant, right: MatchParticipant) -> MatchEndpoint:
        raise NotImplementedError


class StubMatchSpawner(MatchSpawner):
    def __init__(self) -> None:
        self._session_ids = itertools.count(int(os.environ.get("BROKER_SESSION_START", "1")))
        self._token_prefix = os.environ.get("BROKER_TOKEN_PREFIX", "stub")
        self._ip = os.environ.get("BROKER_STUB_IP", "127.0.0.1")
        self._tcp_port = int(os.environ.get("BROKER_STUB_TCP_PORT", "5555"))
        self._udp_port = int(os.environ.get("BROKER_STUB_UDP_PORT", "5556"))

    async def spawn(self, left: MatchParticipant, right: MatchParticipant) -> MatchEndpoint:
        session_id = next(self._session_ids)
        token = f"{self._token_prefix}-{secrets.token_hex(8)}"
        return MatchEndpoint(
            session_id=session_id,
            token=token,
            ip=self._ip,
            port=self._tcp_port,
            udp_port=self._udp_port,
        )


class DockerMatchSpawner(MatchSpawner):
    def __init__(self) -> None:
        if docker is None:
            raise RuntimeError("docker SDK is not installed")

        self._client = docker.from_env()
        self._image = os.environ.get("BROKER_GAME_IMAGE", "sharp-blaze-server:latest")
        self._ip = os.environ.get("BROKER_GAME_HOST_IP", "127.0.0.1")
        self._tcp_port = int(os.environ.get("BROKER_GAME_TCP_PORT", "5555"))
        self._udp_port = int(os.environ.get("BROKER_GAME_UDP_PORT", "5556"))
        self._network = os.environ.get("BROKER_GAME_NETWORK")
        self._session_ids = itertools.count(int(os.environ.get("BROKER_SESSION_START", "1")))

    async def spawn(self, left: MatchParticipant, right: MatchParticipant) -> MatchEndpoint:
        return await asyncio.to_thread(self._spawn_blocking, left, right)

    def _spawn_blocking(self, left: MatchParticipant, right: MatchParticipant) -> MatchEndpoint:
        session_id = next(self._session_ids)
        token = secrets.token_hex(16)

        environment = {
            "SHARP_BLAZE_SESSION_ID": str(session_id),
            "SHARP_BLAZE_SESSION_TOKEN": token,
            "SHARP_BLAZE_PLAYER_ONE": left.player_id,
            "SHARP_BLAZE_PLAYER_TWO": right.player_id,
            "SHARP_BLAZE_TCP_PORT": str(self._tcp_port),
            "SHARP_BLAZE_UDP_PORT": str(self._udp_port),
        }

        ports = {
            f"{self._tcp_port}/tcp": None,
            f"{self._udp_port}/udp": None,
        }

        kwargs = {
            "image": self._image,
            "detach": True,
            "environment": environment,
            "ports": ports,
            "name": f"sharp-blaze-match-{session_id}",
            "remove": True,
        }

        if self._network:
            kwargs["network"] = self._network

        container = self._client.containers.run(**kwargs)
        container.reload()

        port_map = container.attrs["NetworkSettings"]["Ports"]
        tcp_binding = port_map.get(f"{self._tcp_port}/tcp")
        udp_binding = port_map.get(f"{self._udp_port}/udp")

        if not tcp_binding or not udp_binding:
            raise RuntimeError("container did not expose the expected ports")

        return MatchEndpoint(
            session_id=session_id,
            token=token,
            ip=self._ip,
            port=int(tcp_binding[0]["HostPort"]),
            udp_port=int(udp_binding[0]["HostPort"]),
        )


class BrokerServer:
    def __init__(self, spawner: MatchSpawner) -> None:
        self._spawner = spawner
        self._waiting: deque[MatchParticipant] = deque()
        self._waiting_by_writer: dict[asyncio.StreamWriter, MatchParticipant] = {}
        self._lock = asyncio.Lock()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        print(f"[broker] client connected: {peer}")

        try:
            while True:
                raw_line = await reader.readline()
                if not raw_line:
                    break

                try:
                    message = json.loads(raw_line.decode("utf-8"))
                except json.JSONDecodeError:
                    await self._send(writer, self._error_payload("invalid_json"))
                    continue

                action = str(message.get("action") or message.get("type") or "").lower()
                if action == "queue":
                    await self._enqueue_player(writer, str(message.get("player_id", "")).strip())
                elif action == "cancel_queue":
                    await self._remove_waiting(writer)
                    await self._send(writer, self._ack_payload("queue_cancelled"))
                else:
                    await self._send(writer, self._error_payload("unsupported_action"))
        except (ConnectionResetError, asyncio.IncompleteReadError, BrokenPipeError):
            pass
        finally:
            await self._remove_waiting(writer)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            print(f"[broker] client disconnected: {peer}")

    async def _enqueue_player(self, writer: asyncio.StreamWriter, player_id: str) -> None:
        if not player_id:
            await self._send(writer, self._error_payload("missing_player_id"))
            return

        participant = MatchParticipant(player_id=player_id, writer=writer, internal_player_id=0)

        async with self._lock:
            if writer in self._waiting_by_writer:
                return

            self._waiting.append(participant)
            self._waiting_by_writer[writer] = participant
            queue_size = len(self._waiting)

        await self._send(writer, self._queue_payload(player_id, queue_size))
        await self._try_match()

    async def _try_match(self) -> None:
        pairs: list[tuple[MatchParticipant, MatchParticipant]] = []

        async with self._lock:
            while len(self._waiting) >= 2:
                left = self._waiting.popleft()
                right = self._waiting.popleft()
                self._waiting_by_writer.pop(left.writer, None)
                self._waiting_by_writer.pop(right.writer, None)
                pairs.append((left, right))

        for pair in pairs:
            asyncio.create_task(self._spawn_and_notify(pair[0], pair[1]))

    async def _spawn_and_notify(self, left: MatchParticipant, right: MatchParticipant) -> None:
        left.internal_player_id = 1
        right.internal_player_id = 2

        try:
            endpoint = await self._spawner.spawn(left, right)
        except Exception as exc:
            print(f"[broker] failed to spawn match: {exc}")
            await self._send(left.writer, self._error_payload("match_spawn_failed"))
            await self._send(right.writer, self._error_payload("match_spawn_failed"))
            return

        await self._send(left.writer, self._match_payload(left, right, endpoint))
        await self._send(right.writer, self._match_payload(right, left, endpoint))

        print(
            f"[broker] match {endpoint.session_id} ready: {left.player_id} vs {right.player_id} "
            f"at {endpoint.ip}:{endpoint.port}"
        )

    async def _remove_waiting(self, writer: asyncio.StreamWriter) -> None:
        async with self._lock:
            participant = self._waiting_by_writer.pop(writer, None)
            if participant is None:
                return

            self._waiting = deque(item for item in self._waiting if item.writer is not writer)

    async def _send(self, writer: asyncio.StreamWriter, payload: dict) -> None:
        if writer.is_closing():
            return

        try:
            writer.write((json.dumps(payload) + "\n").encode("utf-8"))
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass

    @staticmethod
    def _queue_payload(player_id: str, queue_size: int) -> dict:
        return {
            "action": "queue_status",
            "type": "QUEUE_STATUS",
            "payload": {
                "players_waiting": queue_size,
                "you": player_id,
            },
        }

    @staticmethod
    def _match_payload(me: MatchParticipant, opponent: MatchParticipant, endpoint: MatchEndpoint) -> dict:
        return {
            "action": "match_found",
            "type": "BROKER_MATCH_FOUND",
            "payload": {
                "session_id": endpoint.session_id,
                "global_player_id": me.internal_player_id,
                "you": me.player_id,
                "opponent": opponent.player_id,
                "ip": endpoint.ip,
                "port": endpoint.port,
                "udp_port": endpoint.udp_port,
                "token": endpoint.token,
            },
        }

    @staticmethod
    def _ack_payload(action: str) -> dict:
        return {"action": action, "type": action.upper()}

    @staticmethod
    def _error_payload(reason: str) -> dict:
        return {"action": "error", "type": "ERROR", "payload": {"reason": reason}}


async def main() -> None:
    use_stub = os.environ.get("BROKER_ALLOW_STUB", "0") == "1"

    if use_stub:
        spawner: MatchSpawner = StubMatchSpawner()
    else:
        try:
            spawner = DockerMatchSpawner()
        except Exception as exc:
            print(f"[broker] docker spawner unavailable: {exc}")
            spawner = StubMatchSpawner()

    broker = BrokerServer(spawner)
    host = os.environ.get("BROKER_HOST", "0.0.0.0")
    port = int(os.environ.get("BROKER_PORT", "6000"))

    server = await asyncio.start_server(broker.handle_client, host, port)
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"[broker] listening on {addresses}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())