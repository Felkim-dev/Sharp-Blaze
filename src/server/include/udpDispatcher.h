#pragma once

#include <atomic>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "platform_socket.h"
#include "GameSession.h"
#include "GameTypes.h"

/*
Esta clase se implemento para resolver un bug al momento de tener multiples sesiones
lo que busca es globalizar el uso de el UDP socket 
multiplexa por session_id 
*/


class GlobalUDPDispatcher
{
    public:
    //unica instancia del puerto que es de acceso global: singleton
        static GlobalUDPDispatcher& getInstance();

        bool init();
        void shutdown();

        //API para las sesiones 
        void onSessionStarted(const int& sessionId,
                            int p1InternalPlayerId,
                            int p2InternalPlayerId,
                            std::shared_ptr<GameSession> session);
        void onSessionClosed(const int& sessionId);

        //API de endpoint
        void registerEndpoint(const games_types::UdpHelloMessage& hello,
                              const sockaddr_in& address);
        void unregisterEndpoint(const int& sessionId, int playerId);

        //acceso a la session
        std::shared_ptr<GameSession> getSession(const int& sessionId) const;

    private:
        GlobalUDPDispatcher();
        ~GlobalUDPDispatcher();

        //borrar el copy/assign
        GlobalUDPDispatcher(const GlobalUDPDispatcher&) = delete;
        GlobalUDPDispatcher& operator=(const GlobalUDPDispatcher&) = delete;

        //socket management
        bool createSocket();
        void closeSocket();

        //thread loops()
        void loopRecepcion();
        void loopEmision();

        //UDP_HELLO parsing
        bool tryParseUdpHello(const char* buffer, int size, 
                              games_types::UdpHelloMessage& out);
        void pruneStaleEndpointsLocked();

        //internal state
        SOCKET udpSocket;
        bool netInitialized;
        std::atomic <bool> isRunning;

        std::thread workerRecepcion;
        std::thread workerEmision;

        struct SessionRegistration
        {
            std::shared_ptr<GameSession> session;
            std::unordered_map<int, games_types::UdpEndpoint> endpointsByPlayer;
        };

        std::unordered_map<int, SessionRegistration> activeSessions;
        mutable std::mutex sessionsMutex;


};
