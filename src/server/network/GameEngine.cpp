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

    int ownerFromEntityId(int entityId)
    {
        if (games_types::id_ranges::p1Structures.contains(entityId) ||
            games_types::id_ranges::p1Attackers.contains(entityId) ||
            games_types::id_ranges::p1Collectors.contains(entityId))
        {
            return 1;
        }

        if (games_types::id_ranges::p2Structures.contains(entityId) ||
            games_types::id_ranges::p2Attackers.contains(entityId) ||
            games_types::id_ranges::p2Collectors.contains(entityId))
        {
            return 2;
        }

        return 0;
    }

    bool isAttackerUnitOwnedByPlayer(int playerId, int entityId)
    {
        if (playerId == 1)
        {
            return games_types::id_ranges::p1Attackers.contains(entityId);
        }
        if (playerId == 2)
        {
            return games_types::id_ranges::p2Attackers.contains(entityId);
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

        if (cmd.type == games_types::CommandType::MoveUnit)
        {
            if (!propertyValidation(cmd.playerId, cmd.unitId))
            {
                continue;
            }

            setNewRoute(cmd);
            continue;
        }

        if (cmd.type == games_types::CommandType::AttackUnit)
        {
            processAttackCommand(cmd);
            continue;
        }
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
    if (deltaMs <= 0)
    {
        return;
    }

    for (auto it = attackerCooldownRemainingMs.begin(); it != attackerCooldownRemainingMs.end();)
    {
        it->second = std::max(0, it->second - deltaMs);
        if (it->second == 0)
        {
            it = attackerCooldownRemainingMs.erase(it);
        }
        else
        {
            ++it;
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

std::vector<GameEngine::AttackRequestResult> GameEngine::drainAttackResults()
{
    std::lock_guard<std::mutex> lock(mtxAttackResults);
    std::vector<AttackRequestResult> out;
    out.swap(pendingAttackResults);
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

void GameEngine::processAttackCommand(const games_types::PlayerCommand& cmd)
{
    AttackRequestResult result{};
    result.playerId = cmd.playerId;
    result.attackerId = cmd.attack.attackerId;
    result.targetId = cmd.attack.targetId;
    result.accepted = false;
    result.reason = "rejected";

    if (!session || !session->hasPlayer(cmd.playerId))
    {
        result.reason = "invalid_player";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    if (!isAttackerUnitOwnedByPlayer(cmd.playerId, cmd.attack.attackerId))
    {
        result.reason = "invalid_attacker_owner_or_type";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    int winnerPlayerId = 0;
    if (session->isGameOver(winnerPlayerId))
    {
        result.reason = "game_over";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    games_types::UnitPosition attackerPos{};
    games_types::UnitPosition targetPos{};
    if (!session->getEntityPosition(cmd.attack.attackerId, attackerPos))
    {
        result.reason = "attacker_not_found";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    if (!session->getEntityPosition(cmd.attack.targetId, targetPos))
    {
        result.reason = "target_not_found";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    const int attackerOwner = ownerFromEntityId(cmd.attack.attackerId);
    const int targetOwner = ownerFromEntityId(cmd.attack.targetId);
    if (attackerOwner == 0 || targetOwner == 0)
    {
        result.reason = "invalid_owner";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    if (attackerOwner == targetOwner)
    {
        result.reason = "invalid_target_ally";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    int attackerCurrentHp = 0;
    int attackerMaxHp = 0;
    if (!session->getEntityHealth(cmd.attack.attackerId, attackerCurrentHp, attackerMaxHp) || attackerCurrentHp <= 0)
    {
        result.reason = "attacker_dead_or_missing";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    int targetCurrentHp = 0;
    int targetMaxHp = 0;
    if (!session->getEntityHealth(cmd.attack.targetId, targetCurrentHp, targetMaxHp) || targetCurrentHp <= 0)
    {
        result.reason = "target_dead_or_missing";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    const int remainingCooldown = attackerCooldownRemainingMs[cmd.attack.attackerId];
    if (remainingCooldown > 0)
    {
        result.reason = "cooldown";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    const int attackerRange = session->getAttackerRange();
    const float distSq = distanceSquared(attackerPos.x, attackerPos.y, targetPos.x, targetPos.y);
    if (distSq > static_cast<float>(attackerRange * attackerRange))
    {
        result.reason = "out_of_range";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    games_types::DamageResolution resolution{};
    const int damage = std::max(session->getMinDamage(), session->getAttackerDamage());
    if (!session->applyDamageToEntity(attackerOwner, cmd.attack.targetId, damage, resolution) || !resolution.applied)
    {
        result.reason = "attack_not_applied";
        std::lock_guard<std::mutex> lock(mtxAttackResults);
        pendingAttackResults.push_back(result);
        return;
    }

    attackerCooldownRemainingMs[cmd.attack.attackerId] = session->getAttackerCooldownMs();

    {
        std::lock_guard<std::mutex> lock(mtxCombatEvents);

        games_types::CombatEvent damagedEvent{};
        damagedEvent.type = games_types::CombatEventType::UnitDamaged;
        damagedEvent.sessionId = session->getSessionId();
        damagedEvent.attackerPlayerId = attackerOwner;
        damagedEvent.attackerEntityId = cmd.attack.attackerId;
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
            destroyedEvent.attackerPlayerId = attackerOwner;
            destroyedEvent.targetEntityId = resolution.entityId;
            destroyedEvent.targetPlayerId = resolution.ownerPlayerId;
            destroyedEvent.attackerEntityId = cmd.attack.attackerId;
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

    result.accepted = true;
    result.reason = "ok";
    result.targetCurrentHp = resolution.currentHp;

    std::lock_guard<std::mutex> lock(mtxAttackResults);
    pendingAttackResults.push_back(result);
}