#pragma once

#include <cstdint>
#include <unordered_map>
#include <vector>

class SpatialGrid
{
public:
    struct CellCoord
    {
        int x = 0;
        int y = 0;

        bool operator==(const CellCoord& other) const
        {
            return x == other.x && y == other.y;
        }
    };

    enum class MoveStatus : std::uint8_t
    {
        Ok,
        InvalidEntity,
        OutOfBounds,
        StaticBlocked,
        Occupied,
        ReservedByOther
    };

    struct MoveResult
    {
        MoveStatus status = MoveStatus::Ok;
        CellCoord from{};
        CellCoord to{};
        int blockerEntityId = -1;

        bool accepted() const
        {
            return status == MoveStatus::Ok;
        }
    };

    struct GridDelta
    {
        int entityId = 0;
        CellCoord from{};
        CellCoord to{};
    };

    SpatialGrid(int cols = 100, int rows = 100);

    int getCols() const;
    int getRows() const;

    bool inBounds(const CellCoord& cell) const;
    bool inBounds(int x, int y) const;

    bool setStaticBlocked(const CellCoord& cell, bool blocked);
    bool isStaticBlocked(const CellCoord& cell) const;
    void clearStaticBlocked();

    bool placeEntity(int entityId, const CellCoord& cell);
    bool removeEntity(int entityId);
    bool getEntityCell(int entityId, CellCoord& outCell) const;

    bool isOccupied(const CellCoord& cell) const;
    int getOccupant(const CellCoord& cell) const;

    MoveResult tryReserveMove(int entityId, const CellCoord& toCell);
    std::vector<GridDelta> commitReservedMoves();
    void clearReservations();

    std::vector<CellCoord> neighbors4(const CellCoord& cell) const;

private:
    int cols;
    int rows;

    std::vector<std::vector<bool>> staticBlocked;
    std::vector<std::vector<int>> cellOccupant;
    std::unordered_map<int, CellCoord> entityToCell;
    std::unordered_map<int, int> reservationByCellIndex;
    std::unordered_map<int, CellCoord> reservedTargetByEntity;

    int toIndex(const CellCoord& cell) const;
};