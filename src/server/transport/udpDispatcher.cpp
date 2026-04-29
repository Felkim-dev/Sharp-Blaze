#include "../include/udpDispatcher.h"
#include "../include/GameSession.h"
#include "../include/GameTypes.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <cstring>
#include <cstdint>
#include <cstdlib>
#include <vector>


GlobalUDPDispatcher& GlobalUDPDispatcher::getInstance()
{
    static GlobalUDPDispatcher instance;
    return instance;
};

GlobalUDPDispatcher::GlobalUDPDispatcher()
    :udpSocket(INVALID_SOCKET),
    netInitialized(false),
    isRunning(false)
{
    std::cout << "[UDP] GlobalUdpDispatcher constructor" << std::endl;
};

GlobalUDPDispatcher::~GlobalUDPDispatcher()
{
    std::cout << "[UDP] GlobalUdpDispatcher destructor" <<std::endl;
    shutdown();
};


bool GlobalUDPDispatcher::init()
{
    if(isRunning.load())
    {
        std::cerr << "[UDP] Already initialized" <<std::endl;
        return false;
    };

    //Inicializar libreria de sockets
    netInitialized = net::Init();
    if(!netInitialized)
    {
        std::cerr << "[UDP][ERROR] Socket library init failed" <<std::endl;
        return false;
    }

    if (!createSocket())
    {
        net::Cleanup();
        netInitialized = false;
        return false;
    }

    //marcar el running
    isRunning.store(true);

    //inicializar hilos de recepcion y emision
    workerRecepcion = std::thread(&GlobalUDPDispatcher::loopRecepcion,this);
    workerEmision = std::thread(&GlobalUDPDispatcher::loopEmision, this);
    std::cout << "[UDP] GlobalUDPDistpatcher initialized succesfully" << std::endl;
    return true;
};

void GlobalUDPDispatcher::shutdown()
{
    if(!isRunning.exchange(false))
    {
        return;
    }
    std::cout << "[UDP] shutting down GlobalUDPDispatcher" <<std::endl;
    
    if(workerRecepcion.joinable())
    {
        workerRecepcion.join();
    }
    if(workerEmision.joinable())
    {
        workerEmision.join();
    }
    closeSocket();
    //limpiar libreria de sockets
    if(netInitialized)
    {
        net::Cleanup();
        netInitialized = false;
    }
    std::cout << "[UDP] GlobaUDPDistpatcher shutdown complete" <<std::endl;
};

bool GlobalUDPDispatcher::createSocket()
{
    udpSocket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if(!net::IsValid(udpSocket))
    {
        std::cerr << "[UDP][ERROR] socket failed.code=" << net::GetLastError() << std::endl;
        return false;
    }

    // Read UDP port from environment or use default
    int udpPort = 5556;
    const char* udpPortEnv = std::getenv("SHARP_BLAZE_UDP_PORT");
    if (udpPortEnv) {
        udpPort = std::atoi(udpPortEnv);
        std::cout << "[UDP] UDP port from env: " << udpPort << std::endl;
    }

    //preparar la direccion local

    sockaddr_in localAddr{};
    localAddr.sin_family = AF_INET;
    localAddr.sin_port = htons(udpPort);
    localAddr.sin_addr.s_addr = htonl (INADDR_ANY);

    //Bind al puerto dinámico
    if(bind(udpSocket, reinterpret_cast<sockaddr*>(&localAddr),sizeof(localAddr)) == SOCKET_ERROR)
    {
        std::cerr << "[UDP][ERROR] bind failed on port " << udpPort << ". code=" << net::GetLastError() << std::endl;
        net::CloseSocket(udpSocket);
        udpSocket = INVALID_SOCKET;
        return false;
    }
    //no-blocking mode
    if(!net::SetNonBlocking(udpSocket))
    {
        std::cerr << "[UDP][ERROR] SetNonBlocking failed. code=" << net::GetLastError() << std::endl;
    }
    std::cout << "[UDP] Socket created successfully on port " << udpPort << std::endl;
    return true;
};

void GlobalUDPDispatcher::closeSocket()
{
    if(net::IsValid(udpSocket))
    {
        net::CloseSocket(udpSocket);
        udpSocket = INVALID_SOCKET;
        std::cout << "[UDP] Socket closed" << std::endl;
    }
    return;
};

