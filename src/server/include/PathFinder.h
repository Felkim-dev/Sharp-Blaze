#pragma once

#include <vector>

#include "GameTypes.h"
#include "spatialGrid.h"

class PathFinder
{
    public:
        PathFinder() = default;
        ~PathFinder() = default;

        std::vector<games_types::CellCoord> buildRoute(
            const games_types::CellCoord& start,
            const games_types::CellCoord& destination,
            const SpatialGrid& grid) const;
};