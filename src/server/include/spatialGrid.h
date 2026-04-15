#include <vector>
#include <iostream>


#include "GameTypes.h"


class SpatialGrid
{
    private:
        std::vector<std::vector<int>> grid;
        int cols = 100;
        int rows = 100;
        std::vector<std::vector<bool>> staticBlocked;


    public:
        int getPosition(int entitityId);
        games_types::Cell entityToCell(int entityId);
        int cellToEntity(games_types::Cell positioin);
        
};