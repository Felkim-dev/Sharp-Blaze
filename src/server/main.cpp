#include "NetworkManager.h"
#include <iostream>
#include "../include/udpDispatcher.h"

int main(){
    std::cout << "------SHARP BLAZE SERVER ENGINE------" <<std::endl;

    //INICIALIZA UDP DISTPATCHER

    GlobalUDPDispatcher &udpDispatcher = GlobalUDPDispatcher::getInstance();
    if (!udpDispatcher.init())
    {
        std::cerr << "[ERROR] Failed to initialize UDP dispatcher" <<std::endl;
        return 1;
    }
    //inicializa TCP SERVER
    NetworkManager serverRTS(5555);
    serverRTS.start();

    udpDispatcher.shutdown();
    

    return 0;
}
