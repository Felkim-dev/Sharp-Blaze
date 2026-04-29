import itertools
import os
import secrets

from .matchSpawner import MatchSpawner, MatchParticipant, MatchEndpoint

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
