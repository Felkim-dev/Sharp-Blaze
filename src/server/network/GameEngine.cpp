#include "GameEngine.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>
#include <vector>

#include "GameSession.h"
#include "PathFinder.h"

namespace
{
    constexpr float kCollectorCollisionRadius = 15.0f;
    constexpr float kBaseCollisionRadius = 215.0f;

    float distanceSquared(float x1, float y1, float x2, float y2)
    {
        const float dx = x1 - x2;
        const float dy = y1 - y2;
        return (dx * dx) + (dy * dy);
    }

    bool circlesIntersect(float x1, float y1, float radius1,
                          float x2, float y2, float radius2)
    {
        const float radiusSum = radius1 + radius2;
        return distanceSquared(x1, y1, x2, y2) <= (radiusSum * radiusSum);
    }

    bool getPlayerBaseCenter(const std::vector<games_types::UnitPosition>& structures,
                             int ownerPlayerId,
                             games_types::UnitPosition& outBase)
    {
        for (const auto& structure : structures)
        {
            if (ownerPlayerId == 1 && games_types::id_ranges::p1Structures.contains(structure.entity_id))
            {
                outBase = structure;
                return true;
            }

            if (ownerPlayerId == 2 && games_types::id_ranges::p2Structures.contains(structure.entity_id))
            {
                outBase = structure;
                return true;
            }
        }

        return false;
    }

    bool isPurchasableTroop(games_types::EntityType unitType)
    {
        return unitType == games_types::EntityType::Attacker ||
               unitType == games_types::EntityType::Collector;
    }

    bool findShopAuthorizationState(const std::vector<games_types::UnitPosition>& units,
                                    const std::vector<games_types::ShopUnit>& shops,
                                    int playerId,
                                    games_types::ShopAuthorizationState& outState)
    {
        outState = games_types::ShopAuthorizationState{};

        for (const auto& unit : units)
        {
            if (!games_types::isPlayerControllableUnitId(playerId, unit.entity_id))
            {
                continue;
            }

            for (const auto& shop : shops)
            {
                if (circlesIntersect(unit.x, unit.y, 0.0f, shop.x, shop.y, shop.radius))
                {
                    outState.authorized = true;
                    outState.shopId = shop.entityId;
                    outState.unitId = unit.entity_id;
                    return true;
                }
            }
        }

        return false;
    }
}

GameEngine::GameEngine(std::shared_ptr<GameSession> sessionRef,
                       std::shared_ptr<PathFinder> pathFinderRef)
    : session(std::move(sessionRef)),
      pathFinder(std::move(pathFinderRef))
{
    if (!pathFinder)
    {
        pathFinder = std::make_shared<PathFinder>();
    }
}

void GameEngine::tcpCommandEnqueue(const games_types::PlayerCommand& cmd)
{
    std::lock_guard<std::mutex> lock(mtxCommands);
    commandQueue.push(cmd);
}

void GameEngine::commandQueueProcess()
{
    std::queue<games_types::PlayerCommand> pendingCommands;
    {
        std::lock_guard<std::mutex> lock(mtxCommands);
        std::swap(pendingCommands, commandQueue);
    }

    while (!pendingCommands.empty())
    {
        const games_types::PlayerCommand cmd = pendingCommands.front();
        pendingCommands.pop();

        if (!propertyValidation(cmd.playerId, cmd.unitId))
        {
            continue;
        }

        setNewRoute(cmd);
    }
}

