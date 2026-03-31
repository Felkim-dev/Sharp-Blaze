#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include "platform_socket.h"
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <deque>
#include <string>


class NetworkManager {
public:
    NetworkManager(int port); //constructor
    ~NetworkManager();        //destructor
    void start();             //para iniciar el server 
    void stop();              //para detener el server

private:
    void handleClient(SOCKET clientSocket, int playerId); 
    SOCKET serverSocket;
    int port;
    std::atomic<bool> isRunning;
    std::vector<std::thread> clientThreads;
    std::mutex clientMutex;

    struct WaitingPlayer
    {
        SOCKET socket;
        int playerId;
        std::string playerName;
    };

    std::deque<WaitingPlayer> waitingQueue;
    std::mutex matchmakingMutex;
    std::atomic<int> sessionCounter{1};
    
    void enqueueForMatchmaking(SOCKET socket, int playerId, const std::string& playerName);
    void removeFromMatchmakingQueue(SOCKET socket);
    void tryMatchPlayersLocked();
    std::string createSessionId();
    bool sendAll(SOCKET socket, const std::string& text);
    

};


#endif