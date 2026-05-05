import os
import itertools
import asyncio
import secrets


from .matchSpawner import MatchEndpoint,MatchParticipant, MatchSpawner


try:
    import docker
except ImportError:  # pragma: no cover - optional dependency for local development
    docker = None

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

        # Explicitly bind to the specific host IP (self._ip) rather than 0.0.0.0.
        # This is critical for UDP over Tailscale/VPNs: if we bind to 0.0.0.0,
        # docker-proxy may reply using the host's default interface IP instead
        # of the VPN IP. The client's socket will drop the mismatched source IP.
        ports = {
            f"{self._tcp_port}/tcp": (self._ip,),
            f"{self._udp_port}/udp": (self._ip,),
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