#include "spatialGrid.h"
#include "GameTypes.h"

#include <algorithm>

SpatialGrid::SpatialGrid(int cols, int rows)
	: cols(std::max(1, cols)),
	  rows(std::max(1, rows)),
	  staticBlocked(this->rows, std::vector<bool>(this->cols, false)),
	  cellOccupant(this->rows, std::vector<int>(this->cols, -1))
{
}

int SpatialGrid::getCols() const
{
	return cols;
}

int SpatialGrid::getRows() const
{
	return rows;
}

bool SpatialGrid::inBounds(const games_types::CellCoord& cell) const
{
	return inBounds(cell.x, cell.y);
}

bool SpatialGrid::inBounds(int x, int y) const
{
	return x >= 0 && x < cols && y >= 0 && y < rows;
}

bool SpatialGrid::setStaticBlocked(const games_types::CellCoord& cell, bool blocked)
{
	if (!inBounds(cell))
	{
		return false;
	}

	staticBlocked[cell.y][cell.x] = blocked;
	return true;
}

bool SpatialGrid::isStaticBlocked(const games_types::CellCoord& cell) const
{
	if (!inBounds(cell))
	{
		return true;
	}

	return staticBlocked[cell.y][cell.x];
}

void SpatialGrid::clearStaticBlocked()
{
	for (auto& row : staticBlocked)
	{
		std::fill(row.begin(), row.end(), false);
	}
}

bool SpatialGrid::placeEntity(int entityId, const games_types::CellCoord& cell)
{
	if (entityId <= 0 || !inBounds(cell) || isStaticBlocked(cell) || isOccupied(cell))
	{
		return false;
	}

	auto existingIt = entityToCell.find(entityId);
	if (existingIt != entityToCell.end())
	{
		const games_types::CellCoord old = existingIt->second;
		if (inBounds(old) && cellOccupant[old.y][old.x] == entityId)
		{
			cellOccupant[old.y][old.x] = -1;
		}
	}

	cellOccupant[cell.y][cell.x] = entityId;
	entityToCell[entityId] = cell;
	return true;
}

bool SpatialGrid::removeEntity(int entityId)
{
	auto it = entityToCell.find(entityId);
	if (it == entityToCell.end())
	{
		return false;
	}

	const games_types::CellCoord cell = it->second;
	if (inBounds(cell) && cellOccupant[cell.y][cell.x] == entityId)
	{
		cellOccupant[cell.y][cell.x] = -1;
	}

	entityToCell.erase(it);
	reservedTargetByEntity.erase(entityId);

	for (auto reserveIt = reservationByCellIndex.begin(); reserveIt != reservationByCellIndex.end();)
	{
		if (reserveIt->second == entityId)
		{
			reserveIt = reservationByCellIndex.erase(reserveIt);
		}
		else
		{
			++reserveIt;
		}
	}

	return true;
}

bool SpatialGrid::getEntityCell(int entityId, games_types::CellCoord& outCell) const
{
	auto it = entityToCell.find(entityId);
	if (it == entityToCell.end())
	{
		return false;
	}

	outCell = it->second;
	return true;
}

bool SpatialGrid::isOccupied(const games_types::CellCoord& cell) const
{
	if (!inBounds(cell))
	{
		return true;
	}
	return cellOccupant[cell.y][cell.x] >= 0;
}

int SpatialGrid::getOccupant(const games_types::CellCoord& cell) const
{
	if (!inBounds(cell))
	{
		return -1;
	}
	return cellOccupant[cell.y][cell.x];
}

games_types::MoveResult SpatialGrid::tryReserveMove(int entityId, const games_types::CellCoord& toCell)
{
	games_types::MoveResult result{};
	result.to = toCell;

	auto entityIt = entityToCell.find(entityId);
	if (entityIt == entityToCell.end())
	{
		result.status = games_types::MoveStatus::InvalidEntity;
		return result;
	}

	result.from = entityIt->second;

	if (!inBounds(toCell))
	{
		result.status = games_types::MoveStatus::OutOfBounds;
		return result;
	}

	if (isStaticBlocked(toCell))
	{
		result.status = games_types::MoveStatus::StaticBlocked;
		return result;
	}

	const int currentOccupant = getOccupant(toCell);
	if (currentOccupant >= 0 && currentOccupant != entityId)
	{
		result.status = games_types::MoveStatus::Occupied;
		result.blockerEntityId = currentOccupant;
		return result;
	}

	const int targetIdx = toIndex(toCell);
	auto reserveIt = reservationByCellIndex.find(targetIdx);
	if (reserveIt != reservationByCellIndex.end() && reserveIt->second != entityId)
	{
		result.status = games_types::MoveStatus::ReservedByOther;
		result.blockerEntityId = reserveIt->second;
		return result;
	}

	if (entityIt->second == toCell)
	{
		result.status = games_types::MoveStatus::Ok;
		return result;
	}

	reservationByCellIndex[targetIdx] = entityId;
	reservedTargetByEntity[entityId] = toCell;
	result.status = games_types::MoveStatus::Ok;
	return result;
}

std::vector<games_types::GridDelta> SpatialGrid::commitReservedMoves()
{
	std::vector<games_types::GridDelta> deltas;
	deltas.reserve(reservedTargetByEntity.size());

	for (const auto& moveEntry : reservedTargetByEntity)
	{
		const int entityId = moveEntry.first;
		const games_types::CellCoord toCell = moveEntry.second;

		auto it = entityToCell.find(entityId);
		if (it == entityToCell.end())
		{
			continue;
		}

		const games_types::CellCoord fromCell = it->second;
		if (fromCell == toCell)
		{
			continue;
		}

		if (!inBounds(fromCell) || !inBounds(toCell))
		{
			continue;
		}

		if (cellOccupant[toCell.y][toCell.x] != -1)
		{
			continue;
		}

		cellOccupant[fromCell.y][fromCell.x] = -1;
		cellOccupant[toCell.y][toCell.x] = entityId;
		it->second = toCell;

		deltas.push_back(games_types::GridDelta{entityId, fromCell, toCell});
	}

	clearReservations();
	return deltas;
}

void SpatialGrid::clearReservations()
{
	reservationByCellIndex.clear();
	reservedTargetByEntity.clear();
}

std::vector<games_types::CellCoord> SpatialGrid::neighbors4(const games_types::CellCoord& cell) const
{
	static constexpr int kDx[4] = {1, -1, 0, 0};
	static constexpr int kDy[4] = {0, 0, 1, -1};

	std::vector<games_types::CellCoord> out;
	out.reserve(4);

	for (int i = 0; i < 4; ++i)
	{
		const games_types::CellCoord next{cell.x + kDx[i], cell.y + kDy[i]};
		if (inBounds(next))
		{
			out.push_back(next);
		}
	}

	return out;
}

int SpatialGrid::toIndex(const games_types::CellCoord& cell) const
{
	return (cell.y * cols) + cell.x;
}