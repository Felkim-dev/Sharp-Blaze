import asyncio
import json
import contextlib

from collections import deque
from .matchSpawner import MatchParticipant,MatchSpawner, MatchEndpoint


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
