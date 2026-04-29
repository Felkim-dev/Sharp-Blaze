import asyncio

from dataclasses import dataclass

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