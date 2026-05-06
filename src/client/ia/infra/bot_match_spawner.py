"""
BotMatchSpawner — Spawns a Docker Game Server for Bot Match mode.

Bypasses the broker entirely.  When a player selects "Bot Match" in the UI,
this module directly starts a Game Server container using the Docker SDK,
exactly like the broker's DockerMatchSpawner does, but without the
matchmaking queue.

Prerequisites
─────────────
1. Docker must be running on the host machine.
2. The game server image must be built first:
       docker-compose build game-server-image
   This creates the "sharp-blaze-server:latest" image.
3. The Python Docker SDK must be installed:
       pip install docker

How it works
────────────
1. spawn() creates a container from "sharp-blaze-server:latest"
2. Docker assigns random host ports for TCP (5555) and UDP (5556)
3. Returns a dict with {ip, tcp_port, udp_port, session_id, token}
4. Both the human and bot clients connect to these ports
5. cleanup() stops the container when the match ends

This mirrors the exact Docker setup used in:
    src/broker/dockerMatchSpawner.py (lines 31-77)
"""

import os
import secrets
import time
from typing import Optional, Dict, Any

try:
    import docker
    from docker.errors import DockerException, NotFound, APIError
except ImportError:
    docker = None
    DockerException = Exception
    NotFound = Exception
    APIError = Exception


