#pragma once

#include <cstdint>
#include <unordered_map>
#include <vector>
#include "GameTypes.h"

class SpatialGrid
{
public:
    SpatialGrid(int cols = 100, int rows = 100);

    int getCols() const;
    int getRows() const;

    bool inBounds(const games_types::CellCoord& cell) const;
    bool inBounds(int x, int y) const;

    bool setStaticBlocked(const games_types::CellCoord& cell, bool blocked);
    bool isStaticBlocked(const games_types::CellCoord& cell) const;
    void clearStaticBlocked();

    bool placeEntity(int entityId, const games_types::CellCoord& cell);
    bool removeEntity(int entityId);
    bool getEntityCell(int entityId, games_types::CellCoord& outCell) const;

    bool isOccupied(const games_types::CellCoord& cell) const;
    int getOccupant(const games_types::CellCoord& cell) const;

    games_types::MoveResult tryReserveMove(int entityId, const games_types::CellCoord& toCell);
    std::vector<games_types::GridDelta> commitReservedMoves();
    void clearReservations();

    std::vector<games_types::CellCoord> neighbors4(const games_types::CellCoord& cell) const;

private:
    int cols;
    int rows;

    std::vector<std::vector<bool>> staticBlocked;
    std::vector<std::vector<int>> cellOccupant;
    std::unordered_map<int, games_types::CellCoord> entityToCell;
    std::unordered_map<int, int> reservationByCellIndex;
    std::unordered_map<int, games_types::CellCoord> reservedTargetByEntity;

    int toIndex(const games_types::CellCoord& cell) const;
};