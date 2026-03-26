

#include <iostream>
#include <thread>


//#include "third_party/json.hpp"
#include "NetworkManager.h"
#include "clientProtocol.h"

#ifdef _MSC_VER
#pragma comment(lib, "Ws2_32.lib")
#endif

//using json = nlohmann::json;

NetworkManager::NetworkManager(int p):port(p){
    // Initialize WSA variables
    isRunning = false;
    serverSocket=INVALID_SOCKET;
    
    WSADATA wsaData;

    // request winsock version 2.2
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        std::cerr << "[ERROR] WSAStartup failed.\n";
    }
};

NetworkManager::~NetworkManager(){
    stop();
};

void NetworkManager::stop(){

    isRunning = false;
    if (serverSocket != INVALID_SOCKET)
    {
        closesocket(serverSocket);
    }
    WSACleanup();
};
void NetworkManager::start(){

    serverSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (serverSocket == INVALID_SOCKET)
    {
        std::cerr << "[ERROR] Socket creation failed.\n";
        WSACleanup();
        return;
    }
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    serverAddr.sin_addr.s_addr = INADDR_ANY;

    // bind the socket to the address and port
    if (bind(serverSocket, (sockaddr *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
    {
        std::cerr << "[ERROR] Socket bind failed.\n";
        closesocket(serverSocket);
        WSACleanup();
        return;
    }

    // listen for incoming connections
    if (listen(serverSocket, SOMAXCONN) == SOCKET_ERROR)
    {
        std::cerr << "[ERROR] Listen failed.\n";
        closesocket(serverSocket);
        WSACleanup();
        return;
    }
    std::cout << "[INFO] Server is listening on port " << port << '\n';
    int playerIdCounter = 1;

    isRunning = true;
    // main loop to accept clients
    while (isRunning)
    {
        sockaddr_in clientAddr;
        int clientSize = sizeof(clientAddr);

        SOCKET clientSocket = accept(serverSocket, (sockaddr *)&clientAddr, &clientSize);

        if (clientSocket == INVALID_SOCKET)
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
        // gets data from client without blocking the main thread
        int bytesReceived = recv(clientSocket, recvBuffer, sizeof(recvBuffer), 0);
        if (bytesReceived > 0)
        {
            std::vector<std::string> messages;
            const bool framingOk = client_protocol::MessageFramer(
                carryBuffer,
                recvBuffer,
                static_cast<size_t>(bytesReceived),
                messages
            );

            if (!framingOk)
            {
                std::cerr << "[ERROR] Framing failed for P" << playerId << ". Closing connection. \n";
                break;
            }
            for (const std::string& rawMessage : messages)
            {
                client_protocol::InitialConnectData metaData;
                std::string responseToSend;

                const bool protocolOk = client_protocol::MessageProtocol(
                    rawMessage,
                    metaData,
                    responseToSend
                );
                if (protocolOk)
                {
                    std::cout << "[JSON] Data received from P" << playerId                 << ":\n";
                    std::cout << "  - ID: "                    << metaData.playerId        << "\n";
                    std::cout << "  - Version: "               << metaData.clientVersion   << "\n";
                    std::cout << "  - State: " << (metaData.isReady ? "Ready" : "Waiting") << "\n";
                }
                else
                {
                    std::cout << "[WARN] Invalid Message from P " << playerId << "\n";
                }

                size_t totalSent = 0;
                while (totalSent < responseToSend.size())
                {
                    const int sent = send(
                        clientSocket,
                        responseToSend.c_str() + totalSent,
                        static_cast<int>(responseToSend.size() - totalSent),
                        0
                    );
                    if (sent == SOCKET_ERROR)
                    {
                        std::cerr << "[ERROR] send() failed for p " << playerId
                                  << "code: " << WSAGetLastError() << '\n';
                        break;
                    }
                    else
                    {
                        totalSent += static_cast<size_t>(sent);       
                    }
                }
                
            }
        }
        else if(bytesReceived == 0)
        {
            std::cout << "[INFO] Player " << playerId << " disconnected.\n";
            break;
        }
        else
        {
            std::cerr << "[ERROR] recv() failed for P" << playerId
                      << " code=" << WSAGetLastError() << "\n";
            break;
        }

    }
    closesocket(clientSocket);        
}