class BotMatchSpawner:
    """
    Directly spawns a Game Server Docker container for Player vs Bot matches.

    Lifecycle
    ---------
    1. spawner = BotMatchSpawner()          → connects to Docker daemon
    2. info = spawner.spawn(player, bot)    → starts container, returns connection info
    3. ... match plays ...
    4. spawner.cleanup()                    → stops and removes the container
    """

    # Bot match sessions start at 9000 to avoid collisions with broker sessions (1+)
    _session_counter = 9000

    def __init__(self, image: str = None, host_ip: str = None):
        """
        Initialize connection to Docker daemon.

        Args:
            image:   Docker image name (default: "sharp-blaze-server:latest")
            host_ip: IP address the client uses to reach the container
                     (default: "127.0.0.1" for local play)

        Raises:
            RuntimeError: If Docker SDK is not installed or Docker daemon is not running.
        """
        if docker is None:
            raise RuntimeError(
                "Docker SDK is not installed. Run: pip install docker"
            )

        try:
            self._client = docker.from_env()
            # Quick check that the daemon is reachable
            self._client.ping()
        except DockerException as e:
            raise RuntimeError(
                f"Cannot connect to Docker daemon. Is Docker running?\n"
                f"Error: {e}"
            )

        self._image = image or os.environ.get(
            "BOT_GAME_IMAGE", "sharp-blaze-server:latest"
        )
        self._host_ip = host_ip or os.environ.get(
            "BOT_GAME_HOST_IP", "127.0.0.1"
        )

        # Internal TCP/UDP ports inside the container (must match server Dockerfile)
        self._internal_tcp_port = 5555
        self._internal_udp_port = 5556

        # Track the spawned container for cleanup
        self._container = None
        self._session_id: Optional[int] = None
        self._token: Optional[str] = None

    def spawn(self, human_player_id: str = "player",
              bot_player_id: str = "bot_ai") -> Dict[str, Any]:
        """
        Spawn a Game Server container and return connection info.

        Creates a container with the same environment variables that
        the broker's DockerMatchSpawner uses (src/broker/dockerMatchSpawner.py:35-42).

        Args:
            human_player_id: Player name for the human (Player 1)
            bot_player_id:   Player name for the bot (Player 2)

        Returns:
            Dict with connection information:
            {
                "ip": str,           # Host IP to connect to
                "tcp_port": int,     # Mapped TCP port on the host
                "udp_port": int,     # Mapped UDP port on the host
                "session_id": int,   # Unique session identifier
                "token": str,        # Auth token for this session
            }

        Raises:
            RuntimeError: If the container fails to start or expose ports.
        """
        # Generate session ID and token
        BotMatchSpawner._session_counter += 1
        self._session_id = BotMatchSpawner._session_counter
        self._token = secrets.token_hex(16)

        # Environment variables — identical to DockerMatchSpawner
        environment = {
            "SHARP_BLAZE_SESSION_ID": str(self._session_id),
            "SHARP_BLAZE_SESSION_TOKEN": self._token,
            "SHARP_BLAZE_PLAYER_ONE": human_player_id,
            "SHARP_BLAZE_PLAYER_TWO": bot_player_id,
            "SHARP_BLAZE_TCP_PORT": str(self._internal_tcp_port),
            "SHARP_BLAZE_UDP_PORT": str(self._internal_udp_port),
        }

        # Bind mapped ports to the specific host IP (like the broker does).
        # This avoids Docker/proxy returning packets from a different host
        # interface IP (which breaks UDP when multiple interfaces/VPNs exist).
        ports = {
            f"{self._internal_tcp_port}/tcp": (self._host_ip,),
            f"{self._internal_udp_port}/udp": (self._host_ip,),
        }

        container_name = f"sharp-blaze-bot-{self._session_id}"

        print(f"[BotSpawner] Starting container '{container_name}' "
              f"from image '{self._image}'...")

        try:
            self._container = self._client.containers.run(
                image=self._image,
                detach=True,
                environment=environment,
                ports=ports,
                name=container_name,
                remove=True,  # Auto-remove when container stops
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to start game server container.\n"
                f"Have you built the image? Run:\n"
                f"    docker-compose build game-server-image\n"
                f"Error: {e}"
            )

        # Reload to get the assigned host ports
        self._container.reload()

        port_map = self._container.attrs["NetworkSettings"]["Ports"]
        tcp_binding = port_map.get(f"{self._internal_tcp_port}/tcp")
        udp_binding = port_map.get(f"{self._internal_udp_port}/udp")

        if not tcp_binding or not udp_binding:
            self.cleanup()
            raise RuntimeError(
                "Container started but did not expose the expected ports.\n"
                f"Port map: {port_map}"
            )

        host_tcp_port = int(tcp_binding[0]["HostPort"])
        host_udp_port = int(udp_binding[0]["HostPort"])

        print(f"[BotSpawner] Container ready: "
              f"TCP={self._host_ip}:{host_tcp_port}, "
              f"UDP={self._host_ip}:{host_udp_port}, "
              f"session={self._session_id}")

        return {
            "ip": self._host_ip,
            "tcp_port": host_tcp_port,
            "udp_port": host_udp_port,
            "session_id": self._session_id,
            "token": self._token,
        }

    def wait_for_server_ready(self, timeout: float = 5.0,
                              poll_interval: float = 0.3) -> bool:
        """
        Wait until the Game Server inside the container is ready to accept
        TCP connections.

        The C++ server needs ~1-2 seconds to initialize after the container
        starts.  This method polls by attempting a TCP connect.

        Args:
            timeout:       Maximum seconds to wait
            poll_interval: Seconds between connection attempts

        Returns:
            True if server is ready, False if timeout expired.
        """
        import socket

        if self._container is None:
            return False

        # Re-read port info
        self._container.reload()
        port_map = self._container.attrs["NetworkSettings"]["Ports"]
        tcp_binding = port_map.get(f"{self._internal_tcp_port}/tcp")
        if not tcp_binding:
            return False

        host_port = int(tcp_binding[0]["HostPort"])
        deadline = time.time() + timeout

        print(f"[BotSpawner] Waiting for server to be ready on "
              f"{self._host_ip}:{host_port}...")

        while time.time() < deadline:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(poll_interval)
                sock.connect((self._host_ip, host_port))
                sock.close()
                print("[BotSpawner] Server is ready!")
                return True
            except (ConnectionRefusedError, socket.timeout, OSError):
                time.sleep(poll_interval)
            finally:
                try:
                    sock.close()
                except Exception:
                    pass

        print("[BotSpawner] Timeout waiting for server to be ready.")
        return False

    def is_running(self) -> bool:
        """Check if the spawned container is still running."""
        if self._container is None:
            return False

        try:
            self._container.reload()
            return self._container.status == "running"
        except (NotFound, APIError):
            return False

    def get_container_logs(self, tail: int = 50) -> str:
        """
        Get recent logs from the game server container (useful for debugging).

        Args:
            tail: Number of log lines to retrieve

        Returns:
            String with the container's stdout/stderr output.
        """
        if self._container is None:
            return "(no container)"

        try:
            return self._container.logs(tail=tail).decode("utf-8", errors="replace")
        except Exception as e:
            return f"(error reading logs: {e})"

    def cleanup(self) -> None:
        """
        Stop and remove the game server container.

        Safe to call multiple times.  Should be called when:
        - The match ends (GAME_OVER)
        - The player disconnects
        - The application closes
        """
        if self._container is None:
            return

        container_name = self._container.name
        print(f"[BotSpawner] Stopping container '{container_name}'...")

        try:
            self._container.stop(timeout=3)
            print(f"[BotSpawner] Container '{container_name}' stopped.")
        except NotFound:
            # Container already removed (remove=True flag)
            print(f"[BotSpawner] Container '{container_name}' already removed.")
        except Exception as e:
            print(f"[BotSpawner] Error stopping container: {e}")

        self._container = None
