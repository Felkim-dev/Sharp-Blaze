#pragma once

#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

#include "GameTypes.h"

using games_types::RegisteredClient;
using games_types::UnitPosition;

class GameSession
{
    private:
        int player1;
        int player2;
        std::string sessionId;
        std::unordered_map<int, UnitPosition> structures;
        std::unordered_map<int, UnitPosition> units;
        std::unordered_map<int, UnitPosition> resources;
        std::unordered_map<std::string, RegisteredClient> udpClients;
        mutable std::mutex sessionMutex;

    public:
        GameSession(int player1, int player2, std::string sessionId);
        ~GameSession() = default;

        std::string getSessionId() const;
        bool hasPlayer(int playerId) const;

        void registerUdpClient(const std::string& clientKey, const RegisteredClient& client);
        bool isUdpClientRegistered(const std::string& clientKey) const;
        std::vector<RegisteredClient> getUdpClientsSnapshot() const;

        void upsertUnitPosition(int id, float x, float y);
        std::vector<UnitPosition> getUnitsSnapshot() const;
        void setUnitsSnapshot(const std::vector<UnitPosition>& newUnits);
        std::vector<UnitPosition> getStructuresSnapshot() const;
        void initializeGameState();
};