# Sharp Blaze | Distributed RTS Simulator 🎮🛰️

**Sharp Blaze** is a real-time strategy (RTS) simulator designed as a comprehensive integration platform for five core Computer Science disciplines. Developed over a 12-week timeframe by a two-person team in their seventh semester, the project simulates a networked environment where "data packets" compete for resources within a distributed, highly optimized, and containerized ecosystem.

---

## 📖 Project Overview

This project serves as a multidisciplinary integration platform for senior-level computational studies. The system architecture relies on **containerized microservices**, featuring an authoritative server developed in **C++** that manages concurrency and state synchronization via low-level sockets. The **Python-based** client integrates an **Artificial Intelligence** module combining **A*** navigation with a **Finite State Machine (FSM)**. Strategic decision-making is driven by a **Linear Programming (Simplex)** model to ensure optimal resource management.

---

## 🎓 Academic Integration

The project is structured to meet the mandatory requirements for the following subjects:

* **Distributed Systems:** Authoritative Client-Server architecture using Sockets (TCP/UDP) in **C++** to manage state synchronization and concurrency between nodes.
* **Artificial Intelligence:** Implementation of an autonomous adversary bot utilizing **A*** search algorithms for pathfinding and reactive decision-making systems.
* **Optimization Methods:** Economic decision-making engine using the **Simplex Method** to maximize unit production and resource gathering under constraints.
* **Service Administration:** Deployment and orchestration of the entire ecosystem using **Docker** and **Docker Compose** for environment isolation.
* **Software Engineering:** Development following **Agile (Scrum)** methodologies, featuring professional **Git** workflows and formal technical documentation.

---

## 🛠️ Tech Stack

* **Languages:** C++ (Server-side), Python (Client & IA).
* **Graphics Library:** Pygame.
* **Infrastructure:** Docker, Docker Compose.
* **Networking:** Low-level Sockets (POSIX).
* **Math/AI Libraries:** SciPy, NumPy (for Optimization and Pathfinding).

---

## 🚀 Quick Start (Deployment)

To launch the complete environment (Server + 2 Clients + Bot) on any machine with Docker installed:

```bash
# Clone the repository
git clone [https://github.com/your-repo/Unificated_Game.git](https://github.com/your-repo/Unificated_Game.git)

# Enter the directory
cd Unificated_Game

# Build and run the services
docker-compose up --build
```
---
## 📅 Development Roadmap (12 Weeks)
The project is divided into 6 Sprints of 2 weeks each:

1. S1-S2: Infrastructure. Initial Handshake and Dockerization setup.

2. S3-S4: World & Movement. Shared grid implementation and network synchronization.

3. S5-S6: Game Logic. Resource systems, combat mechanics, and health management.

4. S7-S8: Tactical AI. Implementation of intelligent navigation (A*).

5. S9-S10: Strategic Optimization. Integration of the Simplex model for bot decision-making.

6. S11-S12: QA & Polish. Load testing, bug fixing, and final documentation.
---
## 👥 Contributors
- Lead Developer A - Backend, Networking & Infrastructure - Steve Tene.

- Lead Developer B - Frontend, AI & Optimization Logic - Felipe Quilumbango.

- Lead Developer C - AI implementation logic - Kevin Sánchez.
--- 
