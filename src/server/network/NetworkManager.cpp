

#include <iostream>
#include <thread>
#include <deque>
#include <string>
#include <algorithm>


#include "NetworkManager.h"
#include "clientProtocol.h"
#include "platform_socket.h"

bool NetworkManager::sendText(SOCKET socket, const std::string& text)
{
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

        if ( !p1.sessionId.empty() || !p2.sessionId.empty())
        {
            continue;
        }

        MatchCandidate c1{};
        c1.socket = p1.socket;
        c1.internalPlayerId = p1.internalPlayerId;
        c1.playerName = p1.playerName;
        MatchCandidate c2{};
        c2.socket = p2.socket;
        c2.internalPlayerId = p2.internalPlayerId;
        c2.playerName = p2.playerName;

        const std::string sessionId = sessionOrchestrator.createMatch(c1, c2);
        p1.sessionId = sessionId;
        p2.sessionId = sessionId;

        const std::string msg1 = client_protocol::BuildMatchFoundResponse(
            sessionId,
            p1.playerName,
            p2.playerName);
        const std::string msg2 = client_protocol::BuildMatchFoundResponse(
            sessionId,
            p2.playerName,
            p1.playerName);
        sendText(a,msg1);
        sendText(b,msg2);

        std::cout << "[MATCH] " << p1.playerName << " vs " << p2.playerName
                    << " | " << sessionId << "\n";
    }
}

void NetworkManager::handleReadyNoLock(SOCKET socket, const std::string &sessionId)
{
    if (!g_players.count(socket))
    {
        return;
    }

    PlayerState &me = g_players[socket];
    const std::string effectiveSessionId = sessionId.empty() ? me.sessionId : sessionId;

    if (effectiveSessionId.empty())
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

    const std::string startMsg = client_protocol::BuildMatchStartResponse(
        effectiveSessionId,
        session);
    if (sendText(players.first, startMsg))
    {
        std::cout << "GAME_START ENVIADO CORRECTAMENTE\n";
    };
    sendText(players.second, startMsg);

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

    if (me.sessionId.empty())
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
        opponent.sessionId.clear();
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
                            playerId,
                            parsed.initialConnect.playerId,
                            std::string{}
                        };
                    }

                    if (g_players[clientSocket].sessionId.empty())
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
                    std::lock_guard<std::mutex> lock(g_matchMutex);

                    if (!g_players.count(clientSocket))
                    {
                        continue;
                    }

                    const PlayerState& me = g_players[clientSocket];
                    if (me.sessionId.empty())
                    {
                        continue;
                    }

                    auto engine = sessionOrchestrator.getEngine(me.sessionId);
                    if (!engine)
                    {
                        continue;
                    }

                    games_types::PlayerCommand cmd{};
                    cmd.playerId = me.internalPlayerId;
                    cmd.unitId = parsed.moveUnit.unitId;
                    cmd.destX = parsed.moveUnit.destX;
                    cmd.destY = parsed.moveUnit.destY;

                    engine->tcpCommandEnqueue(cmd);
                    engine->commandQueueProcess();
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