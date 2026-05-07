#include "GameEngine.h"

#include <algorithm>
#include <deque>
#include <cmath>
#include <map>
#include <limits>
#include <set>
#include <utility>
#include <vector>
#include <unordered_set>

#include "GameSession.h"
#include "PathFinder.h"
#include "spatialGrid.h"

namespace
{
    constexpr int kGridCols = 100;
    constexpr int kGridRows = 100;
    constexpr float kCellSize = 50.0f;
    constexpr int kBaseFootprintSize = 6;
    constexpr int kSmallStructureFootprintSize = 2;
    constexpr int kAttackImpactDelayMinMs = 120;
    constexpr int kAttackImpactDelayMaxMs = 600;

    constexpr float kCollectorCollisionRadius = 25.0f;
    constexpr float kBaseCollisionRadius = 250.0f;

    constexpr float kProjectileSpeed = 600.0f;
    constexpr float kProjectileMaxLifetimeMs = 3000.0f;
    constexpr float kProjectileHitRadius = 25.0f;
    constexpr float kStructureCollisionRadius = 50.0f;

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

    int computeAttackImpactDelayMs(float distSq)
    {
        const float dist = std::sqrt(distSq);
        const int delay = static_cast<int>(dist * 0.18f);
        return std::clamp(delay, kAttackImpactDelayMinMs, kAttackImpactDelayMaxMs);
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

    bool isPurchasableTroop(games_types::EntityType unitType, bool isArcadeMode)
    {
        if (isArcadeMode)
        {
            return unitType == games_types::EntityType::Attacker ||
                   unitType == games_types::EntityType::Bomb;
        }
        return unitType == games_types::EntityType::Attacker ||
               unitType == games_types::EntityType::Collector ||
               unitType == games_types::EntityType::Bomb;
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
                if (circlesIntersect(unit.x, unit.y, 100.0f, shop.x, shop.y, shop.radius))
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
            games_types::id_ranges::p1Collectors.contains(entityId) ||
            games_types::id_ranges::p1Bombs.contains(entityId))
        {
            return 1;
        }

        if (games_types::id_ranges::p2Structures.contains(entityId) ||
            games_types::id_ranges::p2Attackers.contains(entityId) ||
            games_types::id_ranges::p2Collectors.contains(entityId) ||
            games_types::id_ranges::p2Bombs.contains(entityId))
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

    bool isBaseStructureId(int entityId)
    {
        return games_types::id_ranges::p1Structures.contains(entityId) ||
               games_types::id_ranges::p2Structures.contains(entityId);
    }

    games_types::CellCoord footprintTopLeftFromCenter(const games_types::CellCoord& center,
                                                      int footprintSize)
    {
        // For even sizes (like 6x6), keep a stable anchor around the center cell.
        const int offset = (footprintSize - 1) / 2;
        return games_types::CellCoord{center.x - offset, center.y - offset};
    }

    void blockFootprintFromWorldCenter(SpatialGrid& grid,
                                       float worldX,
                                       float worldY,
                                       int footprintSize)
    {
        const games_types::CellCoord center = worldToCell(worldX, worldY);
        const games_types::CellCoord topLeft = footprintTopLeftFromCenter(center, footprintSize);

        for (int dy = 0; dy < footprintSize; ++dy)
        {
            for (int dx = 0; dx < footprintSize; ++dx)
            {
                const games_types::CellCoord cell{topLeft.x + dx, topLeft.y + dy};
                if (grid.inBounds(cell))
                {
                    grid.setStaticBlocked(cell, true);
                }
            }
        }
    }

    void blockStaticObstacleCells(SpatialGrid& grid,
                                  const std::vector<games_types::StaticObstacle>& obstacles)
    {
        for (const auto& obstacle : obstacles)
        {
            for (const auto& cell : obstacle.cells)
            {
                if (grid.inBounds(cell))
                {
                    grid.setStaticBlocked(cell, true);
                }
            }
        }
    }

    void populateStaticPathGrid(SpatialGrid& grid,
                                const std::vector<games_types::UnitPosition>& structures,
                                const std::vector<games_types::ResourceNode>& resources,
                                const std::vector<games_types::ShopUnit>& shops,
                                const std::vector<games_types::StaticObstacle>& obstacles,
                                int skippedEntityId)
    {
        for (const auto& structure : structures)
        {
            if (structure.entity_id == skippedEntityId)
            {
                continue;
            }

            const int footprint = isBaseStructureId(structure.entity_id)
                                      ? kBaseFootprintSize
                                      : kSmallStructureFootprintSize;
            blockFootprintFromWorldCenter(grid, structure.x, structure.y, footprint);
        }

        for (const auto& resource : resources)
        {
            blockFootprintFromWorldCenter(
                grid,
                resource.x,
                resource.y,
                kSmallStructureFootprintSize);
        }

        for (const auto& shop : shops)
        {
            blockFootprintFromWorldCenter(
                grid,
                shop.x,
                shop.y,
                kSmallStructureFootprintSize);
        }

        blockStaticObstacleCells(grid, obstacles);
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

    // Deduplicate attack commands per attacker within the same processing cycle.
    std::unordered_set<int> seenAttackers;

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
            attackLockTargetByAttacker.erase(cmd.unitId);
            pendingMoveCommands.push_back(cmd);
            continue;
        }

        if (cmd.type == games_types::CommandType::AttackUnit)
        {
            // If we've already seen an attack command for this attacker in the
            // current batch, ignore subsequent ones to avoid "burst" effects
            // when the unit later becomes able to attack.
            const int attackerId = cmd.attack.attackerId;
            if (attackerId > 0)
            {
                if (seenAttackers.find(attackerId) != seenAttackers.end())
                {
                    continue;
                }
                seenAttackers.insert(attackerId);
            }

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
    std::vector<games_types::StaticObstacle> obstacles = session->getStaticObstaclesSnapshot();

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
        populateStaticPathGrid(slotGrid, structures, resources, shops, obstacles, -1);

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
    const bool hasBombs = session->isArcadeMode() && !session->getBombsSnapshot().empty();
    if (units.empty() && !hasBombs)
    {
        return;
    }

    const std::vector<games_types::UnitPosition> structures = session->getStructuresSnapshot();
    const std::vector<games_types::ResourceNode> resources = session->getResourcesSnapshot();
    const std::vector<games_types::ShopUnit> shops = session->getShopsSnapshot();
    const std::vector<games_types::StaticObstacle> obstacles = session->getStaticObstaclesSnapshot();

    SpatialGrid movementGrid(kGridCols, kGridRows);
    populateStaticPathGrid(movementGrid, structures, resources, shops, obstacles, -1);

    std::sort(units.begin(), units.end(), [](const games_types::UnitPosition& lhs, const games_types::UnitPosition& rhs) {
        return lhs.entity_id < rhs.entity_id;
    });

    for (const auto& unit : units)
    {
        movementGrid.placeEntity(unit.entity_id, worldToCell(unit.x, unit.y));
    }

    // Decrease cooldowns
    for (auto it = movementCooldownRemainingMs.begin(); it != movementCooldownRemainingMs.end();)
    {
        it->second = std::max(0, it->second - deltaMs);
        if (it->second == 0)
        {
            it = movementCooldownRemainingMs.erase(it);
        }
        else
        {
            ++it;
        }
    }

    std::vector<int> stuckUnits;

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

        if (movementCooldownRemainingMs.count(unit.entity_id) > 0)
        {
            continue;
        }

        games_types::MoveResult res = movementGrid.tryReserveMove(unit.entity_id, route.front());
        if (res.status == games_types::MoveStatus::Occupied || res.status == games_types::MoveStatus::ReservedByOther)
        {
            stuckUnits.push_back(unit.entity_id);
        }
    }

    const auto committedMoves = movementGrid.commitReservedMoves();
    
    for (const auto& move : committedMoves)
    {
        const auto [worldX, worldY] = cellCenterToWorld(move.to);
        session->upsertUnitPosition(move.entityId, worldX, worldY);
        movementCooldownRemainingMs[move.entityId] = 83; // Match 10 pixels/frame in client (~83ms per cell)

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

    // Repath stuck units to bypass dynamic blocks
    for (int unitId : stuckUnits)
    {
        auto routeIt = movementRoutes.find(unitId);
        if (routeIt != movementRoutes.end() && !routeIt->second.empty())
        {
            repathUnit(unitId, routeIt->second.back());
        }
    }

    if (session->isArcadeMode())
    {
        std::vector<games_types::UnitPosition> bombs = session->getBombsSnapshot();
        for (const auto& bomb : bombs)
        {
            const int ownerId = ownerFromEntityId(bomb.entity_id);
            games_types::UnitPosition enemyBase{};
            if (ownerId == 1)
            {
                for (const auto& s : structures)
                {
                    if (s.entity_id == 5000)
                    {
                        enemyBase = s;
                        break;
                    }
                }
            }
            else if (ownerId == 2)
            {
                for (const auto& s : structures)
                {
                    if (s.entity_id == 0)
                    {
                        enemyBase = s;
                        break;
                    }
                }
            }

            auto routeIt = movementRoutes.find(bomb.entity_id);
            if (routeIt == movementRoutes.end() || routeIt->second.empty())
            {
                if (enemyBase.entity_id != 0)
                {
                    repathUnit(bomb.entity_id, worldToCell(enemyBase.x, enemyBase.y));
                }
                continue;
            }

            if (movementCooldownRemainingMs.count(bomb.entity_id) > 0)
            {
                continue;
            }

            auto& route = routeIt->second;
            const games_types::CellCoord currentCell = worldToCell(bomb.x, bomb.y);
            while (!route.empty() && route.front() == currentCell)
            {
                route.pop_front();
            }

            if (route.empty())
            {
                movementRoutes.erase(routeIt);
                continue;
            }

            games_types::CellCoord nextCell = route.front();
            if (!movementGrid.inBounds(nextCell) || movementGrid.isStaticBlocked(nextCell))
            {
                if (enemyBase.entity_id != 0)
                {
                    repathUnit(bomb.entity_id, worldToCell(enemyBase.x, enemyBase.y));
                }
                continue;
            }

            const auto [worldX, worldY] = cellCenterToWorld(nextCell);
            session->upsertBombPosition(bomb.entity_id, worldX, worldY);
            movementCooldownRemainingMs[bomb.entity_id] = 83;
            route.pop_front();

            if (enemyBase.entity_id != 0)
            {
                const float explosionRadius = static_cast<float>(session->getArcadeExplosionRadius());
                if (circlesIntersect(worldX, worldY, 25.0f, enemyBase.x, enemyBase.y, explosionRadius))
                {
                    session->setGameOver(ownerId);
                }
            }
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

void GameEngine::updateProjectiles(int deltaMs)
{
    if (!session || activeProjectiles.empty() || deltaMs <= 0)
    {
        return;
    }

    const std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    const std::vector<games_types::UnitPosition> bombs = session->getBombsSnapshot();
    const std::vector<games_types::UnitPosition> structures = session->getStructuresSnapshot();
    const std::vector<games_types::StaticObstacle> obstacles = session->getStaticObstaclesSnapshot();

    SpatialGrid projectileGrid(kGridCols, kGridRows);
    for (const auto& obstacle : obstacles)
    {
        for (const auto& cell : obstacle.cells)
        {
            if (projectileGrid.inBounds(cell))
            {
                projectileGrid.setStaticBlocked(cell, true);
            }
        }
    }

    for (const auto& unit : units)
    {
        projectileGrid.placeEntity(unit.entity_id, worldToCell(unit.x, unit.y));
    }

    for (const auto& bomb : bombs)
    {
        projectileGrid.placeEntity(bomb.entity_id, worldToCell(bomb.x, bomb.y));
    }

    for (auto& projectile : activeProjectiles)
    {
        const float dt = static_cast<float>(deltaMs) / 1000.0f;
        projectile.posX += projectile.velX * dt;
        projectile.posY += projectile.velY * dt;
        projectile.lifetimeMs -= static_cast<float>(deltaMs);

        const bool outOfBounds = projectile.posX < 0.0f ||
                                 projectile.posX >= kGridCols * kCellSize ||
                                 projectile.posY < 0.0f ||
                                 projectile.posY >= kGridRows * kCellSize;

        if (outOfBounds || projectile.lifetimeMs <= 0.0f)
        {
            projectile.lifetimeMs = 0.0f;
            continue;
        }

        const games_types::CellCoord cell = worldToCell(projectile.posX, projectile.posY);
        if (!projectileGrid.inBounds(cell))
        {
            projectile.lifetimeMs = 0.0f;
            continue;
        }

        if (projectileGrid.isStaticBlocked(cell))
        {
            projectile.lifetimeMs = 0.0f;
            continue;
        }

        const int occupantId = projectileGrid.getOccupant(cell);
        if (occupantId >= 0 && occupantId != projectile.sourceEntityId)
        {
            const games_types::EntityType occupantType = games_types::classifyEntityTypeFromId(occupantId);
            if (occupantType == games_types::EntityType::Attacker ||
                occupantType == games_types::EntityType::Bomb)
            {
                applyProjectileDamage(projectile.sourceEntityId, occupantId);
                projectile.lifetimeMs = 0.0f;
                continue;
            }
        }

        for (const auto& structure : structures)
        {
            if (structure.entity_id == projectile.sourceEntityId)
            {
                continue;
            }

            const float collisionRadius = isBaseStructureId(structure.entity_id)
                                              ? kBaseCollisionRadius
                                              : kStructureCollisionRadius;
            if (circlesIntersect(projectile.posX, projectile.posY, kProjectileHitRadius,
                                 structure.x, structure.y, collisionRadius))
            {
                applyProjectileDamage(projectile.sourceEntityId, structure.entity_id);
                projectile.lifetimeMs = 0.0f;
                break;
            }
        }

        if (projectile.lifetimeMs <= 0.0f)
        {
            continue;
        }

        games_types::UnitPosition targetPos{};
        if (session->getEntityPosition(projectile.targetEntityId, targetPos))
        {
            if (distanceSquared(projectile.posX, projectile.posY, targetPos.x, targetPos.y) <=
                (kProjectileHitRadius * kProjectileHitRadius))
            {
                applyProjectileDamage(projectile.sourceEntityId, projectile.targetEntityId);
                projectile.lifetimeMs = 0.0f;
                continue;
            }
        }
    }

    activeProjectiles.erase(
        std::remove_if(activeProjectiles.begin(), activeProjectiles.end(),
                       [](const games_types::Projectile& p) { return p.lifetimeMs <= 0.0f; }),
        activeProjectiles.end());
}

void GameEngine::applyProjectileDamage(int attackerId, int targetId)
{
    if (!session)
    {
        return;
    }

    const int attackerOwner = ownerFromEntityId(attackerId);
    if (attackerOwner == 0)
    {
        return;
    }

    games_types::DamageResolution resolution{};
    const int damage = std::max(session->getMinDamage(), session->getAttackerDamage());
    if (!session->applyDamageToEntity(attackerOwner, targetId, damage, resolution) || !resolution.applied)
    {
        return;
    }

    std::lock_guard<std::mutex> lock(mtxCombatEvents);

    games_types::CombatEvent damagedEvent{};
    damagedEvent.type = games_types::CombatEventType::UnitDamaged;
    damagedEvent.sessionId = session->getSessionId();
    damagedEvent.attackerPlayerId = attackerOwner;
    damagedEvent.attackerEntityId = attackerId;
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
        destroyedEvent.attackerEntityId = attackerId;
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

    updateProjectiles(deltaMs);

    for (auto it = attackImpactRemainingMs.begin(); it != attackImpactRemainingMs.end();)
    {
        it->second = std::max(0, it->second - deltaMs);
        if (it->second > 0)
        {
            ++it;
            continue;
        }

        const int attackerId = it->first;
        it = attackImpactRemainingMs.erase(it);

        auto lockIt = attackLockTargetByAttacker.find(attackerId);
        if (lockIt == attackLockTargetByAttacker.end())
        {
            continue;
        }

        const int targetId = lockIt->second;
        const int playerId = ownerFromEntityId(attackerId);
        if (playerId == 0)
        {
            attackLockTargetByAttacker.erase(attackerId);
            movementRoutes.erase(attackerId);
            continue;
        }

        AttackRequestResult impactResult = executeAttackAttempt(playerId, attackerId, targetId, true);
        if (!shouldKeepAttackLock(impactResult))
        {
            attackLockTargetByAttacker.erase(attackerId);
            movementRoutes.erase(attackerId);
        }
        else if (impactResult.reason == "out_of_range")
        {
            if (movementRoutes.find(attackerId) == movementRoutes.end() || movementRoutes[attackerId].empty())
            {
                games_types::UnitPosition targetPos{};
                if (session->getEntityPosition(targetId, targetPos))
                {
                    repathUnit(attackerId, worldToCell(targetPos.x, targetPos.y));
                }
            }
        }
    }

    if (attackLockTargetByAttacker.empty())
    {
        return;
    }

    std::vector<int> attackers;
    attackers.reserve(attackLockTargetByAttacker.size());
    for (const auto& lock : attackLockTargetByAttacker)
    {
        attackers.push_back(lock.first);
    }
    std::sort(attackers.begin(), attackers.end());

    std::vector<int> attackersToUnlock;
    attackersToUnlock.reserve(attackers.size());

    for (const int attackerId : attackers)
    {
        auto lockIt = attackLockTargetByAttacker.find(attackerId);
        if (lockIt == attackLockTargetByAttacker.end())
        {
            continue;
        }

        if (attackerCooldownRemainingMs.count(attackerId) > 0)
        {
            continue;
        }

        if (attackImpactRemainingMs.count(attackerId) > 0)
        {
            continue;
        }

        const int targetId = lockIt->second;
        const int playerId = ownerFromEntityId(attackerId);
        if (playerId == 0)
        {
            attackersToUnlock.push_back(attackerId);
            continue;
        }

        AttackRequestResult result = executeAttackAttempt(playerId, attackerId, targetId, false);
        if (!shouldKeepAttackLock(result))
        {
            attackersToUnlock.push_back(attackerId);
            movementRoutes.erase(attackerId);
        }
        else if (result.accepted)
        {
            if (session && session->isArcadeMode())
            {
                games_types::UnitPosition attackerPos{};
                games_types::UnitPosition targetPos{};
                if (session->getEntityPosition(attackerId, attackerPos) &&
                    session->getEntityPosition(targetId, targetPos))
                {
                    const float dx = targetPos.x - attackerPos.x;
                    const float dy = targetPos.y - attackerPos.y;
                    const float dist = std::sqrt(dx * dx + dy * dy);
                    if (dist > 0.0f)
                    {
                        games_types::Projectile projectile{};
                        projectile.posX = attackerPos.x;
                        projectile.posY = attackerPos.y;
                        projectile.velX = (dx / dist) * kProjectileSpeed;
                        projectile.velY = (dy / dist) * kProjectileSpeed;
                        projectile.sourceEntityId = attackerId;
                        projectile.targetEntityId = targetId;
                        projectile.damage = std::max(session->getMinDamage(), session->getAttackerDamage());
                        projectile.lifetimeMs = kProjectileMaxLifetimeMs;
                        activeProjectiles.push_back(projectile);
                    }
                }
                attackerCooldownRemainingMs[attackerId] = session->getAttackerCooldownMs();
            }
            else
            {
                attackImpactRemainingMs[attackerId] = result.impactDelayMs;
            }
            movementRoutes.erase(attackerId);

            std::lock_guard<std::mutex> lock(mtxAttackResults);
            pendingAttackResults.push_back(result);
        }
        else if (result.reason == "out_of_range")
        {
            if (movementRoutes.find(attackerId) == movementRoutes.end() || movementRoutes[attackerId].empty())
            {
                games_types::UnitPosition targetPos{};
                if (session->getEntityPosition(targetId, targetPos))
                {
                    repathUnit(attackerId, worldToCell(targetPos.x, targetPos.y));
                }
            }
        }
    }

    for (const int attackerId : attackersToUnlock)
    {
        attackLockTargetByAttacker.erase(attackerId);
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

    // Arcade mode: always authorized, no proximity check needed
    if (session->isArcadeMode())
    {
        outState.authorized = true;
        outState.shopId = 11000;
        outState.unitId = -1;
        session->setShopAuthorizationState(playerId, outState);
        return true;
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

    if (!isPurchasableTroop(unitType, session->isArcadeMode()))
    {
        result.reason = "unit_type_not_purchasable";
        return result;
    }

    const bool isBombInArcade = (unitType == games_types::EntityType::Bomb && session->isArcadeMode());
    if (!isBombInArcade && !hasShopAuthorization(playerId))
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
    const float radius = 250.0f;
    const float angle = static_cast<float>(unitId % 11) * angleStep;
    const float spawnX = basePos.x + radius * std::cos(angle);
    const float spawnY = basePos.y + radius * std::sin(angle);
    // const float spawnX = 75.0;
    // const float spawnY = 75.0;

    if (isBombInArcade)
    {
        session->upsertBombPosition(unitId, spawnX, spawnY);
        session->registerSpawnedUnit(unitId, playerId, games_types::EntityType::Bomb);
    }
    else
    {
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

    if (games_types::isPlayerControllableUnitId(playerId, unitId))
    {
        return true;
    }

    if (session->isArcadeMode())
    {
        if (playerId == 1 && games_types::id_ranges::p1Bombs.contains(unitId))
        {
            return true;
        }
        if (playerId == 2 && games_types::id_ranges::p2Bombs.contains(unitId))
        {
            return true;
        }
    }

    return false;
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
    games_types::UnitPosition unitPos{};
    if (!session->getEntityPosition(cmd.unitId, unitPos))
    {
        return;
    }

    SpatialGrid pathGrid(kGridCols, kGridRows);

    const auto structures = session->getStructuresSnapshot();
    const auto resources = session->getResourcesSnapshot();
    const auto shops = session->getShopsSnapshot();
    const auto obstacles = session->getStaticObstaclesSnapshot();
    populateStaticPathGrid(pathGrid, structures, resources, shops, obstacles, cmd.unitId);

    const games_types::CellCoord startCell = worldToCell(unitPos.x, unitPos.y);

    pathGrid.setStaticBlocked(startCell, false);

    games_types::CellCoord effectiveDestination = destinationCell;
    if (pathGrid.isStaticBlocked(effectiveDestination))
    {
        bool found = false;
        for (int radius = 1; radius <= kGridCols && !found; ++radius)
        {
            std::vector<games_types::CellCoord> ring = buildRingCells(effectiveDestination, radius);
            std::sort(ring.begin(), ring.end(), cellLess);
            ring.erase(std::unique(ring.begin(),
                                   ring.end(),
                                   [](const games_types::CellCoord& lhs,
                                      const games_types::CellCoord& rhs) {
                                       return lhs.x == rhs.x && lhs.y == rhs.y;
                                   }),
                       ring.end());

            for (const auto& candidate : ring)
            {
                if (!pathGrid.inBounds(candidate) || pathGrid.isStaticBlocked(candidate))
                {
                    continue;
                }
                effectiveDestination = candidate;
                found = true;
                break;
            }
        }
    }

    const std::vector<games_types::CellCoord> routeCells = pathFinder->buildRoute(
        startCell,
        effectiveDestination,
        pathGrid);

    auto& routeState = movementRoutes[cmd.unitId];
    routeState.clear();

    if (routeCells.empty())
    {
        if (startCell == destinationCell)
        {
            movementRoutes.erase(cmd.unitId);
        }
        return;
    }

    routeState = std::deque<games_types::CellCoord>(routeCells.begin(), routeCells.end());
}

void GameEngine::repathUnit(int unitId, const games_types::CellCoord& destinationCell)
{
    if (!session)
    {
        return;
    }
    games_types::UnitPosition unitPos{};
    if (!session->getEntityPosition(unitId, unitPos))
    {
        return;
    }

    SpatialGrid pathGrid(kGridCols, kGridRows);

    const auto structures = session->getStructuresSnapshot();
    const auto resources = session->getResourcesSnapshot();
    const auto shops = session->getShopsSnapshot();
    const auto obstacles = session->getStaticObstaclesSnapshot();
    populateStaticPathGrid(pathGrid, structures, resources, shops, obstacles, unitId);

    // Treat all other units as temporary static blocks so pathfinder avoids them
    const std::vector<games_types::UnitPosition> units = session->getUnitsSnapshot();
    for (const auto& otherUnit : units)
    {
        if (otherUnit.entity_id != unitId)
        {
            const games_types::CellCoord otherCell = worldToCell(otherUnit.x, otherUnit.y);
            if (pathGrid.inBounds(otherCell))
            {
                pathGrid.setStaticBlocked(otherCell, true);
            }
        }
    }

    const games_types::CellCoord startCell = worldToCell(unitPos.x, unitPos.y);
    pathGrid.setStaticBlocked(startCell, false);

    games_types::CellCoord effectiveDestination = destinationCell;
    if (pathGrid.isStaticBlocked(effectiveDestination))
    {
        bool found = false;
        for (int radius = 1; radius <= kGridCols && !found; ++radius)
        {
            std::vector<games_types::CellCoord> ring = buildRingCells(effectiveDestination, radius);
            std::sort(ring.begin(), ring.end(), cellLess);
            ring.erase(std::unique(ring.begin(),
                                   ring.end(),
                                   [](const games_types::CellCoord& lhs,
                                      const games_types::CellCoord& rhs) {
                                       return lhs.x == rhs.x && lhs.y == rhs.y;
                                   }),
                       ring.end());

            for (const auto& candidate : ring)
            {
                if (!pathGrid.inBounds(candidate) || pathGrid.isStaticBlocked(candidate))
                {
                    continue;
                }
                effectiveDestination = candidate;
                found = true;
                break;
            }
        }
    }

    const std::vector<games_types::CellCoord> routeCells = pathFinder->buildRoute(
        startCell,
        effectiveDestination,
        pathGrid);

    auto& routeState = movementRoutes[unitId];
    routeState.clear();

    if (routeCells.empty())
    {
        if (startCell == destinationCell)
        {
            movementRoutes.erase(unitId);
        }
        return;
    }

    routeState = std::deque<games_types::CellCoord>(routeCells.begin(), routeCells.end());
}

void GameEngine::processAttackCommand(const games_types::PlayerCommand& cmd)
{
    AttackRequestResult result = executeAttackAttempt(
        cmd.playerId,
        cmd.attack.attackerId,
        cmd.attack.targetId,
        false);

    if (shouldKeepAttackLock(result))
    {
        attackLockTargetByAttacker[cmd.attack.attackerId] = cmd.attack.targetId;

        if (result.accepted)
        {
            if (session && session->isArcadeMode())
            {
                games_types::UnitPosition attackerPos{};
                games_types::UnitPosition targetPos{};
                if (session->getEntityPosition(cmd.attack.attackerId, attackerPos) &&
                    session->getEntityPosition(cmd.attack.targetId, targetPos))
                {
                    const float dx = targetPos.x - attackerPos.x;
                    const float dy = targetPos.y - attackerPos.y;
                    const float dist = std::sqrt(dx * dx + dy * dy);
                    if (dist > 0.0f)
                    {
                        games_types::Projectile projectile{};
                        projectile.posX = attackerPos.x;
                        projectile.posY = attackerPos.y;
                        projectile.velX = (dx / dist) * kProjectileSpeed;
                        projectile.velY = (dy / dist) * kProjectileSpeed;
                        projectile.sourceEntityId = cmd.attack.attackerId;
                        projectile.targetEntityId = cmd.attack.targetId;
                        projectile.damage = std::max(session->getMinDamage(), session->getAttackerDamage());
                        projectile.lifetimeMs = kProjectileMaxLifetimeMs;
                        activeProjectiles.push_back(projectile);
                    }
                }
                attackerCooldownRemainingMs[cmd.attack.attackerId] = session->getAttackerCooldownMs();
                movementRoutes.erase(cmd.attack.attackerId);
            }
            else if (result.impactDelayMs > 0)
            {
                attackImpactRemainingMs[cmd.attack.attackerId] = result.impactDelayMs;
                movementRoutes.erase(cmd.attack.attackerId);
            }
        }

        if (result.reason == "out_of_range")
        {
            games_types::UnitPosition targetPos{};
            if (session->getEntityPosition(cmd.attack.targetId, targetPos))
            {
                repathUnit(cmd.attack.attackerId, worldToCell(targetPos.x, targetPos.y));
            }
        }
        else if (!result.accepted || !session || !session->isArcadeMode())
        {
            movementRoutes.erase(cmd.attack.attackerId);
        }
    }
    else
    {
        attackLockTargetByAttacker.erase(cmd.attack.attackerId);
        movementRoutes.erase(cmd.attack.attackerId);
    }

    std::lock_guard<std::mutex> lock(mtxAttackResults);
    pendingAttackResults.push_back(result);
}

GameEngine::AttackRequestResult GameEngine::executeAttackAttempt(int playerId, int attackerId, int targetId, bool applyDamage)
{
    AttackRequestResult result{};
    result.playerId = playerId;
    result.attackerId = attackerId;
    result.targetId = targetId;
    result.accepted = false;
    result.reason = "rejected";
    result.impactDelayMs = 0;

    if (!session || !session->hasPlayer(playerId))
    {
        result.reason = "invalid_player";
        return result;
    }

    if (!isAttackerUnitOwnedByPlayer(playerId, attackerId))
    {
        result.reason = "invalid_attacker_owner_or_type";
        return result;
    }

    int winnerPlayerId = 0;
    if (session->isGameOver(winnerPlayerId))
    {
        result.reason = "game_over";
        return result;
    }

    games_types::UnitPosition attackerPos{};
    games_types::UnitPosition targetPos{};
    if (!session->getEntityPosition(attackerId, attackerPos))
    {
        result.reason = "attacker_not_found";
        return result;
    }

    if (!session->getEntityPosition(targetId, targetPos))
    {
        result.reason = "target_not_found";
        return result;
    }

    const int attackerOwner = ownerFromEntityId(attackerId);
    const int targetOwner = ownerFromEntityId(targetId);
    if (attackerOwner == 0 || targetOwner == 0)
    {
        result.reason = "invalid_owner";
        return result;
    }

    if (attackerOwner == targetOwner)
    {
        result.reason = "invalid_target_ally";
        return result;
    }

    int attackerCurrentHp = 0;
    int attackerMaxHp = 0;
    if (!session->getEntityHealth(attackerId, attackerCurrentHp, attackerMaxHp) || attackerCurrentHp <= 0)
    {
        result.reason = "attacker_dead_or_missing";
        return result;
    }

    int targetCurrentHp = 0;
    int targetMaxHp = 0;
    if (!session->getEntityHealth(targetId, targetCurrentHp, targetMaxHp) || targetCurrentHp <= 0)
    {
        result.reason = "target_dead_or_missing";
        return result;
    }

    const int remainingCooldown = attackerCooldownRemainingMs[attackerId];
    if (remainingCooldown > 0)
    {
        result.reason = "cooldown";
        return result;
    }

    const int attackerRange = session->getAttackerRange();
    const float distSq = distanceSquared(attackerPos.x, attackerPos.y, targetPos.x, targetPos.y);
    if (distSq > static_cast<float>(attackerRange * attackerRange))
    {
        result.reason = "out_of_range";
        return result;
    }

    if (!applyDamage)
    {
        result.accepted = true;
        result.reason = "launching";
        if (session->isArcadeMode())
        {
            result.impactDelayMs = 0;
        }
        else
        {
            result.impactDelayMs = computeAttackImpactDelayMs(distSq);
        }
        return result;
    }

    games_types::DamageResolution resolution{};
    const int damage = std::max(session->getMinDamage(), session->getAttackerDamage());
    if (!session->applyDamageToEntity(attackerOwner, targetId, damage, resolution) || !resolution.applied)
    {
        result.reason = "attack_not_applied";
        return result;
    }

    attackerCooldownRemainingMs[attackerId] = session->getAttackerCooldownMs();

    {
        std::lock_guard<std::mutex> lock(mtxCombatEvents);

        games_types::CombatEvent damagedEvent{};
        damagedEvent.type = games_types::CombatEventType::UnitDamaged;
        damagedEvent.sessionId = session->getSessionId();
        damagedEvent.attackerPlayerId = attackerOwner;
        damagedEvent.attackerEntityId = attackerId;
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
            destroyedEvent.attackerEntityId = attackerId;
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
    return result;
}

bool GameEngine::shouldKeepAttackLock(const AttackRequestResult& result) const
{
    if (result.accepted)
    {
        return true;
    }

    return result.reason == "cooldown" || result.reason == "out_of_range";
}