

#include <iostream>
#include <thread>
#include <deque>
#include <string>
#include <algorithm>
#include <cstdint>


#include "NetworkManager.h"
#include "clientProtocol.h"
#include "platform_socket.h"

bool NetworkManager::sendText(SOCKET socket, const std::string& text)
{
    std::lock_guard<std::mutex> lock(sendMutex);
    size_t totalSent = 0;
    while(totalSent < text.size())
    {
        const int sent = send(
            socket,
            text.c_str() + totalSent,
            static_cast<int>(text.size() - totalSent),
            0);
        if (sent == SOCKET_ERROR)
        {
            return false;
        }
        else
        {
            totalSent += static_cast<size_t>(sent);
        }
    }
    return true;
}

void NetworkManager::removeFromQueueNoLock(SOCKET socket)
{
    g_waitingQueue.erase(
        std::remove(g_waitingQueue.begin(),g_waitingQueue.end(),socket),
        g_waitingQueue.end());
}

void NetworkManager::tryMatchPlayersNoLock()
{
    while (g_waitingQueue.size() >= 2)
    {
        const SOCKET a = g_waitingQueue.front();
        g_waitingQueue.pop_front();

        const SOCKET b = g_waitingQueue.front();
        g_waitingQueue.pop_front();

        if (!g_players.count(a) || !g_players.count(b))
        {
            continue;
        }

        PlayerState& p1 = g_players[a];
        PlayerState& p2 = g_players[b];

        if (p1.sessionId != 0 || p2.sessionId != 0)
        {
            continue;
        }

        // Internal gameplay ids are per-session roles, not global connection counters.
        p1.internalPlayerId = 1;
        p2.internalPlayerId = 2;

        MatchCandidate c1{};
        c1.socket = p1.socket;
        c1.internalPlayerId = p1.internalPlayerId;
        c1.playerName = p1.playerName;
        MatchCandidate c2{};
        c2.socket = p2.socket;
        c2.internalPlayerId = p2.internalPlayerId;
        c2.playerName = p2.playerName;

        const int sessionId = sessionOrchestrator.createMatch(c1, c2);
        p1.sessionId = sessionId;
        p2.sessionId = sessionId;

        const std::string msg1 = client_protocol::BuildMatchFoundResponse(
            sessionId,
            p1.internalPlayerId,
            p1.playerName,
            p2.playerName);
        const std::string msg2 = client_protocol::BuildMatchFoundResponse(
            sessionId,
            p2.internalPlayerId,
            p2.playerName,
            p1.playerName);
        sendText(a,msg1);
        sendText(b,msg2);

        std::cout << "[MATCH] " << p1.playerName << " vs " << p2.playerName
                    << " | " << sessionId << "\n";
    }
}

void NetworkManager::handleReadyNoLock(SOCKET socket, const int &sessionId)
{
    if (!g_players.count(socket))
    {
        return;
    }

    PlayerState &me = g_players[socket];
    const int effectiveSessionId = sessionId == 0 ? me.sessionId : sessionId;

    if (effectiveSessionId == 0)
    {
        return;
    }

    if (me.sessionId != effectiveSessionId)
    {
        return;
    }

    const bool shouldStart = sessionOrchestrator.markReady(socket, effectiveSessionId);
    if (!shouldStart)
    {
        return;
    }

    std::pair<SOCKET, SOCKET> players{};
    if (!sessionOrchestrator.getPlayers(effectiveSessionId, players))
    {
        return;
    }

    const auto session = sessionOrchestrator.getSession(effectiveSessionId);
    if (!session)
    {
        return;
    }

    const int p1InternalPlayerId = g_players.count(players.first) ? g_players[players.first].internalPlayerId : 0;
    const int p2InternalPlayerId = g_players.count(players.second) ? g_players[players.second].internalPlayerId : 0;

    const std::uint16_t udpPort = 5556;
    const std::string startMsgP1 = client_protocol::BuildMatchStartResponse(
        effectiveSessionId,
        p1InternalPlayerId,
        udpPort,
        session);
    const std::string startMsgP2 = client_protocol::BuildMatchStartResponse(
        effectiveSessionId,
        p2InternalPlayerId,
        udpPort,
        session);

    if (sendText(players.first, startMsgP1))
    {
        std::cout << "GAME_START ENVIADO CORRECTAMENTE\n";
    }
    sendText(players.second, startMsgP2);

    std::cout << "[MATCH] " << effectiveSessionId << " started.\n";
}

