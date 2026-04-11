#pragma once
#include <atomic>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <unordered_map>

#include "platform_socket.h"
#include "GameSession.h"
#include "GameEngine.h"
#include "UDPBroadcaster.h"

struct MatchCandidate {
    SOCKET socket = INVALID_SOCKET;
    int internalPlayerId = 0;
    std::string playerName;
};

class SessionOrchestrator {
public:
    SessionOrchestrator();
    ~SessionOrchestrator();

    std::string createMatch(const MatchCandidate& a, const MatchCandidate& b);
    bool markReady(SOCKET clientSocket, const std::string& sessionId);
    void closeByClient(SOCKET clientSocket);
    void setResourceBalanceCallback(std::function<void(SOCKET, int)> callback);

    std::shared_ptr<GameSession> getSession(const std::string& sessionId) const;
    std::shared_ptr<GameEngine> getEngine(const std::string& sessionId) const;
    bool getPlayers(const std::string& sessionId, std::pair<SOCKET, SOCKET>& players) const;

private:
    struct SessionRecord {
        SOCKET p1 = INVALID_SOCKET;
        SOCKET p2 = INVALID_SOCKET;
        int p1InternalPlayerId = 0;
        int p2InternalPlayerId = 0;
        bool p1Ready = false;
        bool p2Ready = false;
        bool started = false;
        std::shared_ptr<GameSession> session;
        std::shared_ptr<GameEngine> engine;
        std::unique_ptr<KinematicSender> udpSender;
        std::shared_ptr<std::atomic<bool>> simulationRunning;
        std::thread simulationThread;
    };

    std::string makeSessionId();
    void startSimulationNoLock(SessionRecord& record);
    void stopSimulationNoLock(SessionRecord& record);
    static void simulationLoop(std::shared_ptr<GameEngine> engine,
                               std::shared_ptr<std::atomic<bool>> runningFlag,
                               SOCKET p1Socket,
                               int p1InternalPlayerId,
                               SOCKET p2Socket,
                               int p2InternalPlayerId,
                               std::function<void(SOCKET, int)> resourceBalanceCallback);

    mutable std::mutex mtx;
    std::atomic<int> sessionCounter{1};

    std::unordered_map<std::string, SessionRecord> sessionsById;
    std::unordered_map<SOCKET, std::string> sessionIdByClient;
    std::function<void(SOCKET, int)> resourceBalanceCallback;
};