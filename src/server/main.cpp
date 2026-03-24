#include <iostream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <thread>
#include <vector>

#ifdef _MSC_VER
#pragma comment(lib, "Ws2_32.lib")
#endif


//Client handler function

void handleClient(SOCKET clientSocket, int playerId){
    std::cout << "[INFO] Player" << playerId << "connected. Hearing in other thread.\n";
    
    char buffer[1024];
    while (true){
        ZeroMemory(buffer, 1024);

        //gets data from client without blocking the main thread
        int bytesReceived = recv(clientSocket, buffer, 1024, 0);
        if (bytesReceived > 0){
            std::cout << "[P" << playerId << " TCP. Message received: " << buffer << "\n";
            // Echo the message back to the client
            send(clientSocket, buffer, bytesReceived, 0);
        } else if (bytesReceived == 0){
            std::cout << "[INFO] Player" << playerId << "disconnected.\n";
            break;
        } else {
            std::cerr << "[ERROR] recv failed for Player" << playerId << ".\n";
            break;
        }
    }
    closesocket(clientSocket);
}

int main(){

    //Initialize WSA variables
    WSADATA wsaData;

    //request winsock version 2.2
    if(WSAStartup(MAKEWORD(2, 2), &wsaData) != 0){
        std::cerr << "[ERROR] WSAStartup failed.\n";
        return 1;
    }

    //Socket creation and binding
    SOCKET serverSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (serverSocket == INVALID_SOCKET){
        std::cerr << "[ERROR] Socket creation failed.\n";
        WSACleanup();
        return 1;
    }
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(5555);
    serverAddr.sin_addr.s_addr = INADDR_ANY;

    //bind the socket to the address and port
    if (bind(serverSocket, (sockaddr*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR){
        std::cerr << "[ERROR] Socket bind failed.\n";
        closesocket(serverSocket);
        WSACleanup();
        return 1;
    }

    //listen for incoming connections
    if (listen(serverSocket, SOMAXCONN) == SOCKET_ERROR){
        std::cerr << "[ERROR] Listen failed.\n";
        closesocket(serverSocket);
        WSACleanup();
        return 1;
    }
    std::cout << "[INFO] Server is listening on port 5555...\n";
    int playerIdCounter = 1;

    //main loop to accept clients
    while (true){
        sockaddr_in clientAddr;
        int clientSize = sizeof(clientAddr);

        SOCKET clientSocket = accept(serverSocket, (sockaddr*)&clientAddr, &clientSize);
    
        if (clientSocket == INVALID_SOCKET){
            std::cerr << "[ERROR] Accept failed.\n";
            continue;
        }
        std::thread(handleClient, clientSocket, playerIdCounter).detach();
        playerIdCounter++;

    }

    //cleanup
    closesocket(serverSocket);
    WSACleanup();
    return 0;
}