void NetworkManager::cleanupDisconnectedNoLock(SOCKET socket)
{
    removeFromQueueNoLock(socket);

    if (!g_players.count(socket))
    {
        sessionOrchestrator.closeByClient(socket);
        return;
    }

    const PlayerState me = g_players[socket];
    g_players.erase(socket);

    if (me.sessionId == 0)
    {
        sessionOrchestrator.closeByClient(socket);
        return;
    }

    std::pair<SOCKET, SOCKET> pair{};
    const bool hasPair = sessionOrchestrator.getPlayers(me.sessionId, pair);
    sessionOrchestrator.closeByClient(socket);

    if (!hasPair)
    {
        return;
    }

    const SOCKET other = (pair.first == socket) ? pair.second : pair.first;
    if (g_players.count(other))
    {
        PlayerState &opponent = g_players[other];
        opponent.sessionId = 0;
        g_waitingQueue.push_back(other);

        const std::string queueMsg =
            client_protocol::BuildQueueStatusResponse(static_cast<int>(g_waitingQueue.size()), me.playerName);
        sendText(other, queueMsg);            
        tryMatchPlayersNoLock();
    }
}



NetworkManager::NetworkManager(int p):port(p){
    // Initialize variables
    isRunning = false;
    serverSocket=INVALID_SOCKET;

    // INIT de platform_socket.h
    if (!net::Init())
    {
        std::cerr << "[ERROR] Socket library failed.\n";
    }

    sessionOrchestrator.setResourceBalanceCallback(
        [this](SOCKET socket, int newBalance)
        {
            if (!isRunning)
            {
                return;
            }

            const std::string goldMessage = client_protocol::BuildResourcesResponse(newBalance);
            sendText(socket, goldMessage);
        });

    sessionOrchestrator.setMatchEventCallback(
        [this](SOCKET socket, const std::string& message)
        {
            if (!isRunning)
            {
                return;
            }

            sendText(socket, message);
        });
};

NetworkManager::~NetworkManager(){
    stop();
};