void GameEngine::advanceCollectors(int deltaMs)
{
    if (!session || deltaMs <= 0)
    {
        return;
    }

    std::vector<games_types::CollectorUnit> collectors = session->getCollectorsSnapshot();
    if (collectors.empty())
    {
        return;
    }

    const std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    const std::vector<games_types::ResourceNode> resources = session->getResourcesSnapshot();
    const std::vector<games_types::UnitPosition> structures = session->getStructuresSnapshot();

    for (auto& collector : collectors)
    {
        auto unitIt = std::find_if(
            units.begin(),
            units.end(),
            [collectorId = collector.entityId](const games_types::UnitPosition& unit) {
                return unit.entity_id == collectorId;
            });
        if (unitIt != units.end())
        {
            collector.x = unitIt->x;
            collector.y = unitIt->y;
        }

        if (collector.stateTimeRemainingMs > 0)
        {
            collector.stateTimeRemainingMs = std::max(0, collector.stateTimeRemainingMs - deltaMs);
        }

        if (collector.state == games_types::CollectorState::Gathering && collector.stateTimeRemainingMs == 0)
        {
            if (collector.targetResourceId > 0)
            {
                collector.carriedAmount = session->extractResource(collector.targetResourceId, collector.carryCapacity);
            }
            else
            {
                collector.carriedAmount = 0;
            }
            collector.state = games_types::CollectorState::Returning;
        }

        if (collector.state == games_types::CollectorState::Idle)
        {
            if (collector.targetResourceId <= 0)
            {
                float nearestDistSq = std::numeric_limits<float>::max();
                for (const auto& node : resources)
                {
                    if (node.remainingCapacity <= 0)
                    {
                        continue;
                    }

                    const float distSq = distanceSquared(collector.x, collector.y, node.x, node.y);
                    if (distSq < nearestDistSq)
                    {
                        nearestDistSq = distSq;
                        collector.targetResourceId = node.entityId;
                    }
                }
            }

            auto targetIt = std::find_if(
                resources.begin(),
                resources.end(),
                [targetId = collector.targetResourceId](const games_types::ResourceNode& node) {
                    return node.entityId == targetId;
                });

            if (targetIt != resources.end() && targetIt->remainingCapacity > 0)
            {
                if (circlesIntersect(collector.x, collector.y, kCollectorCollisionRadius,
                                     targetIt->x, targetIt->y, targetIt->radius))
                {
                    collector.state = games_types::CollectorState::Gathering;
                    collector.stateTimeRemainingMs = collector.gatherDurationMs;
                }
            }
        }

        if (collector.state == games_types::CollectorState::Returning && collector.carriedAmount > 0)
        {
            games_types::UnitPosition basePos{};
            if (getPlayerBaseCenter(structures, collector.ownerPlayerId, basePos) &&
                circlesIntersect(collector.x, collector.y, kCollectorCollisionRadius,
                                 basePos.x, basePos.y, kBaseCollisionRadius))
            {
                collector.state = games_types::CollectorState::Depositing;
                collector.stateTimeRemainingMs = collector.depositDurationMs;
                
            }
        }

        if (collector.state == games_types::CollectorState::Depositing && collector.stateTimeRemainingMs == 0)
        {
            if (collector.carriedAmount > 0)
            {
                session->addGold(collector.ownerPlayerId, collector.carriedAmount);
            }
            collector.carriedAmount = 0;
            collector.state = games_types::CollectorState::Idle;
            collector.targetResourceId = -1;
        }
    }

    session->setCollectorsSnapshot(collectors);
}

std::vector<games_types::EconomyTransaction> GameEngine::drainEconomyTransactions()
{
    if (!session)
    {
        return {};
    }

    return session->drainEconomyTransactions();
}

