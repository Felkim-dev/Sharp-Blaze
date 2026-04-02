#pragma once

#include <chrono>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>
#include <thread>
#include <atomic>
#include <memory>

#include "platform_socket.h"
#include "GameTypes.h"
#include "GameSession.h"

using games_types::UnitPosition;
using games_types::RegisteredClient;


class KinematicSender
{
    public:
        KinematicSender(int udpPort); //constructor
        ~KinematicSender(); //destructor

        void start(); //inicia a correr los bucles
        void stop(); //detiene los hilos corriendo
        void setSession(std::shared_ptr<GameSession> sessionRef);
        void updateData(const std::vector<UnitPosition>& newUnits); //actualiza las posiciones de una partida
    
    private:

        int udpPort; //puerto para el protocolo udp
        void loopEmision(); //loop corriendo en su propio hilo que envia los paquetes udp a 60hz
        void LoopRecepcion(); //loop corriendo en su propio hilo que registra clientes udp y actualiza posiciones por jugador
        void updateInternPosition(int id, float x, float y);
        void sendSnapshotTick();

        SOCKET udpSocket; //SI
        std::atomic<bool> isRunning;//si
        std::thread workerEmision; //hilo dedicado a enviar datos a 60hz
        std::thread workerRecepcion; //hilo dedicado a escuchar actualizaciones de los cientes
        bool netInitialized; //se usa en el start
        std::shared_ptr<GameSession> session;

        std::vector<UnitPosition> currentUnits; //lista de posiciones a enviar por cada rafaga
        std::mutex dataMutex; // lock para evitar que multiples hilos modifiquen el mismo dato

        std::unordered_map<std::string, RegisteredClient> udpClients; //diccionario que asocia el ID del jugador con su IP y puerto UDP
        std::mutex clientsMutex; //lock para evitar modificar lista de clientes
};