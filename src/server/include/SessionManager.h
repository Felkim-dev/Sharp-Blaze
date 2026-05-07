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

struct MatchCandidate {
    SOCKET socket = INVALID_SOCKET;
    int internalPlayerId = 0;
    std::string playerName;
};

class SessionOrchestrator {
public:
    SessionOrchestrator();
    ~SessionOrchestrator();

    int createMatch(const MatchCandidate& a, const MatchCandidate& b);
    
    // For dedicated sessions (created by broker)
    void createDedicatedSession(int sessionId, bool arcadeMode = false);
    // Register a client socket to a dedicated session. Returns assigned internalPlayerId (1 or 2), or 0 on failure.
    int registerClientToSession(SOCKET clientSocket, int sessionId, int internalPlayerId);
    
    bool markReady(SOCKET clientSocket, const int& sessionId);
    void closeByClient(SOCKET clientSocket);
    void setResourceBalanceCallback(std::function<void(SOCKET, int)> callback);
    void setMatchEventCallback(std::function<void(SOCKET, const std::string&)> callback);

    std::shared_ptr<GameSession> getSession(const int& sessionId) const;
    std::shared_ptr<GameEngine> getEngine(const int& sessionId) const;
    bool getPlayers(const int& sessionId, std::pair<SOCKET, SOCKET>& players) const;

    struct SessionRecord {
        int sessionId;
        SOCKET p1 = INVALID_SOCKET;
        SOCKET p2 = INVALID_SOCKET;
        int p1InternalPlayerId = 0;
        int p2InternalPlayerId = 0;
        bool p1Ready = false;
        bool p2Ready = false;
        bool started = false;
        std::shared_ptr<GameSession> session;
        std::shared_ptr<GameEngine> engine;
        std::shared_ptr<std::atomic<bool>> simulationRunning;
        std::thread simulationThread;
        bool isDedicated = false;
        int pausedByPlayerId{-1};  // which player paused (1 or 2), -1 = no active pause
    };

    SessionRecord* findSessionRecord(int sessionId);

private:
    int makeSessionId();
    void startSimulationNoLock(SessionRecord& record);
    void stopSimulationNoLock(SessionRecord& record);
    static void simulationLoop(std::shared_ptr<GameEngine> engine,
                               std::shared_ptr<std::atomic<bool>> runningFlag,
                               SOCKET p1Socket,
                               int p1InternalPlayerId,
                               SOCKET p2Socket,
                               int p2InternalPlayerId,
                               std::function<void(SOCKET, int)> resourceBalanceCallback,
                               std::function<void(SOCKET, const std::string&)> matchEventCallback);

    mutable std::mutex mtx;
    std::atomic<int> sessionCounter{1};

    std::unordered_map<int, SessionRecord> sessionsById;
    std::unordered_map<SOCKET, int> sessionIdByClient;
    std::function<void(SOCKET, int)> resourceBalanceCallback;
    std::function<void(SOCKET, const std::string&)> matchEventCallback;
};
