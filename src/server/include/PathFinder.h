#pragma once

#include <vector>

#include "GameTypes.h"

class PathFinder
{
    public:
        PathFinder() = default;
        ~PathFinder() = default;

        std::vector<games_types::UnitPosition> buildRoute(
            const games_types::UnitPosition& start,
            float destX,
            float destY) const;
};