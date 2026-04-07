#include "../include/SessionManager.h"

#include <utility>

namespace
{
    constexpr int kGameUdpPort = 5556;
}

SessionOrchestrator::SessionOrchestrator() = default;

SessionOrchestrator::~SessionOrchestrator()
{
    std::lock_guard<std::mutex> lock(mtx);
    for (auto& entry : sessionsById)
    {
        if (entry.second.udpSender)
        {
            entry.second.udpSender->stop();
        }
    }
}

std::string SessionOrchestrator::makeSessionId()
{
    const int id = sessionCounter.fetch_add(1);
    return "session_" + std::to_string(id);
}

std::string SessionOrchestrator::createMatch(const MatchCandidate& a, const MatchCandidate& b)
{
    std::lock_guard<std::mutex> lock(mtx);

    const std::string sessionId = makeSessionId();

    auto session = std::make_shared<GameSession>(a.internalPlayerId, b.internalPlayerId, sessionId);
    auto engine = std::make_shared<GameEngine>(session);

    auto sender = std::make_unique<KinematicSender>(kGameUdpPort);
    sender->setSession(session);
    sender->start();

    SessionRecord record;
    record.p1 = a.socket;
    record.p2 = b.socket;
    record.session = session;
    record.engine = engine;
    record.udpSender = std::move(sender);

    sessionsById[sessionId] = std::move(record);
    sessionIdByClient[a.socket] = sessionId;
    sessionIdByClient[b.socket] = sessionId;

    return sessionId;
}

bool SessionOrchestrator::markReady(SOCKET clientSocket, const std::string& sessionId)
{
    std::lock_guard<std::mutex> lock(mtx);

    auto it = sessionsById.find(sessionId);
    if (it == sessionsById.end())
    {
        return false;
    }

    SessionRecord& record = it->second;
    if (record.started)
    {
        return false;
    }

    if (clientSocket == record.p1)
    {
        record.p1Ready = true;
    }
    else if (clientSocket == record.p2)
    {
        record.p2Ready = true;
    }
    else
    {
        return false;
    }

    if (record.p1Ready && record.p2Ready)
    {
        record.started = true;
        return true;
    }

    return false;
}

void SessionOrchestrator::closeByClient(SOCKET clientSocket)
{
    std::lock_guard<std::mutex> lock(mtx);

    auto clientIt = sessionIdByClient.find(clientSocket);
    if (clientIt == sessionIdByClient.end())
    {
        return;
    }

    const std::string sessionId = clientIt->second;
    auto sessionIt = sessionsById.find(sessionId);
    if (sessionIt == sessionsById.end())
    {
        sessionIdByClient.erase(clientIt);
        return;
    }

    const SOCKET p1 = sessionIt->second.p1;
    const SOCKET p2 = sessionIt->second.p2;

    if (sessionIt->second.udpSender)
    {
        sessionIt->second.udpSender->stop();
    }

    sessionsById.erase(sessionIt);
    sessionIdByClient.erase(clientIt);
    sessionIdByClient.erase(p1);
    sessionIdByClient.erase(p2);
}

std::shared_ptr<GameSession> SessionOrchestrator::getSession(const std::string& sessionId) const
{
    std::lock_guard<std::mutex> lock(mtx);

    auto it = sessionsById.find(sessionId);
    if (it == sessionsById.end())
    {
        return nullptr;
    }
    return it->second.session;
}

std::shared_ptr<GameEngine> SessionOrchestrator::getEngine(const std::string& sessionId) const
{
    std::lock_guard<std::mutex> lock(mtx);

    auto it = sessionsById.find(sessionId);
    if (it == sessionsById.end())
    {
        return nullptr;
    }
    return it->second.engine;
}

bool SessionOrchestrator::getPlayers(const std::string& sessionId, std::pair<SOCKET, SOCKET>& players) const
{
    std::lock_guard<std::mutex> lock(mtx);

    auto it = sessionsById.find(sessionId);
    if (it == sessionsById.end())
    {
        return false;
    }

    players = {it->second.p1, it->second.p2};
    return true;
}
