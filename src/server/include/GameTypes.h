#pragma once

#include <chrono>
#include <string>
#include "platform_socket.h"

namespace games_types
{
    struct RegisteredClient // estructura para registrar a los clientes
    {
        sockaddr_in addr;
        std::string sessionId;
        std::chrono::steady_clock::time_point lastSeen;
    };
    struct UnitPosition // estructure para los paquetes udp de cada unidad
    {
        int entity_id;
        float x, y;
    };
}