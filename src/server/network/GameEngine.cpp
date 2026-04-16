#include "GameEngine.h"

#include <algorithm>
#include <deque>
#include <cmath>
#include <map>
#include <limits>
#include <set>
#include <utility>
#include <vector>

#include "GameSession.h"
#include "PathFinder.h"
#include "spatialGrid.h"

namespace
{
    constexpr int kGridCols = 100;
    constexpr int kGridRows = 100;
    constexpr float kCellSize = 50.0f;

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

    int clampToRange(int value, int minValue, int maxValue)
    {
        return std::max(minValue, std::min(value, maxValue));
    }

    games_types::CellCoord worldToCell(float x, float y)
    {
        const int cellX = clampToRange(static_cast<int>(x / kCellSize), 0, kGridCols - 1);
        const int cellY = clampToRange(static_cast<int>(y / kCellSize), 0, kGridRows - 1);
        return games_types::CellCoord{cellX, cellY};
    }

    std::pair<float, float> cellCenterToWorld(const games_types::CellCoord& cell)
    {
        const float worldX = (static_cast<float>(cell.x) + 0.5f) * kCellSize;
        const float worldY = (static_cast<float>(cell.y) + 0.5f) * kCellSize;
        return {worldX, worldY};
    }

    void blockCellForEntity(SpatialGrid& grid, int entityId, float x, float y)
    {
        (void)entityId;
        grid.setStaticBlocked(worldToCell(x, y), true);
    }

    void populateStaticPathGrid(SpatialGrid& grid,
                                const std::vector<games_types::UnitPosition>& structures,
                                const std::vector<games_types::ResourceNode>& resources,
                                const std::vector<games_types::ShopUnit>& shops,
                                int skippedEntityId)
    {
        for (const auto& structure : structures)
        {
            if (structure.entity_id == skippedEntityId)
            {
                continue;
            }
            blockCellForEntity(grid, structure.entity_id, structure.x, structure.y);
        }

        for (const auto& resource : resources)
        {
            blockCellForEntity(grid, resource.entityId, resource.x, resource.y);
        }

        for (const auto& shop : shops)
        {
            blockCellForEntity(grid, shop.entityId, shop.x, shop.y);
        }
    }

    std::vector<games_types::CellCoord> buildRingCells(const games_types::CellCoord& center, int radius)
    {
        std::vector<games_types::CellCoord> ring;
        if (radius <= 0)
        {
            return ring;
        }

        for (int x = center.x - radius; x <= center.x + radius; ++x)
        {
            ring.push_back(games_types::CellCoord{x, center.y - radius});
            ring.push_back(games_types::CellCoord{x, center.y + radius});
        }

        for (int y = center.y - radius + 1; y <= center.y + radius - 1; ++y)
        {
            ring.push_back(games_types::CellCoord{center.x - radius, y});
            ring.push_back(games_types::CellCoord{center.x + radius, y});
        }

        return ring;
    }

    bool cellLess(const games_types::CellCoord& lhs, const games_types::CellCoord& rhs)
    {
        if (lhs.x != rhs.x)
        {
            return lhs.x < rhs.x;
        }
        return lhs.y < rhs.y;
    }

    std::int64_t makeFormationGroupKey(int playerId, const games_types::CellCoord& destination)
    {
        return (static_cast<std::int64_t>(playerId) << 20) |
               (static_cast<std::int64_t>(destination.x) << 10) |
               static_cast<std::int64_t>(destination.y);
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

    std::vector<games_types::PlayerCommand> pendingMoveCommands;

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
            pendingMoveCommands.push_back(cmd);
            continue;
        }

        if (cmd.type == games_types::CommandType::AttackUnit)
        {
            processAttackCommand(cmd);
            continue;
        }
    }

    processMoveCommandsWithFormation(pendingMoveCommands);
}

