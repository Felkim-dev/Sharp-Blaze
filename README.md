# Sharp Blaze | Distributed RTS Simulator 🎮🛰️

**Sharp Blaze** is a real-time strategy (RTS) game built as a multidisciplinary integration platform covering five core Computer Science subjects. Two players compete on a shared grid world managing units and resources, with all game state synchronized through an authoritative C++ server. The system is fully containerized and uses a broker service for automatic matchmaking.

---

## 📖 Project Overview

The architecture is composed of three independent services that work together:

1. **Broker** (`src/broker`) — A Python matchmaking server (port **6000**). Clients connect here to enter the matchmaking queue. When two players are waiting, the broker automatically spawns a dedicated game-server Docker container and sends both clients the connection details.

2. **Game Server** (`src/server`) — An authoritative C++ server. Handles TCP (port **5555**) for game logic messages and UDP (port **5556**) for high-frequency position broadcasts. Built with CMake and packaged as a Docker image (`sharp-blaze-server:latest`).

3. **Client** (`src/client`) — A Python/Pygame application (1280×720). Manages all game screens (Main → Join → Lobby → Connecting → Game), sends player input over TCP, and receives real-time position updates over UDP.

### Connection Flow
```
Client ──TCP──▶ Broker (6000)
                  │ match found → spawns container
                  │
Client ◀──TCP── Broker (server IP:TCP port)
                  │
Client ──TCP──▶ Game Server (5555)
Client ──UDP──▶ Game Server (5556)
```

---

## 🎓 Academic Integration

| Subject | Implementation |
|---|---|
| **Distributed Systems** | Authoritative Client-Server over POSIX sockets (TCP + UDP) in C++. Session management with multi-threading and spatial grid synchronization. |
| **Artificial Intelligence** | A* pathfinder (`PathFinder.cpp`) integrated server-side for unit navigation. Client-side AI module scaffolded under `src/client/ia/`. |
| **Optimization Methods** | Simplex-based strategic decision engine scaffolded under `src/client/optimization/`. |
| **Service Administration** | Full containerization with Docker and Docker Compose. The broker manages dynamic container lifecycle via the Docker SDK. |
| **Software Engineering** | Agile/Scrum workflow with Git, formal technical documentation in `docs/`, and modular screen/component architecture in the client. |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Game Server | C++17, CMake, POSIX Sockets |
| Broker | Python 3.12, asyncio, Docker SDK |
| Client | Python 3.12, Pygame-CE 2.5.7 |
| Infrastructure | Docker, Docker Compose |
| Networking | TCP (game logic) + UDP (position updates) |

---

## 🚀 Quick Start — Docker (Recommended)

> **Requirements:** Docker Engine with access to the Docker socket.

```bash
# 1. Clone the repository
git clone https://github.com/Felkim-dev/Sharp-Blaze.git
cd Sharp-Blaze

# 2. Build the game-server image and start the broker
docker-compose up --build
```

The broker will be listening on port **6000**. Start the client separately on any machine (see below).

---

## ▶️ Running the Client

> **Requirements:** Python 3.12+

```bash
cd src/client

# Install dependencies
pip install -r requirements.txt

# Run the client
python main.py
```

The client connects to the broker at `127.0.0.1:6000` by default. To connect to a remote broker, edit `src/client/utils/config.py`:

```python
BROKER_IP   = "127.0.0.1"   # Change to the broker's IP address
BROKER_PORT = 6000
```

---

## 🖥️ Running the Server Manually (without Docker)

### Broker

> **Requirements:** Python 3.12+, Docker daemon running

```bash
cd src/broker

# Install dependencies
pip install -r requirements.txt

# Start the broker
python app.py
```

### Game Server

> **Requirements:** CMake 3.x, GCC/Clang with C++17 support

```bash
cd src/server

# Configure and build
cmake -S Makefile -B build/linux -DCMAKE_BUILD_TYPE=Release
cmake --build build/linux -j

# Run the server
./build/linux/sharp_blaze_server
```

The server reads its configuration from environment variables:

| Variable | Default | Description |
|---|---|---|
| `SHARP_BLAZE_TCP_PORT` | `5555` | TCP listening port |
| `SHARP_BLAZE_SESSION_ID` | `0` | Session ID for dedicated instances |
| `SHARP_BLAZE_SESSION_TOKEN` | — | Auth token issued by the broker |

---

## 📁 Project Structure

```
Sharp-Blaze/
├── docker-compose.yml          # Starts the broker; builds game-server image
├── src/
│   ├── broker/                 # Python matchmaking service (port 6000)
│   │   ├── app.py
│   │   └── Dockerfile
│   ├── server/                 # C++ authoritative game server (TCP 5555 / UDP 5556)
│   │   ├── main.cpp
│   │   ├── network/            # TCP session management
│   │   ├── transport/          # UDP dispatcher
│   │   ├── infrastructure/     # Spatial grid
│   │   ├── include/            # Header files
│   │   └── Dockerfile
│   ├── client/                 # Python/Pygame client
│   │   ├── main.py
│   │   ├── ui/                 # Screens: Main, Join, Lobby, Connecting, Game
│   │   ├── network/            # TCP + UDP network manager
│   │   ├── engine/             # World grid and camera
│   │   ├── entities/           # Units, structures, projectiles
│   │   ├── ia/                 # AI module (A* / FSM)
│   │   ├── optimization/       # Simplex decision engine
│   │   └── utils/              # Config, JSON helpers
│   └── config/
│       └── combat_stats.json   # Shared unit stats
└── docs/                       # Architecture diagrams, sprint records, requirements
```

---

## 📅 Development Roadmap (12 Weeks)

| Sprint | Focus |
|---|---|
| S1–S2 | Infrastructure: initial handshake, broker, Docker setup |
| S3–S4 | World & Movement: shared grid, TCP/UDP sync, camera |
| S5–S6 | Game Logic: resource system, combat, health management |
| S7–S8 | Tactical AI: A* pathfinding server-side integration |
| S9–S10 | Strategic Optimization: Simplex model for bot decisions |
| S11–S12 | QA & Polish: load testing, bug fixes, final documentation |

---

## 👥 Contributors

- **Steve Tene** — Lead Developer A · Backend, Networking & Infrastructure
- **Felipe Quilumbango** — Lead Developer B · Frontend
- **Kevin Sánchez** — Lead Developer C · AI Implementation

---
