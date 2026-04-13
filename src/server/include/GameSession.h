#pragma once

#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

#include "GameTypes.h"

using games_types::RegisteredClient;
using games_types::CollectorUnit;
using games_types::ResourceNode;
using games_types::UnitPosition;
using games_types::ShopUnit;

class GameSession
{
    private:
        static constexpr int kInitialGold = 500;

        int player1;
        int player2;
        int sessionId;
        std::unordered_map<int, UnitPosition> structures;
        std::unordered_map<int, UnitPosition> units;
        std::unordered_map<int, CollectorUnit> collectors;
        std::unordered_map<int, ResourceNode> resources;
        std::unordered_map<int, ShopUnit> shops;
        std::unordered_map<int, int> playerGold;
        std::unordered_map<int, int> playerGoldSpent;
        std::vector<games_types::EconomyTransaction> pendingEconomyTransactions;
        std::unordered_map<games_types::EntityType, int> unitGoldCostByType;
        std::unordered_map<int, games_types::ShopAuthorizationState> shopAuthorizationByPlayer;
        int nextP1AttackerId = games_types::id_ranges::p1Attackers.minId;
        int nextP1CollectorId = games_types::id_ranges::p1Collectors.minId;
        int nextP2AttackerId = games_types::id_ranges::p2Attackers.minId;
        int nextP2CollectorId = games_types::id_ranges::p2Collectors.minId;
        std::unordered_map<std::string, RegisteredClient> udpClients;
        mutable std::mutex sessionMutex;

    public:
        GameSession(int player1, int player2, int sessionId);
        ~GameSession() = default;

        int getSessionId() const;
        bool hasPlayer(int playerId) const;

        void registerUdpClient(const std::string& clientKey, const RegisteredClient& client);
        bool isUdpClientRegistered(const std::string& clientKey) const;
        std::vector<RegisteredClient> getUdpClientsSnapshot() const;

        void upsertUnitPosition(int id, float x, float y);
        std::vector<UnitPosition> getUnitsSnapshot() const;
        void setUnitsSnapshot(const std::vector<UnitPosition>& newUnits);
        std::vector<CollectorUnit> getCollectorsSnapshot() const;
        void setCollectorsSnapshot(const std::vector<CollectorUnit>& newCollectors);
        bool getCollector(int collectorId, CollectorUnit& outCollector) const;
        bool upsertCollector(const CollectorUnit& collector);
        std::vector<UnitPosition> getStructuresSnapshot() const;
        std::vector<ResourceNode> getResourcesSnapshot() const;
        std::vector<ShopUnit> getShopsSnapshot() const;
        bool getShopAuthorizationState(int playerId, games_types::ShopAuthorizationState& outState) const;
        void setShopAuthorizationState(int playerId, const games_types::ShopAuthorizationState& state);
        void clearShopAuthorizationState(int playerId);
        bool upsertResourceNode(const ResourceNode& node);
        int extractResource(int resourceId, int requestedAmount);

        int getPlayerGold(int playerId) const;
        bool trySpendGold(int playerId, int amount);
        bool addGold(int playerId, int amount);
        int getPlayerSpentGold(int playerId) const;
        std::unordered_map<int, int> getPlayerGoldSnapshot() const;
        std::vector<games_types::EconomyTransaction> drainEconomyTransactions();

        int getUnitGoldCost(games_types::EntityType unitType) const;
        bool isUnitPurchasable(games_types::EntityType unitType) const;
        bool trySpendGoldForUnit(int playerId, games_types::EntityType unitType, int quantity = 1);
        bool allocateUnitId(int playerId, games_types::EntityType unitType, int& outUnitId);
        bool tryPurchaseUnit(
            int playerId,
            games_types::EntityType unitType,
            int quantity,
            int& outUnitId,
            int& outNewBalance,
            std::string& outReason);

        void initializeGameState();
};