bool GlobalUDPDispatcher::tryParseUdpHello(const char* buffer, int size,
                                              games_types::UdpHelloMessage& out)
{
    // Binary format:
    // [sessionId: 4 bytes][playerId: 4 bytes][checksum: 4 bytes] (network byte order)
    const int expectedSize = 4 + 4 + 4;
    
    if (size != expectedSize)
    {
        std::cerr << "[UDP][WARN] UDP_HELLO packet wrong size: expected " << expectedSize 
                  << " got " << size << std::endl;
        return false;
    }

    std::uint32_t sessionNet = 0;
    std::uint32_t playerNet = 0;
    std::uint32_t checksumNet = 0;

    std::memcpy(&sessionNet, buffer, 4);
    std::memcpy(&playerNet, buffer + 4, 4);
    std::memcpy(&checksumNet, buffer + 8, 4);

    const int sessionId = static_cast<int>(ntohl(sessionNet));
    const int playerId = static_cast<int>(ntohl(playerNet));
    const std::uint32_t checksumReceived = ntohl(checksumNet);

    // Validate checksum using the first 8 bytes (sessionId + playerId in network order).
    std::uint32_t checksumComputed = 0;
    for (int i = 0; i < 8; ++i)
    {
        checksumComputed ^= static_cast<std::uint8_t>(buffer[i]);
    }

    if (checksumComputed != checksumReceived)
    {
        std::cerr << "[UDP][WARN] UDP_HELLO checksum mismatch: expected 0x"
                  << std::hex << checksumComputed
                  << " got 0x" << checksumReceived << std::dec << std::endl;
        return false;
    }

    out.playerId = playerId;
    out.sessionId = sessionId;
    out.checksum = checksumReceived;
    return true;
}

void GlobalUDPDispatcher::pruneStaleEndpointsLocked()
{
    const auto now = std::chrono::steady_clock::now();
    constexpr auto kEndpointTimeout = std::chrono::seconds(3600);

    for (auto& sessionPair : activeSessions)
    {
        auto& endpoints = sessionPair.second.endpointsByPlayer;
        for (auto it = endpoints.begin(); it != endpoints.end(); )
        {
            if (now - it->second.lastSeen > kEndpointTimeout)
            {
                std::cerr << "[UDP][WARN] endpoint expired: session=" << sessionPair.first
                          << " player=" << it->second.playerId << std::endl;
                it = endpoints.erase(it);
            }
            else
            {
                ++it;
            }
        }
    }
}

void GlobalUDPDispatcher::loopRecepcion()
{
    std::cout << "[UDP] loopRecepcion thread started" << std::endl;
    
    char buffer[1024];
    sockaddr_in senderAddr;
    socklen_t senderSize = sizeof(senderAddr);

    while(isRunning.load())
    {
        int bytesReceived = recvfrom(udpSocket, buffer, sizeof(buffer), 0,
                                     reinterpret_cast<sockaddr *>(&senderAddr), &senderSize);
        
        if(bytesReceived > 0)
        {
            games_types::UdpHelloMessage hello;
            if (tryParseUdpHello(buffer, bytesReceived, hello))
            {
                std::cout << "[UDP] Valid UDP_HELLO: sessionId=" << hello.sessionId
                          << " playerId=" << hello.playerId << std::endl;
                registerEndpoint(hello, senderAddr);
            }
            else
            {
                const auto ipNumeric = ntohl(senderAddr.sin_addr.s_addr);
                const int port = ntohs(senderAddr.sin_port);
                std::string clientKey = std::to_string(ipNumeric) + ":" + std::to_string(port);
                std::cerr << "[UDP][WARN] Invalid UDP_HELLO from " << clientKey << std::endl;
            }
        }
        else
        {
            int err = net::GetLastError();
            if(err != NET_EWOULDBLOCK)
            {
                std::cerr << "[UDP][WARN] recvfrom() error: " << err << std::endl;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(1));

        }
    }
    std::cout << "[UDP] loopRecepcion thread exiting" <<std::endl;
};

