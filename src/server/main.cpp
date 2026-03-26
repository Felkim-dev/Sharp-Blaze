#include "NetworkManager.h"
#include <iostream>

int main(){
    std::cout << "------SHARP BLAZE SERVER ENGINE------\n";
    
    NetworkManager serverRTS(555);

    //Initialize server 
    serverRTS.start();
    

    return 0;
}
