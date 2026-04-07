#pragma once
#include <atomic>
#include <memory>
#include <mutex>
#include <string>
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

    std::shared_ptr<GameSession> getSession(const std::string& sessionId) const;
    std::shared_ptr<GameEngine> getEngine(const std::string& sessionId) const;
    bool getPlayers(const std::string& sessionId, std::pair<SOCKET, SOCKET>& players) const;

private:
    struct SessionRecord {
        SOCKET p1 = INVALID_SOCKET;
        SOCKET p2 = INVALID_SOCKET;
        bool p1Ready = false;
        bool p2Ready = false;
        bool started = false;
        std::shared_ptr<GameSession> session;
        std::shared_ptr<GameEngine> engine;
        std::unique_ptr<KinematicSender> udpSender;
    };

    std::string makeSessionId();

    mutable std::mutex mtx;
    std::atomic<int> sessionCounter{1};

    std::unordered_map<std::string, SessionRecord> sessionsById;
    std::unordered_map<SOCKET, std::string> sessionIdByClient;
};