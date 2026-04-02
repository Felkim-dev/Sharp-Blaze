#include <chrono>
#include <iostream>
#include <thread>

#include "UDPBroadcaster.h"
#include "platform_socket.h"
#include "GameTypes.h"

KinematicSender::KinematicSender(int udpPort) : udpPort(udpPort), udpSocket(INVALID_SOCKET), isRunning(false), netInitialized(false)
{
    //inicia la libreria apropiada para windows o linux
    netInitialized = net::Init();
    if (!netInitialized)
    {
        std::cerr << "[UDP][ERROR] Socket library init failed.\n";
    }
}

void KinematicSender::setSession(std::shared_ptr<GameSession> sessionRef)
{
    session = std::move(sessionRef);
}

KinematicSender::~KinematicSender()
{
    //cierra los hilos y limpia todo
    stop();
    if (netInitialized)
    {
        net::Cleanup();
        netInitialized = false;
    }
}

void KinematicSender::start()
{
    //corre el bucle principal para udp
    if (isRunning.load())
    {
        std::cerr << "[UDP] KinematicSender already running.\n";
        return;
    }

    if (!netInitialized)
    {
        std::cerr << "[UDP][ERROR] start() aborted: network subsystem not initialized.\n";
        return;
    }
    //crea el socket para udp
    udpSocket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (!net::IsValid(udpSocket))
    {
        std::cerr << "[UDP][ERROR] socket() failed. code=" << net::GetLastError() << '\n';
        return;
    }

    sockaddr_in localAddr{};
    localAddr.sin_family = AF_INET;
    localAddr.sin_port = htons(static_cast<uint16_t>(udpPort));
    localAddr.sin_addr.s_addr = htonl(INADDR_ANY);
    //une el socket del cliente con el del server: bind()
    if (bind(udpSocket, reinterpret_cast<sockaddr*>(&localAddr), sizeof(localAddr)) == SOCKET_ERROR)
    {
        std::cerr << "[UDP][ERROR] bind() failed. code=" << net::GetLastError() << '\n';
        net::CloseSocket(udpSocket);
        udpSocket = INVALID_SOCKET;
        return;
    }
    //setea el canal como nonblocking
    if (!net::SetNonBlocking(udpSocket))
    {
        std::cerr << "[UDP][WARN] SetNonBlocking() failed. code=" << net::GetLastError() << '\n';
    }

    isRunning.store(true);
    workerEmision = std::thread(&KinematicSender::loopEmision, this);
    workerRecepcion = std::thread(&KinematicSender::LoopRecepcion, this);

    std::cout << "[UDP] KinematicSender listening on port " << udpPort << '\n';
}

void KinematicSender::stop()
{
    if (!isRunning.exchange(false))//cambia el isRunning a false para detener el bucle
    {
        return;
    }

    if (workerEmision.joinable()) //cierra el hilo emisor
    {
        workerEmision.join();
    }
    if (workerRecepcion.joinable()) //cierrra el hilo receptor
    {
        workerRecepcion.join();
    }
    if (net::IsValid(udpSocket)) //cierra el socket
    {
        net::CloseSocket(udpSocket);
        udpSocket = INVALID_SOCKET;
    }
}

void KinematicSender::updateData(const std::vector<UnitPosition>& newUnits)
{
    if (session)
    {
        session->setUnitsSnapshot(newUnits);
        return;
    }

    //actualiza la lista de unidades
    std::lock_guard<std::mutex> lock(dataMutex);
    currentUnits = newUnits;
}

void KinematicSender::loopEmision()
{
    const std::chrono::microseconds frameTime(16666);
    
    while(isRunning.load())
    {
        auto t_start = std::chrono::high_resolution_clock::now();

        std::vector<UnitPosition> StructuresSnapshot; //copia los datos de las estructuras de la partida
        std::vector<UnitPosition> UnitsSnapshot; //copia los datos de las unidades de la partida
        std::vector<RegisteredClient> clients;

        if (session)
        {
            UnitsSnapshot = session->getUnitsSnapshot();
            clients = session->getUdpClientsSnapshot();
            //std::cout << sizeof(clients) << '\n';
        }
        else
        {
            std::lock_guard<std::mutex> lock(dataMutex);
            UnitsSnapshot = currentUnits;

            std::lock_guard<std::mutex> clientsLock(clientsMutex);
            clients.reserve(udpClients.size());
            for (const auto& entry : udpClients)
            {
                clients.push_back(entry.second);
                std::cout << entry.first << '\n';
            }
        }

        for(const auto& unit: UnitsSnapshot)
        {
            for (const auto& client : clients)
            {
                sendto(udpSocket,
                    reinterpret_cast<const char*>(&unit),
                    static_cast<int>(sizeof(UnitPosition)),
                    0,
                    reinterpret_cast<const sockaddr*>(&client.addr),
                    sizeof(client.addr));
            }
        }
        //controlar el tiempo para mantener 60hz
        auto t_end = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(t_end - t_start);
        if (elapsed < frameTime)
        {
            std::this_thread::sleep_for(frameTime - elapsed);
        }
    }
}

