#include "GameEngine.h"

#include <algorithm>
#include <utility>
#include <vector>

#include "GameSession.h"
#include "PathFinder.h"

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

bool GameEngine::propertyValidation(int playerId, int unitId) const
{
    if (!session || !session->hasPlayer(playerId))
    {
        return false;
    }

    if (playerId == 1)
    { 
        return unitId >= 1 && unitId <= 3;
    }

    if (playerId == 2)
    {
        return unitId >= 4 && unitId <= 6;
    }

    return false;
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