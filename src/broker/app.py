from __future__ import annotations

import asyncio
import os

from .matchSpawner import MatchSpawner
from .stubMatchSpawner import StubMatchSpawner
from .dockerMatchSpawner import DockerMatchSpawner
from .brokerServer import BrokerServer

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