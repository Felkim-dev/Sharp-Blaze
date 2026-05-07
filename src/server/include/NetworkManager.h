#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include "platform_socket.h"
#include "SessionManager.h"

#include <thread>
#include <deque>
#include <atomic>
#include <unordered_map>
#include <string>
#include <mutex>


class NetworkManager {
public:
    NetworkManager(int port); //constructor
    ~NetworkManager();        //destructor
    void start();             //para iniciar el server 
    void stop();              //para detener el server
    void initializeDedicatedSession(int sessionId, bool arcadeMode = false); // For broker-created sessions
    void setArcadeMode(bool enabled) { arcadeMode_ = enabled; }
    bool isArcadeMode() const { return arcadeMode_; }

private:
    struct PlayerState
    {
        SOCKET socket = INVALID_SOCKET;
        int internalPlayerId = 0;
        std::string playerName;
        int sessionId=0;
    };

    bool sendText(SOCKET socket, const std::string& text);
    void handleClient(SOCKET clientSocket, int playerId);
    void removeFromQueueNoLock(SOCKET socket);
    void tryMatchPlayersNoLock();
    void handleReadyNoLock(SOCKET socket, const int& sessionId);
    void cleanupDisconnectedNoLock(SOCKET socket);

    SessionOrchestrator sessionOrchestrator;

    std::mutex g_matchMutex;
    std::mutex sendMutex;
    std::deque<SOCKET> g_waitingQueue;
    std::unordered_map<SOCKET, PlayerState> g_players;

    SOCKET serverSocket;
    int port;
    std::atomic<bool> isRunning;
    bool arcadeMode_ = false;
};


#endif