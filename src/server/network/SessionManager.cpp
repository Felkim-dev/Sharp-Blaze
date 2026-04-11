#include "../include/SessionManager.h"

#include <chrono>
#include <thread>
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
        stopSimulationNoLock(entry.second);

        if (entry.second.udpSender)
        {
            entry.second.udpSender->stop();
        }
    }
}

void SessionOrchestrator::simulationLoop(std::shared_ptr<GameEngine> engine,
                                         std::shared_ptr<std::atomic<bool>> runningFlag,
                                         SOCKET p1Socket,
                                         int p1InternalPlayerId,
                                         SOCKET p2Socket,
                                         int p2InternalPlayerId,
                                         std::function<void(SOCKET, int)> resourceBalanceCallback)
{
    constexpr int kTickMs = 16;
    const std::chrono::milliseconds targetFrame(kTickMs);

    while (runningFlag && runningFlag->load())
    {
        const auto tickStart = std::chrono::steady_clock::now();

        if (engine)
        {
            engine->advanceCollectors(kTickMs);

            const auto economyEvents = engine->drainEconomyTransactions();
            for (const auto& event : economyEvents)
            {
                if (event.deltaGold <= 0)
                {
                    continue;
                }

                SOCKET targetSocket = INVALID_SOCKET;
                if (event.playerId == p1InternalPlayerId)
                {
                    targetSocket = p1Socket;
                }
                else if (event.playerId == p2InternalPlayerId)
                {
                    targetSocket = p2Socket;
                }

                if (targetSocket != INVALID_SOCKET && resourceBalanceCallback)
                {
                    resourceBalanceCallback(targetSocket, event.resultingGold);
                }
            }
        }

        const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - tickStart);
        if (elapsed < targetFrame)
        {
            std::this_thread::sleep_for(targetFrame - elapsed);
        }
    }
}

void SessionOrchestrator::setResourceBalanceCallback(std::function<void(SOCKET, int)> callback)
{
    std::lock_guard<std::mutex> lock(mtx);
    resourceBalanceCallback = std::move(callback);
}

void SessionOrchestrator::startSimulationNoLock(SessionRecord& record)
{
    if (!record.engine)
    {
        return;
    }

    if (!record.simulationRunning)
    {
        record.simulationRunning = std::make_shared<std::atomic<bool>>(false);
    }

    if (record.simulationThread.joinable())
    {
        return;
    }

    record.simulationRunning->store(true);
    record.simulationThread = std::thread(
        &SessionOrchestrator::simulationLoop,
        record.engine,
        record.simulationRunning,
        record.p1,
        record.p1InternalPlayerId,
        record.p2,
        record.p2InternalPlayerId,
        resourceBalanceCallback);
}

void SessionOrchestrator::stopSimulationNoLock(SessionRecord& record)
{
    if (record.simulationRunning)
    {
        record.simulationRunning->store(false);
    }

    if (record.simulationThread.joinable())
    {
        record.simulationThread.join();
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
    record.p1InternalPlayerId = a.internalPlayerId;
    record.p2InternalPlayerId = b.internalPlayerId;
    record.session = session;
    record.engine = engine;
    record.udpSender = std::move(sender);
    record.simulationRunning = std::make_shared<std::atomic<bool>>(false);

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
        startSimulationNoLock(record);
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

    stopSimulationNoLock(sessionIt->second);

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