void GameEngine::processMoveCommandsWithFormation(const std::vector<games_types::PlayerCommand>& moveCommands)
{
    if (!session || moveCommands.empty())
    {
        return;
    }

    std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    std::vector<games_types::UnitPosition> structures = session->getStructuresSnapshot();
    std::vector<games_types::ResourceNode> resources = session->getResourcesSnapshot();
    std::vector<games_types::ShopUnit> shops = session->getShopsSnapshot();

    std::unordered_map<int, games_types::CellCoord> currentCellByUnit;
    currentCellByUnit.reserve(units.size());
    for (const auto& unit : units)
    {
        currentCellByUnit[unit.entity_id] = worldToCell(unit.x, unit.y);
    }

    std::map<std::int64_t, std::vector<games_types::PlayerCommand>> groups;
    for (const auto& cmd : moveCommands)
    {
        groups[makeFormationGroupKey(cmd.playerId, cmd.destCell)].push_back(cmd);
    }

    for (auto& groupEntry : groups)
    {
        auto& groupCommands = groupEntry.second;
        if (groupCommands.empty())
        {
            continue;
        }

        std::sort(groupCommands.begin(), groupCommands.end(), [](const games_types::PlayerCommand& lhs,
                                                                 const games_types::PlayerCommand& rhs) {
            return lhs.unitId < rhs.unitId;
        });

        if (groupCommands.size() == 1)
        {
            formationByUnit.erase(groupCommands.front().unitId);
            setNewRoute(groupCommands.front());
            continue;
        }

        const games_types::CellCoord groupTarget = groupCommands.front().destCell;
        SpatialGrid slotGrid(kGridCols, kGridRows);
        populateStaticPathGrid(slotGrid, structures, resources, shops, -1);

        std::vector<games_types::CellCoord> slotCandidates;
        slotCandidates.reserve(groupCommands.size() * 2);

        for (int radius = 1; radius <= kGridCols && slotCandidates.size() < groupCommands.size(); ++radius)
        {
            std::vector<games_types::CellCoord> ring = buildRingCells(groupTarget, radius);
            std::sort(ring.begin(), ring.end(), cellLess);
            ring.erase(std::unique(ring.begin(), ring.end(), [](const games_types::CellCoord& lhs,
                                                               const games_types::CellCoord& rhs) {
                          return lhs.x == rhs.x && lhs.y == rhs.y;
                      }),
                      ring.end());

            for (const auto& candidate : ring)
            {
                if (!slotGrid.inBounds(candidate) || slotGrid.isStaticBlocked(candidate))
                {
                    continue;
                }
                slotCandidates.push_back(candidate);
                if (slotCandidates.size() >= groupCommands.size())
                {
                    break;
                }
            }
        }

        if (slotCandidates.empty())
        {
            for (const auto& cmd : groupCommands)
            {
                formationByUnit.erase(cmd.unitId);
                setNewRoute(cmd);
            }
            continue;
        }

        std::set<std::size_t> takenSlots;
        ++formationEpoch;
        for (std::size_t i = 0; i < groupCommands.size(); ++i)
        {
            const auto& cmd = groupCommands[i];
            const auto unitCellIt = currentCellByUnit.find(cmd.unitId);
            if (unitCellIt == currentCellByUnit.end())
            {
                continue;
            }

            const games_types::CellCoord unitCell = unitCellIt->second;
            int bestScore = std::numeric_limits<int>::max();
            std::size_t bestSlotIndex = 0;
            bool foundSlot = false;

            for (std::size_t slotIdx = 0; slotIdx < slotCandidates.size(); ++slotIdx)
            {
                if (takenSlots.count(slotIdx) > 0)
                {
                    continue;
                }

                const auto& slot = slotCandidates[slotIdx];
                const int manhattan = std::abs(slot.x - unitCell.x) + std::abs(slot.y - unitCell.y);
                if (manhattan < bestScore)
                {
                    bestScore = manhattan;
                    bestSlotIndex = slotIdx;
                    foundSlot = true;
                }
            }

            games_types::CellCoord assignedSlot = groupTarget;
            int assignedSlotIndex = -1;
            if (foundSlot)
            {
                assignedSlot = slotCandidates[bestSlotIndex];
                assignedSlotIndex = static_cast<int>(bestSlotIndex);
                takenSlots.insert(bestSlotIndex);
            }

            formationByUnit[cmd.unitId] = FormationAssignment{
                groupTarget,
                assignedSlot,
                static_cast<int>(groupCommands.size()),
                assignedSlotIndex,
                formationEpoch};

            setNewRouteToCell(cmd, assignedSlot);
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

void GameEngine::advanceMovement(int deltaMs)
{
    if (!session || deltaMs <= 0)
    {
        return;
    }

    std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    if (units.empty())
    {
        return;
    }

    const std::vector<games_types::UnitPosition> structures = session->getStructuresSnapshot();
    const std::vector<games_types::ResourceNode> resources = session->getResourcesSnapshot();
    const std::vector<games_types::ShopUnit> shops = session->getShopsSnapshot();

    SpatialGrid movementGrid(kGridCols, kGridRows);
    populateStaticPathGrid(movementGrid, structures, resources, shops, -1);

    std::sort(units.begin(), units.end(), [](const games_types::UnitPosition& lhs, const games_types::UnitPosition& rhs) {
        return lhs.entity_id < rhs.entity_id;
    });

    for (const auto& unit : units)
    {
        movementGrid.placeEntity(unit.entity_id, worldToCell(unit.x, unit.y));
    }

    for (const auto& unit : units)
    {
        auto routeIt = movementRoutes.find(unit.entity_id);
        if (routeIt == movementRoutes.end())
        {
            continue;
        }

        auto& route = routeIt->second;
        const games_types::CellCoord currentCell = worldToCell(unit.x, unit.y);
        while (!route.empty() && route.front() == currentCell)
        {
            route.pop_front();
        }

        if (route.empty())
        {
            movementRoutes.erase(routeIt);
            continue;
        }

        movementGrid.tryReserveMove(unit.entity_id, route.front());
    }

    const auto committedMoves = movementGrid.commitReservedMoves();
    if (committedMoves.empty())
    {
        return;
    }

    for (const auto& move : committedMoves)
    {
        const auto [worldX, worldY] = cellCenterToWorld(move.to);
        session->upsertUnitPosition(move.entityId, worldX, worldY);

        auto routeIt = movementRoutes.find(move.entityId);
        if (routeIt == movementRoutes.end())
        {
            continue;
        }

        auto& route = routeIt->second;
        if (!route.empty() && route.front() == move.to)
        {
            route.pop_front();
        }

        if (route.empty())
        {
            movementRoutes.erase(routeIt);
        }
    }
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
    setNewRouteToCell(cmd, cmd.destCell);
}

void GameEngine::setNewRouteToCell(const games_types::PlayerCommand& cmd, const games_types::CellCoord& destinationCell)
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

    SpatialGrid pathGrid(kGridCols, kGridRows);

    const auto structures = session->getStructuresSnapshot();
    const auto resources = session->getResourcesSnapshot();
    const auto shops = session->getShopsSnapshot();
    populateStaticPathGrid(pathGrid, structures, resources, shops, unitIt->entity_id);

    const games_types::CellCoord startCell = worldToCell(unitIt->x, unitIt->y);

    pathGrid.setStaticBlocked(startCell, false);

    const std::vector<games_types::CellCoord> routeCells = pathFinder->buildRoute(
        startCell,
        destinationCell,
        pathGrid);

    auto& routeState = movementRoutes[unitIt->entity_id];
    routeState.clear();

    if (routeCells.empty())
    {
        if (startCell == destinationCell)
        {
            movementRoutes.erase(unitIt->entity_id);
        }
        return;
    }

    routeState = std::deque<games_types::CellCoord>(routeCells.begin(), routeCells.end());
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