void GlobalUDPDispatcher::loopEmision() {
    const std::chrono::microseconds frameTime(16666);

    struct BroadcastBatch
    {
        int sessionId;
        std::shared_ptr<GameSession> session;
        std::vector<games_types::UdpEndpoint> endpoints;
    };

    while (isRunning.load())
    {
        auto t_start = std::chrono::high_resolution_clock::now();

        std::vector<BroadcastBatch> pendingBroadcasts;
        {
            std::lock_guard<std::mutex> lock(sessionsMutex);
            pruneStaleEndpointsLocked();
            pendingBroadcasts.reserve(activeSessions.size());

            for (const auto& sessionPair : activeSessions)
            {
                const int& sessionId = sessionPair.first;
                const SessionRegistration& reg = sessionPair.second;

                if (!reg.session || reg.endpointsByPlayer.empty())
                {
                    continue;
                }

                BroadcastBatch batch;
                batch.sessionId = sessionId;
                batch.session = reg.session;
                batch.endpoints.reserve(reg.endpointsByPlayer.size());

                for (const auto& endpointPair : reg.endpointsByPlayer)
                {
                    batch.endpoints.push_back(endpointPair.second);
                }

                pendingBroadcasts.push_back(std::move(batch));
            }
        }

        for (const auto& batch : pendingBroadcasts)
        {
            if (!batch.session)
            {
                continue;
            }

            const auto units = batch.session->getUnitsSnapshot();
            if (units.empty())
            {
                continue;
            }

            // Lambda to convert world coordinates to grid coordinates
            constexpr float kCellSize = 50.0f;
            constexpr int kGridMaxIndex = 99;
            
            auto worldToGrid = [](float value) -> int {
                int cell = static_cast<int>(value / kCellSize);
                if (cell < 0)
                {
                    return 0;
                }
                if (cell > kGridMaxIndex)
                {
                    return kGridMaxIndex;
                }
                return cell;
            };

            for (const auto& unit : units)
            {
                // Convert world coordinates to grid before sending
                games_types::UnitPosition gridUnit = unit;
                gridUnit.x = static_cast<float>(worldToGrid(unit.x));
                gridUnit.y = static_cast<float>(worldToGrid(unit.y));

                for (const auto& endpoint : batch.endpoints)
                {
                    const int sentBytes = sendto(
                        udpSocket,
                        reinterpret_cast<const char*>(&gridUnit),
                        static_cast<int>(sizeof(games_types::UnitPosition)),
                        0,
                        reinterpret_cast<const sockaddr*>(&endpoint.addr),
                        sizeof(endpoint.addr));
                    if (sentBytes != 12)
                    {
                        std::cout << "se envio algo pero no mide 12" << std::endl;
                    }
                    if (sentBytes == 12)
                    {
                        std::cout << "Si envio algo" << std::endl;
                    }
                    if (sentBytes < 0)
                    {
                        const int err = net::GetLastError();
                        if (err != NET_EWOULDBLOCK)
                        {
                            std::cerr << "[UDP][WARN] sendto() failed for session=" << batch.sessionId
                                      << " player=" << endpoint.playerId
                                      << " error=" << err << std::endl;
                        }
                    }
                }
            }
        }

        auto t_end = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(t_end - t_start);
        if (elapsed < frameTime)
        {
            std::this_thread::sleep_for(frameTime - elapsed);
        }
    }
    std::cout << "[UDP] loopEmision thread exiting" << std::endl;
};

/*
API PARA SESIONES
*/

void GlobalUDPDispatcher::onSessionStarted(
    const int& sessionId,
    int p1InternalPlayerId,
    int p2InternalPlayerId,
    std::shared_ptr<GameSession> session)
{
    (void)p1InternalPlayerId;
    (void)p2InternalPlayerId;

    std::lock_guard<std::mutex> lock(sessionsMutex);
    activeSessions[sessionId].session = std::move(session);
    std::cout << "[UDP] Session started: " << sessionId << std::endl;
}

void GlobalUDPDispatcher::onSessionClosed(const int& sessionId)
{
    std::lock_guard<std::mutex> lock(sessionsMutex);
    activeSessions.erase(sessionId);
    std::cout << "[UDP] Session closed: " << sessionId << std::endl;
}

void GlobalUDPDispatcher::registerEndpoint(
    const games_types::UdpHelloMessage& hello,
    const sockaddr_in& address)
{
    std::lock_guard<std::mutex> lock(sessionsMutex);

    auto sessionIt = activeSessions.find(hello.sessionId);
    if (sessionIt == activeSessions.end())
    {
        std::cerr << "[UDP][WARN] registerEndpoint ignored for unknown session: "
                  << hello.sessionId << std::endl;
        return;
    }

    games_types::UdpEndpoint endpoint{};
    endpoint.addr = address;
    endpoint.sessionId = hello.sessionId;
    endpoint.playerId = hello.playerId;
    endpoint.lastSeen = std::chrono::steady_clock::now();

    sessionIt->second.endpointsByPlayer[hello.playerId] = std::move(endpoint);

    std::cout << "[UDP] endpoint registered: session=" << hello.sessionId
              << " player=" << hello.playerId << std::endl;
}

void GlobalUDPDispatcher::unregisterEndpoint(
    const int& sessionId,
    int playerId)
{
    std::lock_guard<std::mutex> lock(sessionsMutex);

    auto sessionIt = activeSessions.find(sessionId);
    if (sessionIt == activeSessions.end())
    {
        return;
    }

    sessionIt->second.endpointsByPlayer.erase(playerId);
    std::cout << "[UDP] endpoint unregistered: session=" << sessionId
              << " player=" << playerId << std::endl;
}

std::shared_ptr<GameSession> GlobalUDPDispatcher::getSession(const int& sessionId) const
{
    std::lock_guard<std::mutex> lock(sessionsMutex);
    auto it = activeSessions.find(sessionId);
    if (it != activeSessions.end())
    {
        return it->second.session;
    }
    return nullptr;
}