void GameEngine::advanceCombat(int deltaMs)
{
    if (!session || deltaMs <= 0)
    {
        return;
    }

    int winnerPlayerId = 0;
    if (session->isGameOver(winnerPlayerId))
    {
        return;
    }

    const int attackerRange = session->getAttackerRange();
    const float attackerRangeSq = static_cast<float>(attackerRange * attackerRange);
    const int attackerDamage = std::max(session->getMinDamage(), session->getAttackerDamage());
    const int cooldownMs = session->getAttackerCooldownMs();

    const std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    for (const auto& attacker : units)
    {
        const bool isP1Attacker = games_types::id_ranges::p1Attackers.contains(attacker.entity_id);
        const bool isP2Attacker = games_types::id_ranges::p2Attackers.contains(attacker.entity_id);
        if (!isP1Attacker && !isP2Attacker)
        {
            continue;
        }

        int currentHp = 0;
        int maxHp = 0;
        if (!session->getEntityHealth(attacker.entity_id, currentHp, maxHp) || currentHp <= 0)
        {
            continue;
        }

        int& remainingCooldown = attackerCooldownRemainingMs[attacker.entity_id];
        remainingCooldown = std::max(0, remainingCooldown - deltaMs);
        if (remainingCooldown > 0)
        {
            continue;
        }

        const int ownerPlayerId = isP1Attacker ? 1 : 2;
        int bestTargetId = -1;
        float bestDistSq = std::numeric_limits<float>::max();

        for (const auto& candidate : units)
        {
            if (candidate.entity_id == attacker.entity_id)
            {
                continue;
            }

            if (ownerPlayerId == 1)
            {
                if (!games_types::id_ranges::p2Attackers.contains(candidate.entity_id) &&
                    !games_types::id_ranges::p2Collectors.contains(candidate.entity_id))
                {
                    continue;
                }
            }
            else
            {
                if (!games_types::id_ranges::p1Attackers.contains(candidate.entity_id) &&
                    !games_types::id_ranges::p1Collectors.contains(candidate.entity_id))
                {
                    continue;
                }
            }

            int targetHp = 0;
            int targetMaxHp = 0;
            if (!session->getEntityHealth(candidate.entity_id, targetHp, targetMaxHp) || targetHp <= 0)
            {
                continue;
            }

            const float distSq = distanceSquared(attacker.x, attacker.y, candidate.x, candidate.y);
            if (distSq <= attackerRangeSq && distSq < bestDistSq)
            {
                bestDistSq = distSq;
                bestTargetId = candidate.entity_id;
            }
        }

        if (bestTargetId < 0)
        {
            const int enemyBaseId = ownerPlayerId == 1 ? games_types::id_ranges::p2Structures.minId
                                                       : games_types::id_ranges::p1Structures.minId;
            games_types::UnitPosition enemyBasePos{};
            if (session->getEntityPosition(enemyBaseId, enemyBasePos))
            {
                const float distSq = distanceSquared(attacker.x, attacker.y, enemyBasePos.x, enemyBasePos.y);
                if (distSq <= attackerRangeSq)
                {
                    bestTargetId = enemyBaseId;
                }
            }
        }

        if (bestTargetId < 0)
        {
            continue;
        }

        games_types::DamageResolution resolution{};
        if (!session->applyDamageToEntity(ownerPlayerId, bestTargetId, attackerDamage, resolution) || !resolution.applied)
        {
            continue;
        }

        remainingCooldown = cooldownMs;

        {
            std::lock_guard<std::mutex> lock(mtxCombatEvents);

            games_types::CombatEvent damagedEvent{};
            damagedEvent.type = games_types::CombatEventType::UnitDamaged;
            damagedEvent.sessionId = session->getSessionId();
            damagedEvent.attackerPlayerId = ownerPlayerId;
            damagedEvent.attackerEntityId = attacker.entity_id;
            damagedEvent.targetEntityId = resolution.entityId;
            damagedEvent.targetPlayerId = resolution.ownerPlayerId;
            damagedEvent.currentHp = resolution.currentHp;
            damagedEvent.maxHp = resolution.maxHp;
            pendingCombatEvents.push_back(damagedEvent);

            if (resolution.destroyed)
            {
                games_types::CombatEvent destroyedEvent{};
                destroyedEvent.type = games_types::CombatEventType::EntityDestroyed;
                destroyedEvent.sessionId = session->getSessionId();
                destroyedEvent.attackerPlayerId = ownerPlayerId;
                destroyedEvent.targetEntityId = resolution.entityId;
                destroyedEvent.targetPlayerId = resolution.ownerPlayerId;
                destroyedEvent.attackerEntityId = attacker.entity_id;
                pendingCombatEvents.push_back(destroyedEvent);
            }

            if (resolution.gameOver)
            {
                games_types::CombatEvent gameOverEvent{};
                gameOverEvent.type = games_types::CombatEventType::GameOver;
                gameOverEvent.sessionId = session->getSessionId();
                gameOverEvent.winnerPlayerId = resolution.winnerPlayerId;
                pendingCombatEvents.push_back(gameOverEvent);
            }
        }
    }
}

std::vector<games_types::CombatEvent> GameEngine::drainCombatEvents()
{
    std::lock_guard<std::mutex> lock(mtxCombatEvents);
    std::vector<games_types::CombatEvent> out;
    out.swap(pendingCombatEvents);
    return out;
}

