

#include <iostream>
#include <thread>
#include <deque>
#include <string>
#include <algorithm>
#include <atomic>
#include <unordered_map>


//#include "third_party/json.hpp"
#include "NetworkManager.h"
#include "clientProtocol.h"
#include "platform_socket.h"

// #ifdef _MSC_VER
// #pragma comment(lib, "Ws2_32.lib")
// #endif

namespace
{
    struct PlayerState
    {
        SOCKET socket = INVALID_SOCKET;
        int internalPlayerId  = 0;
        std::string playerName;
        std::string sessionId;
        bool ready = false;
    };
    std::mutex g_matchMutex;
    std::deque<SOCKET> g_waitingQueue;
    std::unordered_map<SOCKET, PlayerState> g_players;
    std::unordered_map<std::string, std::pair<SOCKET,SOCKET>> g_sessions;
    std::atomic<int> g_sessionCounter{1};
    
    bool SendText(SOCKET socket, const std::string& text)
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

    std::string MakeSessionId()
    {
        const int id = g_sessionCounter.fetch_add(1);
        return "session_" + std::to_string(id);
    }

    void RemoveFromQueueNoLock(SOCKET socket)
    {
        g_waitingQueue.erase(
            std::remove(g_waitingQueue.begin(),g_waitingQueue.end(),socket),
            g_waitingQueue.end());
    }

    void TryMatchPlayersNoLock()
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
            const std::string sessionId = MakeSessionId();
            p1.sessionId = sessionId;
            p2.sessionId = sessionId;
            p1.ready = false;
            p2.ready = false;
            g_sessions[ sessionId ] = {a, b};

            const std::string msg1 = client_protocol::BuildMatchFoundResponse(
                sessionId,
                p1.playerName,
                p2.playerName);
            const std::string msg2 = client_protocol::BuildMatchFoundResponse(
                sessionId,
                p2.playerName,
                p1.playerName);
            SendText(a,msg1);
            SendText(b,msg2);

            std::cout << "[MATCH] " << p1.playerName << " vs " << p2.playerName
                      << " | " << sessionId << "\n";
        }
    }

    void HandleReadyNoLock(SOCKET socket, const std::string &sessionId)
    {
        if (!g_players.count(socket))
        {
            return;
        }

        PlayerState &me = g_players[socket];
        if (me.sessionId != sessionId)
        {
            return;
        }

        if (!g_sessions.count(sessionId))
        {
            return;
        }

        me.ready = true;
        const auto pair = g_sessions[sessionId];

        if (!g_players.count(pair.first) || !g_players.count(pair.second))
        {
            return;
        }

        const bool bothReady = g_players[pair.first].ready && g_players[pair.second].ready;
        if (!bothReady)
        {
            return;
        }   

        const std::string startMsg = client_protocol::BuildMatchStartResponse(sessionId);
        SendText(pair.first, startMsg);
        SendText(pair.second, startMsg);

        std::cout << "[MATCH] " << sessionId << " started.\n";
    }

    void CleanupDisconnectedNoLock(SOCKET socket)
    {
        RemoveFromQueueNoLock(socket);

        if (!g_players.count(socket))
        {
            return;
        }

        const PlayerState me = g_players[socket];
        g_players.erase(socket);

        if (me.sessionId.empty())
        {
            return;
        }

        if (!g_sessions.count(me.sessionId))
        {
            return;
        }

        const auto pair = g_sessions[me.sessionId];
        g_sessions.erase(me.sessionId);

        const SOCKET other = (pair.first == socket) ? pair.second : pair.first;
        if (g_players.count(other))
        {
            PlayerState &opponent = g_players[other];
            opponent.sessionId.clear();
            opponent.ready = false;
            g_waitingQueue.push_back(other);

            const std::string queueMsg =
                client_protocol::BuildQueueStatusResponse(static_cast<int>(g_waitingQueue.size()), g_players[socket].playerName);
            SendText(other, queueMsg);            
            TryMatchPlayersNoLock();
        }
    }
}

//TODO: corregir para que funcione con windows  y linux
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
                    if (!SendText(clientSocket, responseToSend))
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
                        PlayerState st;
                        st.socket = clientSocket;
                        st.internalPlayerId = playerId;
                        st.playerName = parsed.initialConnect.playerId;
                        g_players[clientSocket] = st;
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
                            SendText(clientSocket, queueMsg);
                            
                        }

                        TryMatchPlayersNoLock();
                    }

                    std::cout << "[QUEUE] P" << playerId << " (" << parsed.initialConnect.playerId
                              << ") connected.\n";
                }
                else if (parsed.type == client_protocol::ParsedMessageType::PlayerReady)
                {
                    std::lock_guard<std::mutex> lock(g_matchMutex);
                    HandleReadyNoLock(clientSocket, parsed.playerReady.sessionId);
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
        CleanupDisconnectedNoLock(clientSocket);
    }

    net::CloseSocket(clientSocket);
}