void NetworkManager::stop(){

    isRunning = false;
    if (net::IsValid(serverSocket))
    {
        net::CloseSocket(serverSocket);
    }
    net::Cleanup();
};
void NetworkManager::start(){

    serverSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (!net::IsValid(serverSocket))
    {
        std::cerr << "[ERROR] Socket creation failed." << net::GetLastError() << '\n';
        net::Cleanup();
        return;
    }
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    serverAddr.sin_addr.s_addr = INADDR_ANY; //IP QUE SE ESCUCHA


    // bind the socket to the address and port
    if (bind(serverSocket, (sockaddr *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
    {
        std::cerr << "[ERROR] Socket bind failed." << net::GetLastError() << '\n';
        net::CloseSocket(serverSocket);
        net::Cleanup();
        return;
    }

    // listen for incoming connections
    if (listen(serverSocket, SOMAXCONN) == SOCKET_ERROR)
    {
        std::cerr << "[ERROR] Listen failed." << net::GetLastError() << '\n';
        net::CloseSocket(serverSocket);
        net::Cleanup();
        return;
    }
    std::cout << "[INFO] Server is listening on port " << port << '\n';
    int playerIdCounter = 1;

    isRunning = true;
    // main loop to accept clients
    while (isRunning)
    {
        sockaddr_in clientAddr;
        // int clientSize = sizeof(clientAddr);

        // codigo para bind y listen
        socklen_t clientSize = sizeof(clientAddr);

        SOCKET clientSocket = accept(serverSocket, (sockaddr *)&clientAddr, &clientSize);
        if (!net::IsValid(clientSocket))
        {
            std::cerr << "[ERROR] Accept failed.\n";
            continue;
        }
        std::thread(&NetworkManager::handleClient, this, clientSocket, playerIdCounter).detach();
        playerIdCounter++;
    }
}

void NetworkManager::handleClient(SOCKET clientSocket, int playerId)
{
    char recvBuffer[1024];
    std::string carryBuffer;

    while (isRunning)
    {
        const int bytesReceived = recv(clientSocket, recvBuffer, sizeof(recvBuffer), 0);

        if (bytesReceived > 0)
        {
            std::vector<std::string> messages;
            const bool framingOk = client_protocol::MessageFramer(
                carryBuffer,
                recvBuffer,
                static_cast<size_t>(bytesReceived),
                messages);

            if (!framingOk)
            {
                std::cerr << "[ERROR] Framing failed for P" << playerId << ". Closing connection.\n";
                break;
            }

            for (const std::string &rawMessage : messages)
            {
                client_protocol::ParsedMessage parsed;
                std::string responseToSend;

                const bool protocolOk = client_protocol::MessageProtocol(
                    rawMessage,
                    parsed,
                    responseToSend);

                if (!responseToSend.empty())
                {
                    if (!sendText(clientSocket, responseToSend))
                    {
                        std::cerr << "[ERROR] send() failed for P" << playerId
                                  << " code=" << net::GetLastError() << "\n";
                        break;
                    }
                }

                if (!protocolOk)
                {
                    continue;
                }

                if (parsed.type == client_protocol::ParsedMessageType::InitialConnect)
                {
                    std::lock_guard<std::mutex> lock(g_matchMutex);

                    if (!g_players.count(clientSocket))
                    {
                        g_players[clientSocket] = PlayerState{
                            clientSocket,
                            0,
                            parsed.initialConnect.playerId,
                            int{}
                        };
                    }

                    if (g_players[clientSocket].sessionId == 0)
                    {
                        const bool alreadyQueued =
                            std::find(g_waitingQueue.begin(), g_waitingQueue.end(), clientSocket) != g_waitingQueue.end();

                        if (!alreadyQueued)
                        {
                            g_waitingQueue.push_back(clientSocket);

                            const std::string queueMsg =
                                client_protocol::BuildQueueStatusResponse(static_cast<int>(g_waitingQueue.size()), g_players[clientSocket].playerName);
                            sendText(clientSocket, queueMsg);
                            
                        }

                        tryMatchPlayersNoLock();
                    }

                    std::cout << "[QUEUE] P" << playerId << " (" << parsed.initialConnect.playerId
                              << ") connected.\n";
                }
                else if (parsed.type == client_protocol::ParsedMessageType::PlayerReady)
                {
                    std::lock_guard<std::mutex> lock(g_matchMutex);
                    handleReadyNoLock(clientSocket, parsed.playerReady.sessionId);
                }
                else if (parsed.type == client_protocol::ParsedMessageType::MoveUnit)
                {
                    int sessionId;
                    int internalPlayerId = 0;
                    {
                        std::lock_guard<std::mutex> lock(g_matchMutex);
                        if (!g_players.count(clientSocket))
                        {
                            continue;
                        }

                        const PlayerState& me = g_players[clientSocket];
                        if (me.sessionId == 0)
                        {
                            continue;
                        }

                        sessionId = me.sessionId;
                        internalPlayerId = me.internalPlayerId;
                    }

                    auto engine = sessionOrchestrator.getEngine(sessionId);
                    if (!engine)
                    {
                        continue;
                    }

                    games_types::PlayerCommand cmd{};
                    cmd.playerId = internalPlayerId;
                    cmd.unitId = parsed.moveUnit.unitId;
                    cmd.destCell = parsed.moveUnit.destination;

                    engine->tcpCommandEnqueue(cmd);

                    games_types::ShopAuthorizationState shopState{};
                    if (engine->reconcileShopAuthorization(internalPlayerId, shopState))
                    {
                        const std::string authMsg = client_protocol::BuildShopAuthorizationResponse(
                            internalPlayerId,
                            shopState);
                        sendText(clientSocket, authMsg);
                    }
                }
                else if (parsed.type == client_protocol::ParsedMessageType::Attack)
                {
                    int sessionId;
                    int internalPlayerId = 0;
                    {
                        std::lock_guard<std::mutex> lock(g_matchMutex);
                        if (!g_players.count(clientSocket))
                        {
                            continue;
                        }

                        const PlayerState& me = g_players[clientSocket];
                        if (me.sessionId == 0)
                        {
                            continue;
                        }

                        sessionId = me.sessionId;
                        internalPlayerId = me.internalPlayerId;
                    }

                    auto engine = sessionOrchestrator.getEngine(sessionId);
                    if (!engine)
                    {
                        continue;
                    }

                    games_types::PlayerCommand cmd{};
                    cmd.type = games_types::CommandType::AttackUnit;
                    cmd.playerId = internalPlayerId;
                    cmd.attack.attackerId = parsed.attack.attackerId;
                    cmd.attack.targetId = parsed.attack.targetId;

                    engine->tcpCommandEnqueue(cmd);
                }
                else if (parsed.type == client_protocol::ParsedMessageType::BuyUnit)
                {
                    int sessionId;
                    int internalPlayerId = 0;
                    {
                        std::lock_guard<std::mutex> lock(g_matchMutex);
                        if (!g_players.count(clientSocket))
                        {
                            continue;
                        }

                        const PlayerState& me = g_players[clientSocket];
                        if (me.sessionId == 0)
                        {
                            continue;
                        }

                        sessionId = me.sessionId;
                        internalPlayerId = me.internalPlayerId;
                    }

                    auto engine = sessionOrchestrator.getEngine(sessionId);
                    if (!engine)
                    {
                        continue;
                    }

                    const auto purchase = engine->processUnitPurchase(
                        internalPlayerId,
                        parsed.buyUnit.unitType,
                        parsed.buyUnit.quantity);

                    std::string buyerMsg;
                    if (!purchase.success)
                    {
                        buyerMsg =
                            std::string("{\"type\":\"BUY_UNIT_RESULT\",\"status\":\"rejected\",\"reason\":\"") +
                            purchase.reason +
                            "\"}\n";
                        sendText(clientSocket, buyerMsg);
                        continue;
                    }

                    buyerMsg =
                        std::string("{\"type\":\"BUY_UNIT_RESULT\",\"status\":\"accepted\",\"payload\":{") +
                        "\"unit_id\":" + std::to_string(purchase.unitId) + "," +
                        "\"unit_type\":" + std::to_string(static_cast<int>(purchase.unitType)) + "," +
                        "\"spawn_x\":" + std::to_string(purchase.spawnX) + "," +
                        "\"spawn_y\":" + std::to_string(purchase.spawnY) + "," +
                        "\"new_balance\":" + std::to_string(purchase.newBalance) +
                        "}}\n";
                    sendText(clientSocket, buyerMsg);

                    const std::string goldMessage = client_protocol::BuildResourcesResponse(
                        purchase.newBalance);
                    sendText(clientSocket, goldMessage);

                    std::pair<SOCKET, SOCKET> players{};
                    if (sessionOrchestrator.getPlayers(sessionId, players))
                    {
                        const std::string spawnBroadcast =
                            std::string("{\"type\":\"UNIT_SPAWNED\",\"payload\":{") +
                            "\"unit_id\":" + std::to_string(purchase.unitId) + "," +
                            "\"unit_type\":" + std::to_string(static_cast<int>(purchase.unitType)) + "," +
                            "\"owner_player\":" + std::to_string(internalPlayerId) +
                            "}}\n";
                        sendText(players.first, spawnBroadcast);
                        if (players.second != players.first)
                        {
                            sendText(players.second, spawnBroadcast);
                        }
                    }
                }
                else if (parsed.type == client_protocol::ParsedMessageType::DepositResource)
                {
                    {
                        std::lock_guard<std::mutex> lock(g_matchMutex);
                        if (!g_players.count(clientSocket))
                        {
                            continue;
                        }
                    }

                    const std::string depositAck =
                        "{\"type\":\"DEPOSIT_RESOURCE_RESULT\",\"status\":\"ignored\",\"reason\":\"server_authoritative_fsm\"}\n";
                    sendText(clientSocket, depositAck);
                }
            }
        }
        else if (bytesReceived == 0)
        {
            std::cout << "[INFO] Player " << playerId << " disconnected.\n";
            break;
        }
        else
        {
            std::cerr << "[ERROR] recv() failed for P" << playerId
                      << " code=" << net::GetLastError() << "\n";
            break;
        }
    }

    {
        std::lock_guard<std::mutex> lock(g_matchMutex);
        cleanupDisconnectedNoLock(clientSocket);
    }

    net::CloseSocket(clientSocket);
}