bool GameEngine::reconcileShopAuthorization(int playerId, games_types::ShopAuthorizationState& outState)
{
    outState = games_types::ShopAuthorizationState{};
    if (!session || !session->hasPlayer(playerId))
    {
        return false;
    }

    const std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    const std::vector<games_types::ShopUnit> shops = session->getShopsSnapshot();
    findShopAuthorizationState(units, shops, playerId, outState);

    games_types::ShopAuthorizationState previousState{};
    const bool hadPrevious = session->getShopAuthorizationState(playerId, previousState);
    const bool changed = hadPrevious
        ? (previousState.authorized != outState.authorized ||
           previousState.shopId != outState.shopId ||
           previousState.unitId != outState.unitId)
        : outState.authorized;

    if (outState.authorized)
    {
        session->setShopAuthorizationState(playerId, outState);
    }
    else
    {
        session->clearShopAuthorizationState(playerId);
    }

    return changed;
}

bool GameEngine::hasShopAuthorization(int playerId) const
{
    if (!session || !session->hasPlayer(playerId))
    {
        return false;
    }

    games_types::ShopAuthorizationState state{};
    return session->getShopAuthorizationState(playerId, state) && state.authorized;
}

GameEngine::PurchaseResult GameEngine::processUnitPurchase(
    int playerId,
    games_types::EntityType unitType,
    int quantity)
{
    PurchaseResult result;
    result.unitType = unitType;

    if (!session || !session->hasPlayer(playerId))
    {
        result.reason = "invalid_player";
        return result;
    }

    if (!isPurchasableTroop(unitType))
    {
        result.reason = "unit_type_not_purchasable";
        return result;
    }

    if (!hasShopAuthorization(playerId))
    {
        result.reason = "shop_not_authorized";
        return result;
    }

    const std::vector<games_types::UnitPosition> structures = session->getStructuresSnapshot();
    games_types::UnitPosition basePos{};
    if (!getPlayerBaseCenter(structures, playerId, basePos))
    {
        result.reason = "base_not_found";
        return result;
    }

    int unitId = -1;
    int newBalance = 0;
    std::string reason;
    if (!session->tryPurchaseUnit(playerId, unitType, quantity, unitId, newBalance, reason))
    {
        result.reason = reason;
        return result;
    }

    const float angleStep = 0.55f;
    const float radius = 45.0f;
    const float angle = static_cast<float>(unitId % 11) * angleStep;
    //const float spawnX = basePos.x + radius * std::cos(angle);
    const float spawnX = 2500.0;
    //const float spawnY = basePos.y + radius * std::sin(angle);
    const float spawnY = 2000.0;

    session->upsertUnitPosition(unitId, spawnX, spawnY);
    session->registerSpawnedUnit(unitId, playerId, unitType);
    if (unitType == games_types::EntityType::Collector)
    {
        games_types::CollectorUnit collector{};
        collector.entityId = unitId;
        collector.ownerPlayerId = playerId;
        collector.state = games_types::CollectorState::Idle;
        collector.x = spawnX;
        collector.y = spawnY;
        collector.targetResourceId = -1;
        collector.carriedAmount = 0;
        collector.carryCapacity = 200;
        collector.gatherDurationMs = 1000;
        collector.depositDurationMs = 500;
        collector.stateTimeRemainingMs = 0;
        if (!session->upsertCollector(collector))
        {
            result.reason = "collector_spawn_failed";
            return result;
        }
    }

    result.success = true;
    result.reason = "ok";
    result.unitId = unitId;
    result.spawnX = spawnX;
    result.spawnY = spawnY;
    result.newBalance = newBalance;
    return result;
}

bool GameEngine::propertyValidation(int playerId, int unitId) const
{
    if (!session || !session->hasPlayer(playerId))
    {
        return false;
    }

    return games_types::isPlayerControllableUnitId(playerId, unitId);
}

void GameEngine::setNewRoute(const games_types::PlayerCommand& cmd)
{
    if (!session)
    {
        return;
    }
    std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    auto unitIt = std::find_if(
        units.begin(),
        units.end(),
        [unitId = cmd.unitId](const games_types::UnitPosition& unit) {
            return unit.entity_id == unitId;
        });

    if (unitIt == units.end())
    {
        return;
    }

    const std::vector<games_types::UnitPosition> route = pathFinder->buildRoute(
        *unitIt,
        cmd.destX,
        cmd.destY);

    if (route.empty())
    {
        unitIt->x = cmd.destX;
        unitIt->y = cmd.destY;
    }
    else
    {
        *unitIt = route.back();
    }

    session->setUnitsSnapshot(units);
}