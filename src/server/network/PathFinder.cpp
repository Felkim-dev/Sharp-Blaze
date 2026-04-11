#include "PathFinder.h"

std::vector<games_types::UnitPosition> PathFinder::buildRoute(
    const games_types::UnitPosition& start,
    float destX,
    float destY) const
{
    std::vector<games_types::UnitPosition> route;

    constexpr int kSteps = 10;
    const float dx = (destX - start.x) / static_cast<float>(kSteps);
    const float dy = (destY - start.y) / static_cast<float>(kSteps);

    for (int i = 1; i <= kSteps; ++i)
    {
        route.push_back(games_types::UnitPosition{
            start.entity_id,
            start.x + dx * static_cast<float>(i),
            start.y + dy * static_cast<float>(i)});
    }

    return route;
}