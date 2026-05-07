#pragma once

#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
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
        std::unordered_map<int, games_types::StaticObstacle> staticObstacles;
        std::unordered_map<int, int> playerGold;
        std::unordered_map<int, int> playerGoldSpent;
        std::vector<games_types::EconomyTransaction> pendingEconomyTransactions;
        std::unordered_map<int, int> entityCurrentHp;
        std::unordered_map<int, int> entityMaxHp;
        std::unordered_map<games_types::EntityType, int> unitGoldCostByType;
        std::unordered_map<int, games_types::ShopAuthorizationState> shopAuthorizationByPlayer;
        int attackerHp = 100;
        int attackerDamage = 20;
        int attackerRange = 400;
        int attackerCooldownMs = 500;
        int collectorHp = 100;
        int baseHp = 1500;
        int minDamage = 1;
        bool gameOver = false;
        bool arcadeMode = false;

        std::unordered_map<int, UnitPosition> bombs;
        int nextP1BombId = games_types::id_ranges::p1Bombs.minId;
        int nextP2BombId = games_types::id_ranges::p2Bombs.minId;

        // Arcade mode config (loaded from arcade_config.json)
        int arcadeStartingGold = 500;
        int arcadeBombCost = 1000;
        int arcadeAttackerCost = 200;
        int arcadeBombHp = 200;
        int arcadeBombSpeed = 80;
        int arcadeKillGoldPerUnit = 100;
        int arcadeKillGoldPerBomb = 500;
        int arcadeAutoSpawnIntervalMs = 10000;
        int arcadeInitialAttackers = 3;
        int arcadeGameDurationSeconds = 300;
        bool arcadeBaseImmunityToAttackers = true;
        int arcadeExplosionRadius = 250;

        std::chrono::steady_clock::time_point lastAutoSpawnTime;

        // Arcade mode game timer
        std::chrono::steady_clock::time_point gameStartTime;
        std::chrono::steady_clock::time_point lastTimerUpdateTime;
        int gameDurationSeconds = 300;
        bool suddenDeath = false;

        int winnerPlayerId = 0;
        int nextP1AttackerId = games_types::id_ranges::p1Attackers.minId;
        int nextP1CollectorId = games_types::id_ranges::p1Collectors.minId;
        int nextP2AttackerId = games_types::id_ranges::p2Attackers.minId;
        int nextP2CollectorId = games_types::id_ranges::p2Collectors.minId;
        std::unordered_map<std::string, RegisteredClient> udpClients;
        std::unordered_set<int> recentlyDestroyedUnitIds;
        mutable std::mutex sessionMutex;

        int ownerFromEntityId(int entityId) const;
        void loadCombatConfigNoLock();
        void loadArcadeConfigNoLock();

    public:
        GameSession(int player1, int player2, int sessionId, bool arcadeMode = false);
        ~GameSession() = default;

        int getSessionId() const;
        bool hasPlayer(int playerId) const;
        bool isArcadeMode() const { return arcadeMode; }
        bool isBaseImmuneToAttackers() const { return arcadeBaseImmunityToAttackers; }

        void registerUdpClient(const std::string& clientKey, const RegisteredClient& client);
        bool isUdpClientRegistered(const std::string& clientKey) const;
        std::vector<RegisteredClient> getUdpClientsSnapshot() const;

        void upsertUnitPosition(int id, float x, float y);
        std::vector<UnitPosition> getUnitsSnapshot() const;
        void setUnitsSnapshot(const std::vector<UnitPosition>& newUnits);
        void upsertBombPosition(int id, float x, float y);
        std::vector<UnitPosition> getBombsSnapshot() const;
        std::vector<CollectorUnit> getCollectorsSnapshot() const;
        void setCollectorsSnapshot(const std::vector<CollectorUnit>& newCollectors);
        bool getCollector(int collectorId, CollectorUnit& outCollector) const;
        bool upsertCollector(const CollectorUnit& collector);
        std::vector<UnitPosition> getStructuresSnapshot() const;
        std::vector<ResourceNode> getResourcesSnapshot() const;
        std::vector<ShopUnit> getShopsSnapshot() const;
        std::vector<games_types::StaticObstacle> getStaticObstaclesSnapshot() const;
        bool getShopAuthorizationState(int playerId, games_types::ShopAuthorizationState& outState) const;
        void setShopAuthorizationState(int playerId, const games_types::ShopAuthorizationState& state);
        void clearShopAuthorizationState(int playerId);
        bool upsertResourceNode(const ResourceNode& node);
        int extractResource(int resourceId, int requestedAmount);
        bool registerSpawnedUnit(int unitId, int ownerPlayerId, games_types::EntityType unitType);
        bool getEntityPosition(int entityId, UnitPosition& outPosition) const;
        bool getEntityHealth(int entityId, int& outCurrentHp, int& outMaxHp) const;
        bool applyDamageToEntity(int attackerPlayerId,
                     int entityId,
                     int rawDamage,
                     games_types::DamageResolution& outResolution);
        int getBaseEntityId(int playerId) const;
        int getBaseHealth(int playerId) const;
        bool isGameOver(int& outWinnerPlayerId) const;

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

        int getAttackerDamage() const;
        int getAttackerRange() const;
        int getAttackerCooldownMs() const;
        int getMinDamage() const;

        int getArcadeExplosionRadius() const;
        int getArcadeKillGoldPerBomb() const;
        int getArcadeKillGoldPerUnit() const;
        int getArcadeAutoSpawnIntervalMs() const;
        int getArcadeBombHp() const;
        std::chrono::steady_clock::time_point getLastAutoSpawnTime() const;
        void setLastAutoSpawnTime(std::chrono::steady_clock::time_point t);
        void setGameOver(int winnerId);

        std::chrono::steady_clock::time_point getGameStartTime() const;
        int getGameDurationSeconds() const;
        bool isSuddenDeath() const;
        void setSuddenDeath(bool value);
        std::chrono::steady_clock::time_point getLastTimerUpdateTime() const;
        void setLastTimerUpdateTime(std::chrono::steady_clock::time_point t);

        void clearRecentlyDestroyedUnits();
        void initializeGameState();
};