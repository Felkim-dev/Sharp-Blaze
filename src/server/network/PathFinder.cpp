#include "PathFinder.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <queue>
#include <unordered_map>

namespace
{
    int manhattanDistance(const games_types::CellCoord& a, const games_types::CellCoord& b)
    {
        return std::abs(a.x - b.x) + std::abs(a.y - b.y);
    }

    int cellToIndex(const games_types::CellCoord& cell, int cols)
    {
        return (cell.y * cols) + cell.x;
    }
}

std::vector<games_types::CellCoord> PathFinder::buildRoute(
    const games_types::CellCoord& start,
    const games_types::CellCoord& destination,
    const SpatialGrid& grid) const
{
    std::vector<games_types::CellCoord> route;

    if (!grid.inBounds(start) || !grid.inBounds(destination))
    {
        return route;
    }

    if (start == destination)
    {
        return route;
    }

    if (grid.isStaticBlocked(destination))
    {
        return route;
    }

    struct OpenNode
    {
        games_types::CellCoord cell{};
        int fScore = std::numeric_limits<int>::max();
        int gScore = std::numeric_limits<int>::max();
    };

    struct OpenNodeCompare
    {
        bool operator()(const OpenNode& lhs, const OpenNode& rhs) const
        {
            if (lhs.fScore == rhs.fScore)
            {
                return lhs.gScore > rhs.gScore;
            }
            return lhs.fScore > rhs.fScore;
        }
    };

    const int cols = grid.getCols();
    const int rows = grid.getRows();
    const int totalCells = cols * rows;

    std::vector<int> gScore(totalCells, std::numeric_limits<int>::max());
    std::vector<int> fScore(totalCells, std::numeric_limits<int>::max());
    std::vector<int> cameFrom(totalCells, -1);
    std::vector<bool> closed(totalCells, false);

    const int startIdx = cellToIndex(start, cols);
    gScore[startIdx] = 0;
    fScore[startIdx] = manhattanDistance(start, destination);

    std::priority_queue<OpenNode, std::vector<OpenNode>, OpenNodeCompare> openSet;
    openSet.push(OpenNode{start, fScore[startIdx], gScore[startIdx]});

    bool found = false;
    int destinationIdx = -1;

    while (!openSet.empty())
    {
        const OpenNode currentNode = openSet.top();
        openSet.pop();

        const int currentIdx = cellToIndex(currentNode.cell, cols);
        if (closed[currentIdx])
        {
            continue;
        }

        closed[currentIdx] = true;
        if (currentNode.cell == destination)
        {
            found = true;
            destinationIdx = currentIdx;
            break;
        }

        const auto neighbors = grid.neighbors8(currentNode.cell);
        for (const auto& neighbor : neighbors)
        {
            if (grid.isStaticBlocked(neighbor))
            {
                continue;
            }

            const int neighborIdx = cellToIndex(neighbor, cols);
            if (closed[neighborIdx])
            {
                continue;
            }

            const int tentativeG = gScore[currentIdx] + 1;
            if (tentativeG >= gScore[neighborIdx])
            {
                continue;
            }

            cameFrom[neighborIdx] = currentIdx;
            gScore[neighborIdx] = tentativeG;
            fScore[neighborIdx] = tentativeG + manhattanDistance(neighbor, destination);
            openSet.push(OpenNode{neighbor, fScore[neighborIdx], gScore[neighborIdx]});
        }
    }

    if (!found || destinationIdx < 0)
    {
        return route;
    }

    std::vector<games_types::CellCoord> reversedPath;
    for (int currentIdx = destinationIdx; currentIdx >= 0; currentIdx = cameFrom[currentIdx])
    {
        const int x = currentIdx % cols;
        const int y = currentIdx / cols;
        reversedPath.push_back(games_types::CellCoord{x, y});
        if (currentIdx == startIdx)
        {
            break;
        }
    }

    if (reversedPath.empty())
    {
        return route;
    }

    std::reverse(reversedPath.begin(), reversedPath.end());
    if (!reversedPath.empty() && reversedPath.front() == start)
    {
        reversedPath.erase(reversedPath.begin());
    }

    route.swap(reversedPath);
    return route;
}