void KinematicSender::LoopRecepcion()
{
    char buffer[1024];
    sockaddr_in senderAddr; //direccion desde donde estan llegando los paquetes
    socklen_t senderSize = sizeof (senderAddr);
    while (isRunning.load())
    {
        int bytesReceived = recvfrom(udpSocket, buffer,sizeof(buffer),0,
                                    (sockaddr*)&senderAddr, &senderSize);
        if(bytesReceived > 0) //si llega algo de info
        {
            const auto ipNumeric = ntohl(senderAddr.sin_addr.s_addr);
            const int port = ntohs(senderAddr.sin_port);
            std::string clientKey = std::to_string(ipNumeric) + ":" + std::to_string(port);
            bool known = session ? session->isUdpClientRegistered(clientKey) : false;

            if (!session)
            {
                std::lock_guard<std::mutex> lock(clientsMutex);
                known = udpClients.find(clientKey) != udpClients.end();
            }

            if (bytesReceived == static_cast<int>(sizeof(UnitPosition)))
            {
                const UnitPosition* data = reinterpret_cast<const UnitPosition*>(buffer);
                updateInternPosition(data->entity_id, data->x, data->y);
            }
            else if(bytesReceived == 9)
            {
                if (!known)
                {
                    RegisteredClient clientInfo{
                        senderAddr,
                        clientKey,
                        std::chrono::steady_clock::now()};

                    if (session)
                    {
                        session->registerUdpClient(clientKey, clientInfo);
                        std::cout << clientKey << '\n';
                    }
                    else
                    {
                        std::lock_guard<std::mutex> lock(clientsMutex);
                        udpClients[clientKey] = clientInfo;
                    }

                    std::cout << "[UDP] client registered: " << clientKey << '\n';
                }
            }
            else
            {
                std::cerr << "[UDP][WARN] Ignoring packet with unexpected size " << bytesReceived << '\n';
            }
        }
        else
        {
            int err = net::GetLastError();
            if(err == NET_EWOULDBLOCK)
            {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            else
            {
                std::cerr << "[UDP] Reception error" << err << '\n';
            }
        }
    }
    
}

void KinematicSender::updateInternPosition(int id, float x, float y)
{
    if (session)
    {
        session->upsertUnitPosition(id, x, y);
        return;
    }

    std::lock_guard<std::mutex> lock(dataMutex);
    bool found = false;
    for (auto& unit :currentUnits)
    {
        if (unit.entity_id == id)
        {
            unit.x = x;
            unit.y = y;
            found = true;
            break;
        }
    }

    if(!found)
    {
        UnitPosition newUnit;
        newUnit.entity_id = id;
        newUnit.x = x;
        newUnit.y = y;
        currentUnits.push_back(newUnit);
    }
}



// void KinematicSender::sendSnapshotTick()
// {
//     std::vector<UnitPosition> unitsCopy;
//     {
//         std::lock_guard<std::mutex> lock(dataMutex);
//         unitsCopy = currentUnits;
//     }

//     if (unitsCopy.empty())
//     {
//         return;
//     }

//     std::lock_guard<std::mutex> lock(clientsMutex);
//     for (const auto& [playerId, client] : udpClients)
//     {
//         (void)playerId;
//         sendto(
//             udpSocket,
//             reinterpret_cast<const char*>(unitsCopy.data()),
//             static_cast<int>(unitsCopy.size() * sizeof(UnitPosition)),
//             0,
//             reinterpret_cast<const sockaddr*>(&client.addr),
//             sizeof(client.addr));
//     }
// }