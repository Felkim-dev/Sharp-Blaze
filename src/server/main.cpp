#include "NetworkManager.h"
#include <iostream>
#include <cstdlib>
#include <cstring>
#include "../include/udpDispatcher.h"

int main(){
    std::cout << "------SHARP BLAZE SERVER ENGINE------" <<std::endl;

    // Read TCP port from environment or use default
    int tcpPort = 5555;
    const char* tcpPortEnv = std::getenv("SHARP_BLAZE_TCP_PORT");
    if (tcpPortEnv) {
        tcpPort = std::atoi(tcpPortEnv);
        std::cout << "[INFO] TCP port from env: " << tcpPort << std::endl;
    }

    // Read session_id from environment for dedicated sessions
    int dedicatedSessionId = 0;
    const char* sessionIdEnv = std::getenv("SHARP_BLAZE_SESSION_ID");
    if (sessionIdEnv) {
        dedicatedSessionId = std::atoi(sessionIdEnv);
        std::cout << "[INFO] Session ID: " << sessionIdEnv << std::endl;
    }

    // Read game mode from environment (arcade / normal)
    bool arcadeMode = false;
    const char* gameModeEnv = std::getenv("SHARP_BLAZE_GAME_MODE");
    if (gameModeEnv && std::strcmp(gameModeEnv, "arcade") == 0) {
        arcadeMode = true;
        std::cout << "[INFO] Game mode: ARCADE" << std::endl;
    }

    //INICIALIZA UDP DISTPATCHER

    GlobalUDPDispatcher &udpDispatcher = GlobalUDPDispatcher::getInstance();
    if (!udpDispatcher.init())
    {
        std::cerr << "[ERROR] Failed to initialize UDP dispatcher" <<std::endl;
        return 1;
    }
    //inicializa TCP SERVER
    NetworkManager serverRTS(tcpPort);
    
    // If this is a dedicated session, initialize it
    if (dedicatedSessionId > 0)
    {
        serverRTS.initializeDedicatedSession(dedicatedSessionId, arcadeMode);
    }
    
    serverRTS.start();

    udpDispatcher.shutdown();
    

    return 0;
}
