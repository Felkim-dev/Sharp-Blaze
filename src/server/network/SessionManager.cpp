#include "../include/SessionManager.h"
#include "../include/udpDispatcher.h"
#include "../include/clientProtocol.h"

#include <chrono>
#include <sstream>
#include <thread>
#include <utility>

SessionOrchestrator::SessionOrchestrator() = default;

SessionOrchestrator::~SessionOrchestrator()
{
    std::unordered_map<int, SessionRecord> sessionsToStop;
    {
        std::lock_guard<std::mutex> lock(mtx);
        sessionsToStop = std::move(sessionsById);
        sessionIdByClient.clear();
    }

    for (auto& entry : sessionsToStop)
    {
        stopSimulationNoLock(entry.second);
        GlobalUDPDispatcher::getInstance().onSessionClosed(entry.first);
    }
}

void SessionOrchestrator::simulationLoop(std::shared_ptr<GameEngine> engine,
                                         std::shared_ptr<std::atomic<bool>> runningFlag,
                                         SOCKET p1Socket,
                                         int p1InternalPlayerId,
                                         SOCKET p2Socket,
                                         int p2InternalPlayerId,
                                         std::function<void(SOCKET, int)> resourceBalanceCallback,
                                         std::function<void(SOCKET, const std::string&)> matchEventCallback)
{
    constexpr int kTickMs = 16;
    const std::chrono::milliseconds targetFrame(kTickMs);

    while (runningFlag && runningFlag->load())
    {
        const auto tickStart = std::chrono::steady_clock::now();

        if (engine)
        {
            engine->commandQueueProcess();
            engine->advanceCollectors(kTickMs);
            engine->advanceCombat(kTickMs);

            const auto attackResults = engine->drainAttackResults();
            for (const auto& result : attackResults)
            {
                if (!matchEventCallback)
                {
                    continue;
                }

                SOCKET targetSocket = INVALID_SOCKET;
                if (result.playerId == p1InternalPlayerId)
                {
                    targetSocket = p1Socket;
                }
                else if (result.playerId == p2InternalPlayerId)
                {
                    targetSocket = p2Socket;
                }

                if (targetSocket == INVALID_SOCKET)
                {
                    continue;
                }

                const std::string attackResultMessage = client_protocol::BuildAttackResultResponse(
                    result.attackerId,
                    result.targetId,
                    result.accepted,
                    result.reason,
                    result.targetCurrentHp);
                matchEventCallback(targetSocket, attackResultMessage);
            }

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

            bool shouldStop = false;
            const auto combatEvents = engine->drainCombatEvents();
            for (const auto& event : combatEvents)
            {
                if (!matchEventCallback)
                {
                    continue;
                }

                std::string message;
                if (event.type == games_types::CombatEventType::UnitDamaged)
                {
                    std::ostringstream response;
                    response << "{\"type\":\"UNIT_DAMAGED\",\"payload\":{"
                             << "\"session_id\":" << event.sessionId << ','
                             << "\"target_player_id\":" << event.targetPlayerId << ','
                             << "\"target_entity_id\":" << event.targetEntityId << ','
                             << "\"attacker_player_id\":" << event.attackerPlayerId << ','
                             << "\"attacker_entity_id\":" << event.attackerEntityId << ','
                             << "\"current_hp\":" << event.currentHp
                             << "}}\n";
                    message = response.str();
                }
                else if (event.type == games_types::CombatEventType::EntityDestroyed)
                {
                    message = client_protocol::BuildEntityDestroyedResponse(
                        event.sessionId,
                        event.targetEntityId,
                        event.targetPlayerId,
                        event.attackerPlayerId);
                }
                else if (event.type == games_types::CombatEventType::GameOver)
                {
                    message = client_protocol::BuildGameOverResponse(
                        event.sessionId,
                        event.winnerPlayerId);
                    shouldStop = true;
                }

                if (!message.empty())
                {
                    matchEventCallback(p1Socket, message);
                    if (p2Socket != p1Socket)
                    {
                        matchEventCallback(p2Socket, message);
                    }
                }
            }

            if (shouldStop)
            {
                runningFlag->store(false);
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

void SessionOrchestrator::setMatchEventCallback(std::function<void(SOCKET, const std::string&)> callback)
{
    std::lock_guard<std::mutex> lock(mtx);
    matchEventCallback = std::move(callback);
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

    GlobalUDPDispatcher::getInstance().onSessionStarted(
        record.sessionId,
        record.p1InternalPlayerId,
        record.p2InternalPlayerId,
        record.session);

    record.simulationRunning->store(true);
    record.simulationThread = std::thread(
        &SessionOrchestrator::simulationLoop,
        record.engine,
        record.simulationRunning,
        record.p1,
        record.p1InternalPlayerId,
        record.p2,
        record.p2InternalPlayerId,
        resourceBalanceCallback,
        matchEventCallback);
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

int SessionOrchestrator::makeSessionId()
{
    const int id = sessionCounter.fetch_add(1);
    return id;
}

int SessionOrchestrator::createMatch(const MatchCandidate& a, const MatchCandidate& b)
{
    std::lock_guard<std::mutex> lock(mtx);

    const int sessionId = makeSessionId();

    auto session = std::make_shared<GameSession>(a.internalPlayerId, b.internalPlayerId, sessionId);
    auto engine = std::make_shared<GameEngine>(session);

    SessionRecord record;
    record.sessionId = sessionId;
    record.p1 = a.socket;
    record.p2 = b.socket;
    record.p1InternalPlayerId = a.internalPlayerId;
    record.p2InternalPlayerId = b.internalPlayerId;
    record.session = session;
    record.engine = engine;
    record.simulationRunning = std::make_shared<std::atomic<bool>>(false);

    sessionsById[sessionId] = std::move(record);
    sessionIdByClient[a.socket] = sessionId;
    sessionIdByClient[b.socket] = sessionId;

    return sessionId;
}

bool SessionOrchestrator::markReady(SOCKET clientSocket, const int& sessionId)
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
    SessionRecord recordToStop;
    int sessionId;
    bool found = false;

    {
        std::lock_guard<std::mutex> lock(mtx);

        auto clientIt = sessionIdByClient.find(clientSocket);
        if (clientIt == sessionIdByClient.end())
        {
            return;
        }

        sessionId = clientIt->second;
        auto sessionIt = sessionsById.find(sessionId);
        if (sessionIt == sessionsById.end())
        {
            sessionIdByClient.erase(clientIt);
            return;
        }

        recordToStop = std::move(sessionIt->second);
        sessionsById.erase(sessionIt);
        sessionIdByClient.erase(clientIt);
        sessionIdByClient.erase(recordToStop.p1);
        sessionIdByClient.erase(recordToStop.p2);
        found = true;
    }

    if (found)
    {
        stopSimulationNoLock(recordToStop);
        GlobalUDPDispatcher::getInstance().onSessionClosed(sessionId);
    }
}

std::shared_ptr<GameSession> SessionOrchestrator::getSession(const int& sessionId) const
{
    std::lock_guard<std::mutex> lock(mtx);

    auto it = sessionsById.find(sessionId);
    if (it == sessionsById.end())
    {
        return nullptr;
    }
    return it->second.session;
}

std::shared_ptr<GameEngine> SessionOrchestrator::getEngine(const int& sessionId) const
{
    std::lock_guard<std::mutex> lock(mtx);

    auto it = sessionsById.find(sessionId);
    if (it == sessionsById.end())
    {
        return nullptr;
    }
    return it->second.engine;
}

bool SessionOrchestrator::getPlayers(const int& sessionId, std::pair<SOCKET, SOCKET>& players) const
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
