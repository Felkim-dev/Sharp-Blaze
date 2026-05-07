#include "GameSession.h"

#include <filesystem>
#include <fstream>
#include <queue>
#include <random>
#include <limits>
#include <unordered_set>
#include <vector>

#include "third_party/json.hpp"

using json = nlohmann::json;

namespace
{
constexpr int kGridCols = 100;
constexpr int kGridRows = 100;
constexpr int kReservedPaddingCells = 5;
constexpr int kMazeAttemptLimit = 10;
constexpr int kObstacleSpacing = 10;
constexpr int kObstacleWallLength = 14;
constexpr int kCornerArmLength = 8;
constexpr float kObstacleFillChance = 0.34f;
constexpr float kLongWallChance = 0.72f;
constexpr float kCornerChance = 0.38f;

struct CellCoordHash
{
	std::size_t operator()(const games_types::CellCoord& cell) const noexcept
	{
		const std::size_t x = static_cast<std::size_t>(cell.x);
		const std::size_t y = static_cast<std::size_t>(cell.y);
		return (y << 16U) ^ x;
	}
};

int readIntField(const json& node, const std::initializer_list<const char*>& keys, int fallback)
{
	for (const char* key : keys)
	{
		if (node.contains(key) && node[key].is_number_integer())
		{
			return node[key].get<int>();
		}
	}
	return fallback;
}

games_types::CellCoord worldToGridCell(float x, float y)
{
	return games_types::CellCoord{
		std::max(0, std::min(kGridCols - 1, static_cast<int>(x / 50.0f))),
		std::max(0, std::min(kGridRows - 1, static_cast<int>(y / 50.0f)))};
}

void addReservedFootprint(std::unordered_set<games_types::CellCoord, CellCoordHash>& reservedCells,
					  int centerX,
					  int centerY,
					  int padding)
{
	for (int offsetY = -padding; offsetY <= padding; ++offsetY)
	{
		for (int offsetX = -padding; offsetX <= padding; ++offsetX)
		{
			const int cellX = centerX + offsetX;
			const int cellY = centerY + offsetY;
			if (cellX < 0 || cellX >= kGridCols || cellY < 0 || cellY >= kGridRows)
			{
				continue;
			}

			reservedCells.insert(games_types::CellCoord{cellX, cellY});
		}
	}
}

void buildReservedCells(const std::unordered_map<int, UnitPosition>& structures,
					const std::unordered_map<int, ResourceNode>& resources,
					const std::unordered_map<int, UnitPosition>& units,
					const std::unordered_map<int, ShopUnit>& shops,
					std::unordered_set<games_types::CellCoord, CellCoordHash>& reservedCells)
{
	reservedCells.clear();

	for (const auto& entry : structures)
	{
		const games_types::CellCoord cell = worldToGridCell(entry.second.x, entry.second.y);
		addReservedFootprint(reservedCells, cell.x, cell.y, kReservedPaddingCells);
	}

	for (const auto& entry : resources)
	{
		const games_types::CellCoord cell = worldToGridCell(entry.second.x, entry.second.y);
		addReservedFootprint(reservedCells, cell.x, cell.y, kReservedPaddingCells);
	}

	for (const auto& entry : units)
	{
		const games_types::CellCoord cell = worldToGridCell(entry.second.x, entry.second.y);
		addReservedFootprint(reservedCells, cell.x, cell.y, kReservedPaddingCells);
	}

	for (const auto& entry : shops)
	{
		const games_types::CellCoord cell = worldToGridCell(entry.second.x, entry.second.y);
		addReservedFootprint(reservedCells, cell.x, cell.y, kReservedPaddingCells);
	}
}

void generateObstacleField(unsigned int seed, std::vector<std::vector<std::uint8_t>>& openGrid)
{
	openGrid.assign(kGridRows, std::vector<std::uint8_t>(kGridCols, 1));

	std::mt19937 rng(seed);
	std::uniform_real_distribution<float> chance(0.0f, 1.0f);
	std::uniform_int_distribution<int> offset(0, kObstacleSpacing - 1);

	for (int baseY = 6; baseY < kGridRows - 6; baseY += kObstacleSpacing)
	{
		for (int baseX = 6; baseX < kGridCols - 6; baseX += kObstacleSpacing)
		{
			if (chance(rng) > kObstacleFillChance)
			{
				continue;
			}

			const bool horizontalWall = chance(rng) < kLongWallChance;
			if (horizontalWall)
			{
				const int startX = std::max(1, std::min(kGridCols - kObstacleWallLength - 2, baseX - (kObstacleWallLength / 2) + offset(rng) / 2));
				const int y = std::max(2, std::min(kGridRows - 3, baseY + (offset(rng) % 3) - 1));
				for (int x = startX; x < startX + kObstacleWallLength; ++x)
				{
					openGrid[y][x] = 0;
				}

				if (chance(rng) < kCornerChance)
				{
					const bool cornerUp = chance(rng) < 0.5f;
					const int cornerX = startX + kObstacleWallLength - 1;
					const int cornerStartY = cornerUp ? std::max(1, y - kCornerArmLength + 1) : y;
					const int cornerEndY = cornerUp ? y : std::min(kGridRows - 2, y + kCornerArmLength - 1);
					for (int armY = cornerStartY; armY <= cornerEndY; ++armY)
					{
						openGrid[armY][cornerX] = 0;
					}
				}
			}
			else
			{
				const int x = std::max(2, std::min(kGridCols - 3, baseX + (offset(rng) % 3) - 1));
				const int startY = std::max(1, std::min(kGridRows - kObstacleWallLength - 2, baseY - (kObstacleWallLength / 2) + offset(rng) / 2));
				for (int y = startY; y < startY + kObstacleWallLength; ++y)
				{
					openGrid[y][x] = 0;
				}

				if (chance(rng) < kCornerChance)
				{
					const bool cornerLeft = chance(rng) < 0.5f;
					const int cornerY = startY + kObstacleWallLength - 1;
					const int cornerStartX = cornerLeft ? std::max(1, x - kCornerArmLength + 1) : x;
					const int cornerEndX = cornerLeft ? x : std::min(kGridCols - 2, x + kCornerArmLength - 1);
					for (int armX = cornerStartX; armX <= cornerEndX; ++armX)
					{
						openGrid[cornerY][armX] = 0;
					}
				}
			}
		}
	}
}

bool isTraversableCell(const std::vector<std::vector<std::uint8_t>>& openGrid,
					  const std::unordered_set<games_types::CellCoord, CellCoordHash>& reservedCells,
					  const games_types::CellCoord& cell)
{
	if (cell.x < 0 || cell.x >= kGridCols || cell.y < 0 || cell.y >= kGridRows)
	{
		return false;
	}

	return openGrid[cell.y][cell.x] != 0 || reservedCells.find(cell) != reservedCells.end();
}

bool hasTraversablePath(const std::vector<std::vector<std::uint8_t>>& openGrid,
					   const std::unordered_set<games_types::CellCoord, CellCoordHash>& reservedCells,
					   const games_types::CellCoord& start,
					   const games_types::CellCoord& goal)
{
	if (!isTraversableCell(openGrid, reservedCells, start) || !isTraversableCell(openGrid, reservedCells, goal))
	{
		return false;
	}

	std::queue<games_types::CellCoord> pending;
	std::vector<std::vector<std::uint8_t>> visited(kGridRows, std::vector<std::uint8_t>(kGridCols, 0));
	pending.push(start);
	visited[start.y][start.x] = 1;

	const int dx[4] = {1, -1, 0, 0};
	const int dy[4] = {0, 0, 1, -1};

	while (!pending.empty())
	{
		const games_types::CellCoord current = pending.front();
		pending.pop();

		if (current == goal)
		{
			return true;
		}

		for (int index = 0; index < 4; ++index)
		{
			const games_types::CellCoord next{current.x + dx[index], current.y + dy[index]};
			if (!isTraversableCell(openGrid, reservedCells, next) || visited[next.y][next.x])
			{
				continue;
			}

			visited[next.y][next.x] = 1;
			pending.push(next);
		}
	}

	return false;
}

std::vector<games_types::CellCoord> buildObstacleCells(const std::vector<std::vector<std::uint8_t>>& openGrid,
										  const std::unordered_set<games_types::CellCoord, CellCoordHash>& reservedCells)
{
	std::vector<games_types::CellCoord> obstacleCells;
	obstacleCells.reserve((kGridCols * kGridRows) / 2);

	for (int y = 0; y < kGridRows; ++y)
	{
		for (int x = 0; x < kGridCols; ++x)
		{
			const games_types::CellCoord cell{x, y};
			if (reservedCells.find(cell) != reservedCells.end())
			{
				continue;
			}

			if (openGrid[y][x] == 0)
			{
				obstacleCells.push_back(cell);
			}
		}
	}

	return obstacleCells;
}
}

GameSession::GameSession(int player1, int player2, int sessionId, bool arcadeMode)
	: player1(player1), player2(player2), sessionId(sessionId), arcadeMode(arcadeMode)
{
	initializeGameState();
}

int GameSession::getSessionId() const
{
	return sessionId;
}

bool GameSession::hasPlayer(int playerId) const
{
	return playerId == player1 || playerId == player2;
}

int GameSession::ownerFromEntityId(int entityId) const
{
	if (games_types::id_ranges::p1Structures.contains(entityId) ||
		games_types::id_ranges::p1Attackers.contains(entityId) ||
		games_types::id_ranges::p1Collectors.contains(entityId))
	{
		return 1;
	}

	if (games_types::id_ranges::p2Structures.contains(entityId) ||
		games_types::id_ranges::p2Attackers.contains(entityId) ||
		games_types::id_ranges::p2Collectors.contains(entityId))
	{
		return 2;
	}

	if (games_types::id_ranges::p1Bombs.contains(entityId))
	{
		return 1;
	}

	if (games_types::id_ranges::p2Bombs.contains(entityId))
	{
		return 2;
	}

	return 0;
}

void GameSession::loadCombatConfigNoLock()
{
	attackerHp = 100;
	attackerDamage = 20;
	attackerRange = 1000;
	attackerCooldownMs = 500;
	collectorHp = 100;
	baseHp = 1500;
	minDamage = 1;
    
	const std::vector<std::filesystem::path> candidates = {
		std::filesystem::path("src/config/combat_stats.json"),
		std::filesystem::path("../src/config/combat_stats.json"),
		std::filesystem::path("../../src/config/combat_stats.json"),
		std::filesystem::path("../../../src/config/combat_stats.json")
	};

	std::filesystem::path selectedPath;
	for (const auto& p : candidates)
	{
		if (std::filesystem::exists(p))
		{
			selectedPath = p;
			break;
		}
	}

	if (selectedPath.empty())
	{
		return;
	}

	std::ifstream file(selectedPath);
	if (!file.is_open())
	{
		return;
	}

	json root = json::parse(file, nullptr, false);
	if (root.is_discarded() || !root.is_object())
	{
		return;
	}

	if (root.contains("combat_rules") && root["combat_rules"].is_object())
	{
		const json& rules = root["combat_rules"];
		minDamage = std::max(1, readIntField(rules, {"min_damage"}, minDamage));
	}

	if (root.contains("units") && root["units"].is_object())
	{
		const json& unitsCfg = root["units"];
		if (unitsCfg.contains("attacker") && unitsCfg["attacker"].is_object())
		{
			const json& attackerCfg = unitsCfg["attacker"];
			attackerHp = std::max(1, readIntField(attackerCfg, {"hp"}, attackerHp));
			attackerDamage = std::max(1, readIntField(attackerCfg, {"attack", "atack"}, attackerDamage));
			attackerRange = std::max(1, readIntField(attackerCfg, {"range"}, attackerRange));
			attackerCooldownMs = std::max(1, readIntField(attackerCfg, {"cooldown_ms", "cooldown"}, attackerCooldownMs));
		}

		if (unitsCfg.contains("collector") && unitsCfg["collector"].is_object())
		{
			const json& collectorCfg = unitsCfg["collector"];
			collectorHp = std::max(1, readIntField(collectorCfg, {"hp"}, collectorHp));
		}

		if (unitsCfg.contains("base") && unitsCfg["base"].is_object())
		{
			const json& baseCfg = unitsCfg["base"];
			baseHp = std::max(1, readIntField(baseCfg, {"hp"}, baseHp));
		}
	}
}

void GameSession::loadArcadeConfigNoLock()
{
	arcadeStartingGold = 500;
	arcadeBombCost = 1000;
	arcadeAttackerCost = 200;
	arcadeBombHp = 200;
	arcadeBombSpeed = 80;
	arcadeKillGoldPerUnit = 100;
	arcadeKillGoldPerBomb = 500;
	arcadeAutoSpawnIntervalMs = 10000;
	arcadeInitialAttackers = 3;
	arcadeGameDurationSeconds = 300;
	arcadeBaseImmunityToAttackers = true;
	arcadeExplosionRadius = 250;

	const std::vector<std::filesystem::path> candidates = {
		std::filesystem::path("src/config/arcade_config.json"),
		std::filesystem::path("../src/config/arcade_config.json"),
		std::filesystem::path("../../src/config/arcade_config.json"),
		std::filesystem::path("../../../src/config/arcade_config.json")
	};

	std::filesystem::path selectedPath;
	for (const auto& p : candidates)
	{
		if (std::filesystem::exists(p))
		{
			selectedPath = p;
			break;
		}
	}

	if (selectedPath.empty())
	{
		return;
	}

	std::ifstream file(selectedPath);
	if (!file.is_open())
	{
		return;
	}

	json root = json::parse(file, nullptr, false);
	if (root.is_discarded() || !root.is_object())
	{
		return;
	}

	if (root.contains("arcade_mode") && root["arcade_mode"].is_object())
	{
		const json& mode = root["arcade_mode"];
		arcadeStartingGold = std::max(0, readIntField(mode, {"starting_gold"}, arcadeStartingGold));
		arcadeBombCost = std::max(0, readIntField(mode, {"bomb_cost"}, arcadeBombCost));
		arcadeAttackerCost = std::max(0, readIntField(mode, {"attacker_cost"}, arcadeAttackerCost));
		arcadeBombHp = std::max(0, readIntField(mode, {"bomb_hp"}, arcadeBombHp));
		arcadeBombSpeed = std::max(0, readIntField(mode, {"bomb_speed"}, arcadeBombSpeed));
		arcadeKillGoldPerUnit = std::max(0, readIntField(mode, {"kill_gold_per_unit"}, arcadeKillGoldPerUnit));
		arcadeKillGoldPerBomb = std::max(0, readIntField(mode, {"kill_gold_per_bomb"}, arcadeKillGoldPerBomb));
		arcadeAutoSpawnIntervalMs = std::max(0, readIntField(mode, {"auto_spawn_interval_ms"}, arcadeAutoSpawnIntervalMs));
		arcadeInitialAttackers = std::max(0, readIntField(mode, {"initial_attackers"}, arcadeInitialAttackers));
		arcadeGameDurationSeconds = std::max(0, readIntField(mode, {"game_duration_seconds"}, arcadeGameDurationSeconds));
		arcadeExplosionRadius = std::max(0, readIntField(mode, {"explosion_radius"}, arcadeExplosionRadius));

		if (mode.contains("base_immunity_to_attackers") && mode["base_immunity_to_attackers"].is_boolean())
		{
			arcadeBaseImmunityToAttackers = mode["base_immunity_to_attackers"].get<bool>();
		}
	}
}

int GameSession::getPlayerGold(int playerId) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = playerGold.find(playerId);
	if (it == playerGold.end())
	{
		return 0;
	}
	return it->second;
}

bool GameSession::trySpendGold(int playerId, int amount)
{
	if (amount <= 0)
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	if (playerId != player1 && playerId != player2)
	{
		return false;
	}

	auto it = playerGold.find(playerId);
	if (it == playerGold.end() || it->second < amount)
	{
		return false;
	}

	it->second -= amount;
	playerGoldSpent[playerId] += amount;
	return true;
}

bool GameSession::addGold(int playerId, int amount)
{
	if (amount <= 0)
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	if (playerId != player1 && playerId != player2)
	{
		return false;
	}

	auto it = playerGold.find(playerId);
	if (it == playerGold.end())
	{
		return false;
	}

	it->second += amount;
	pendingEconomyTransactions.push_back(games_types::EconomyTransaction{
		playerId,
		amount,
		it->second,
		"collector_deposit"});
	return true;
}

int GameSession::getPlayerSpentGold(int playerId) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = playerGoldSpent.find(playerId);
	if (it == playerGoldSpent.end())
	{
		return 0;
	}
	return it->second;
}

std::unordered_map<int, int> GameSession::getPlayerGoldSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return playerGold;
}

std::vector<games_types::EconomyTransaction> GameSession::drainEconomyTransactions()
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<games_types::EconomyTransaction> events;
	events.swap(pendingEconomyTransactions);
	return events;
}

int GameSession::getUnitGoldCost(games_types::EntityType unitType) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = unitGoldCostByType.find(unitType);
	if (it == unitGoldCostByType.end())
	{
		return -1;
	}
	return it->second;
}

bool GameSession::isUnitPurchasable(games_types::EntityType unitType) const
{
	return getUnitGoldCost(unitType) > 0;
}

bool GameSession::trySpendGoldForUnit(int playerId, games_types::EntityType unitType, int quantity)
{
	if (quantity <= 0)
	{
		return false;
	}

	const int unitCost = getUnitGoldCost(unitType);
	if (unitCost <= 0)
	{
		return false;
	}

	if (unitCost > std::numeric_limits<int>::max() / quantity)
	{
		return false;
	}

	const int totalCost = unitCost * quantity;
	return trySpendGold(playerId, totalCost);
}

bool GameSession::allocateUnitId(int playerId, games_types::EntityType unitType, int& outUnitId)
{
	std::lock_guard<std::mutex> lock(sessionMutex);

	if (unitType == games_types::EntityType::Attacker)
	{
		if (playerId == player1)
		{
			if (nextP1AttackerId > games_types::id_ranges::p1Attackers.maxId)
			{
				return false;
			}
			outUnitId = nextP1AttackerId++;
			return true;
		}
		if (playerId == player2)
		{
			if (nextP2AttackerId > games_types::id_ranges::p2Attackers.maxId)
			{
				return false;
			}
			outUnitId = nextP2AttackerId++;
			return true;
		}
		return false;
	}

	if (unitType == games_types::EntityType::Collector)
	{
		if (playerId == player1)
		{
			if (nextP1CollectorId > games_types::id_ranges::p1Collectors.maxId)
			{
				return false;
			}
			outUnitId = nextP1CollectorId++;
			return true;
		}
		if (playerId == player2)
		{
			if (nextP2CollectorId > games_types::id_ranges::p2Collectors.maxId)
			{
				return false;
			}
			outUnitId = nextP2CollectorId++;
			return true;
		}
	}

	if (unitType == games_types::EntityType::Bomb)
	{
		if (playerId == player1)
		{
			if (nextP1BombId > games_types::id_ranges::p1Bombs.maxId)
			{
				return false;
			}
			outUnitId = nextP1BombId++;
			return true;
		}
		if (playerId == player2)
		{
			if (nextP2BombId > games_types::id_ranges::p2Bombs.maxId)
			{
				return false;
			}
			outUnitId = nextP2BombId++;
			return true;
		}
	}

	return false;
}

bool GameSession::tryPurchaseUnit(
	int playerId,
	games_types::EntityType unitType,
	int quantity,
	int& outUnitId,
	int& outNewBalance,
	std::string& outReason)
{
	outUnitId = -1;
	outNewBalance = 0;
	outReason.clear();

	if (quantity != 1)
	{
		outReason = "unsupported_quantity";
		return false;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	if (playerId != player1 && playerId != player2)
	{
		outReason = "invalid_player";
		return false;
	}

	auto costIt = unitGoldCostByType.find(unitType);
	if (costIt == unitGoldCostByType.end() || costIt->second <= 0)
	{
		outReason = "unit_type_not_in_catalog";
		return false;
	}

	int candidateId = -1;
	if (unitType == games_types::EntityType::Attacker)
	{
		if (playerId == player1)
		{
			if (nextP1AttackerId > games_types::id_ranges::p1Attackers.maxId)
			{
				outReason = "id_range_exhausted";
				return false;
			}
			candidateId = nextP1AttackerId;
		}
		else
		{
			if (nextP2AttackerId > games_types::id_ranges::p2Attackers.maxId)
			{
				outReason = "id_range_exhausted";
				return false;
			}
			candidateId = nextP2AttackerId;
		}
	}
	else if (unitType == games_types::EntityType::Collector)
	{
		if (playerId == player1)
		{
			if (nextP1CollectorId > games_types::id_ranges::p1Collectors.maxId)
			{
				outReason = "id_range_exhausted";
				return false;
			}
			candidateId = nextP1CollectorId;
		}
		else
		{
			if (nextP2CollectorId > games_types::id_ranges::p2Collectors.maxId)
			{
				outReason = "id_range_exhausted";
				return false;
			}
			candidateId = nextP2CollectorId;
		}
	}
	else if (unitType == games_types::EntityType::Bomb)
	{
		if (playerId == player1)
		{
			if (nextP1BombId > games_types::id_ranges::p1Bombs.maxId)
			{
				outReason = "id_range_exhausted";
				return false;
			}
			candidateId = nextP1BombId;
		}
		else
		{
			if (nextP2BombId > games_types::id_ranges::p2Bombs.maxId)
			{
				outReason = "id_range_exhausted";
				return false;
			}
			candidateId = nextP2BombId;
		}
	}
	else
	{
		outReason = "unit_type_not_purchasable";
		return false;
	}

	auto goldIt = playerGold.find(playerId);
	if (goldIt == playerGold.end() || goldIt->second < costIt->second)
	{
		outReason = "insufficient_gold";
		return false;
	}

	goldIt->second -= costIt->second;
	playerGoldSpent[playerId] += costIt->second;
	if (unitType == games_types::EntityType::Attacker)
	{
		if (playerId == player1)
		{
			++nextP1AttackerId;
		}
		else
		{
			++nextP2AttackerId;
		}
	}
	else if (unitType == games_types::EntityType::Collector)
	{
		if (playerId == player1)
		{
			++nextP1CollectorId;
		}
		else
		{
			++nextP2CollectorId;
		}
	}
	else if (unitType == games_types::EntityType::Bomb)
	{
		if (playerId == player1)
		{
			++nextP1BombId;
		}
		else
		{
			++nextP2BombId;
		}
	}

	outUnitId = candidateId;
	outNewBalance = goldIt->second;
	outReason = "ok";
	return true;
}

void GameSession::registerUdpClient(const std::string& clientKey, const RegisteredClient& client)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	udpClients[clientKey] = client;
}

bool GameSession::isUdpClientRegistered(const std::string& clientKey) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return udpClients.find(clientKey) != udpClients.end();
}

std::vector<RegisteredClient> GameSession::getUdpClientsSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<RegisteredClient> clients;
	clients.reserve(udpClients.size());

	for (const auto& entry : udpClients)
	{
		clients.push_back(entry.second);
	}
    
	return clients;
}

void GameSession::upsertUnitPosition(int id, float x, float y)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = units.find(id);

	if (it != units.end())
	{
		it->second.x = x;
		it->second.y = y;
		return;
	}

	units[id] = UnitPosition{id, x, y};
}

std::vector<UnitPosition> GameSession::getUnitsSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<UnitPosition> snapshot;
	snapshot.reserve(units.size());

	for (const auto& entry : units)
	{
		// Filter out recently destroyed units to prevent UDP/TCP desynchronization
		if (recentlyDestroyedUnitIds.find(entry.first) == recentlyDestroyedUnitIds.end())
		{
			snapshot.push_back(entry.second);
		}
	}
	return snapshot;
}

void GameSession::setUnitsSnapshot(const std::vector<UnitPosition>& newUnits)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	units.clear();
	for (const auto& unit : newUnits)
	{
		units[unit.entity_id] = unit;
	}
}

void GameSession::clearRecentlyDestroyedUnits()
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	recentlyDestroyedUnitIds.clear();
}

std::vector<CollectorUnit> GameSession::getCollectorsSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<CollectorUnit> snapshot;
	snapshot.reserve(collectors.size());

	for (const auto& entry : collectors)
	{
		snapshot.push_back(entry.second);
	}

	return snapshot;
}

void GameSession::setCollectorsSnapshot(const std::vector<CollectorUnit>& newCollectors)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	collectors.clear();

	for (const auto& collector : newCollectors)
	{
		collectors[collector.entityId] = collector;
	}
}

bool GameSession::getCollector(int collectorId, CollectorUnit& outCollector) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = collectors.find(collectorId);
	if (it == collectors.end())
	{
		return false;
	}

	outCollector = it->second;
	return true;
}

bool GameSession::upsertCollector(const CollectorUnit& collector)
{
	if (collector.entityId <= 0)
	{
		return false;
	}

	const bool isP1Collector = games_types::id_ranges::p1Collectors.contains(collector.entityId);
	const bool isP2Collector = games_types::id_ranges::p2Collectors.contains(collector.entityId);
	if (!isP1Collector && !isP2Collector)
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	collectors[collector.entityId] = collector;
	entityMaxHp[collector.entityId] = std::max(1, collector.maxHp > 0 ? collector.maxHp : collectorHp);
	entityCurrentHp[collector.entityId] = std::max(0, collector.currentHp > 0 ? collector.currentHp : entityMaxHp[collector.entityId]);
	return true;
}

std::vector<UnitPosition> GameSession::getStructuresSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<UnitPosition> snapshot;
	snapshot.reserve(structures.size());

	for (const auto& entry : structures)
	{
		snapshot.push_back(entry.second);
	}
	return snapshot;
}

std::vector<ResourceNode> GameSession::getResourcesSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<ResourceNode> snapshot;
	snapshot.reserve(resources.size());

	for (const auto& entry : resources)
	{
		snapshot.push_back(entry.second);
	}

	return snapshot;
}

std::vector<ShopUnit> GameSession::getShopsSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<ShopUnit> snapshot;
	snapshot.reserve(shops.size());

	for (const auto& entry : shops)
	{
		snapshot.push_back(entry.second);
	}

	return snapshot;
}

std::vector<games_types::StaticObstacle> GameSession::getStaticObstaclesSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<games_types::StaticObstacle> snapshot;
	snapshot.reserve(staticObstacles.size());

	for (const auto& entry : staticObstacles)
	{
		snapshot.push_back(entry.second);
	}

	return snapshot;
}

bool GameSession::getShopAuthorizationState(int playerId, games_types::ShopAuthorizationState& outState) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = shopAuthorizationByPlayer.find(playerId);
	if (it == shopAuthorizationByPlayer.end())
	{
		outState = games_types::ShopAuthorizationState{};
		return false;
	}

	outState = it->second;
	return true;
}

void GameSession::setShopAuthorizationState(int playerId, const games_types::ShopAuthorizationState& state)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	shopAuthorizationByPlayer[playerId] = state;
}

void GameSession::clearShopAuthorizationState(int playerId)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	shopAuthorizationByPlayer.erase(playerId);
}

bool GameSession::upsertResourceNode(const ResourceNode& node)
{
	if (node.entityId <= 0 || !games_types::id_ranges::resourceMines.contains(node.entityId))
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	resources[node.entityId] = node;
	return true;
}

int GameSession::extractResource(int resourceId, int requestedAmount)
{
	if (requestedAmount <= 0)
	{
		return 0;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = resources.find(resourceId);
	if (it == resources.end())
	{
		return 0;
	}

	ResourceNode& node = it->second;
	if (node.remainingCapacity <= 0)
	{
		return 0;
	}

	const int extracted = std::min(node.remainingCapacity, requestedAmount);
	node.remainingCapacity -= extracted;
	return extracted;
}

bool GameSession::registerSpawnedUnit(int unitId, int ownerPlayerId, games_types::EntityType unitType)
{
	if (unitId <= 0 || !hasPlayer(ownerPlayerId))
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	int hp = 0;
	if (unitType == games_types::EntityType::Collector)
	{
		hp = collectorHp;
	}
	else if (unitType == games_types::EntityType::Attacker)
	{
		hp = attackerHp;
	}
	else if (unitType == games_types::EntityType::Bomb)
	{
		hp = arcadeBombHp;
	}
	else
	{
		return false;
	}

	entityMaxHp[unitId] = hp;
	entityCurrentHp[unitId] = hp;
	return true;
}

bool GameSession::getEntityPosition(int entityId, UnitPosition& outPosition) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto unitIt = units.find(entityId);
	if (unitIt != units.end())
	{
		outPosition = unitIt->second;
		return true;
	}

	auto structureIt = structures.find(entityId);
	if (structureIt != structures.end())
	{
		outPosition = structureIt->second;
		return true;
	}

	auto bombIt = bombs.find(entityId);
	if (bombIt != bombs.end())
	{
		outPosition = bombIt->second;
		return true;
	}

	return false;
}

bool GameSession::getEntityHealth(int entityId, int& outCurrentHp, int& outMaxHp) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto curIt = entityCurrentHp.find(entityId);
	auto maxIt = entityMaxHp.find(entityId);
	if (curIt == entityCurrentHp.end() || maxIt == entityMaxHp.end())
	{
		return false;
	}

	outCurrentHp = curIt->second;
	outMaxHp = maxIt->second;
	return true;
}

bool GameSession::applyDamageToEntity(int attackerPlayerId,
	                                 int entityId,
	                                 int rawDamage,
	                                 games_types::DamageResolution& outResolution)
{
	outResolution = games_types::DamageResolution{};
	if (rawDamage <= 0)
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	if (gameOver)
	{
		return false;
	}

	auto curIt = entityCurrentHp.find(entityId);
	auto maxIt = entityMaxHp.find(entityId);
	if (curIt == entityCurrentHp.end() || maxIt == entityMaxHp.end())
	{
		return false;
	}

	const int ownerPlayerId = ownerFromEntityId(entityId);
	if (ownerPlayerId == 0 || ownerPlayerId == attackerPlayerId)
	{
		return false;
	}

	const int damage = std::max(minDamage, rawDamage);
	curIt->second = std::max(0, curIt->second - damage);

	outResolution.applied = true;
	outResolution.entityId = entityId;
	outResolution.ownerPlayerId = ownerPlayerId;
	outResolution.currentHp = curIt->second;
	outResolution.maxHp = maxIt->second;
	outResolution.destroyed = curIt->second == 0;

	if (outResolution.destroyed)
	{
		units.erase(entityId);
		collectors.erase(entityId);
		bombs.erase(entityId);
		recentlyDestroyedUnitIds.insert(entityId);
		const bool isStructure = games_types::id_ranges::p1Structures.contains(entityId) ||
		                        games_types::id_ranges::p2Structures.contains(entityId);
		if (!isStructure)
		{
			entityCurrentHp.erase(entityId);
			entityMaxHp.erase(entityId);
		}

		// Arcade mode kill-gold rewards
		if (arcadeMode)
		{
			const games_types::EntityType destroyedType = games_types::classifyEntityTypeFromId(entityId);
			int goldReward = 0;
			std::string reason;
			if (destroyedType == games_types::EntityType::Bomb)
			{
				goldReward = arcadeKillGoldPerBomb;
				reason = "bomb_destroyed";
			}
			else if (!isStructure)
			{
				goldReward = arcadeKillGoldPerUnit;
				reason = "unit_killed";
			}

			if (goldReward > 0)
			{
				auto goldIt = playerGold.find(attackerPlayerId);
				if (goldIt != playerGold.end())
				{
					goldIt->second += goldReward;
					pendingEconomyTransactions.push_back(games_types::EconomyTransaction{
						attackerPlayerId,
						goldReward,
						goldIt->second,
						reason});
				}
			}
		}

		if (isStructure)
		{
			gameOver = true;
			winnerPlayerId = ownerPlayerId == 1 ? 2 : 1;
			outResolution.gameOver = true;
			outResolution.winnerPlayerId = winnerPlayerId;
		}
	}

	return true;
}

int GameSession::getBaseEntityId(int playerId) const
{
	if (playerId == 1)
	{
		return games_types::id_ranges::p1Structures.minId;
	}
	if (playerId == 2)
	{
		return games_types::id_ranges::p2Structures.minId;
	}
	return -1;
}

int GameSession::getBaseHealth(int playerId) const
{
	const int baseId = getBaseEntityId(playerId);
	if (baseId < 0)
	{
		return 0;
	}

	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = entityCurrentHp.find(baseId);
	if (it == entityCurrentHp.end())
	{
		return 0;
	}
	return it->second;
}

bool GameSession::isGameOver(int& outWinnerPlayerId) const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	outWinnerPlayerId = winnerPlayerId;
	return gameOver;
}

int GameSession::getAttackerDamage() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return attackerDamage;
}

int GameSession::getAttackerRange() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return attackerRange;
}

int GameSession::getAttackerCooldownMs() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return attackerCooldownMs;
}

int GameSession::getMinDamage() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return minDamage;
}

int GameSession::getArcadeExplosionRadius() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return arcadeExplosionRadius;
}

int GameSession::getArcadeKillGoldPerBomb() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return arcadeKillGoldPerBomb;
}

int GameSession::getArcadeKillGoldPerUnit() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return arcadeKillGoldPerUnit;
}

int GameSession::getArcadeAutoSpawnIntervalMs() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return arcadeAutoSpawnIntervalMs;
}

std::chrono::steady_clock::time_point GameSession::getLastAutoSpawnTime() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return lastAutoSpawnTime;
}

void GameSession::setLastAutoSpawnTime(std::chrono::steady_clock::time_point t)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	lastAutoSpawnTime = t;
}

int GameSession::getArcadeBombHp() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	return arcadeBombHp;
}

void GameSession::setGameOver(int winnerId)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	if (!gameOver)
	{
		gameOver = true;
		winnerPlayerId = winnerId;
	}
}

void GameSession::upsertBombPosition(int id, float x, float y)
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	auto it = bombs.find(id);
	if (it != bombs.end())
	{
		it->second.x = x;
		it->second.y = y;
		return;
	}
	bombs[id] = UnitPosition{id, x, y};
}

std::vector<UnitPosition> GameSession::getBombsSnapshot() const
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	std::vector<UnitPosition> snapshot;
	snapshot.reserve(bombs.size());
	for (const auto& entry : bombs)
	{
		if (recentlyDestroyedUnitIds.find(entry.first) == recentlyDestroyedUnitIds.end())
		{
			snapshot.push_back(entry.second);
		}
	}
	return snapshot;
}

void GameSession::initializeGameState()
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	loadCombatConfigNoLock();
	loadArcadeConfigNoLock();

	unitGoldCostByType.clear();
	unitGoldCostByType[games_types::EntityType::Attacker] = 200;
	unitGoldCostByType[games_types::EntityType::Collector] = 100;

	playerGold[player1] = kInitialGold;
	playerGold[player2] = kInitialGold;
	playerGoldSpent[player1] = 0;
	playerGoldSpent[player2] = 0;
	pendingEconomyTransactions.clear();
	shopAuthorizationByPlayer.clear();
	entityCurrentHp.clear();
	entityMaxHp.clear();
	gameOver = false;
	winnerPlayerId = 0;

	if (arcadeMode)
	{
		// Arcade mode: no collectors, no mines, config-driven initial attackers per player
		unitGoldCostByType[games_types::EntityType::Attacker] = arcadeAttackerCost;
		playerGold[player1] = arcadeStartingGold;
		playerGold[player2] = arcadeStartingGold;

		structures[0] = UnitPosition{0, 300.0f, 4700.0f};
		structures[5000] = UnitPosition{5000, 4700.0f, 300.0f};
		entityCurrentHp[0] = baseHp;
		entityCurrentHp[5000] = baseHp;
		entityMaxHp[0] = baseHp;
		entityMaxHp[5000] = baseHp;

		for (int i = 0; i < arcadeInitialAttackers; ++i)
		{
			const int p1Id = 1000 + i;
			const int p2Id = 6000 + i;
			units[p1Id] = UnitPosition{p1Id, 700.0f, 4700.0f - i * 100.0f};
			units[p2Id] = UnitPosition{p2Id, 4400.0f, 300.0f + i * 100.0f};
			entityCurrentHp[p1Id] = attackerHp;
			entityCurrentHp[p2Id] = attackerHp;
			entityMaxHp[p1Id] = attackerHp;
			entityMaxHp[p2Id] = attackerHp;
		}

		// Shop in the center
		shops[11000] = ShopUnit{11000, 2500.0f, 2500.0f, 120.0f};

		// Obstacles (maze)
		{
			std::unordered_set<games_types::CellCoord, CellCoordHash> reservedCells;
			buildReservedCells(structures, resources, units, shops, reservedCells);

			std::vector<std::vector<std::uint8_t>> openGrid;
			std::vector<games_types::CellCoord> obstacleCells;
			const games_types::CellCoord base1Cell = worldToGridCell(structures.at(0).x, structures.at(0).y);
			const games_types::CellCoord base2Cell = worldToGridCell(structures.at(5000).x, structures.at(5000).y);

			for (int attempt = 0; attempt < kMazeAttemptLimit; ++attempt)
			{
				generateObstacleField(static_cast<unsigned int>(sessionId + attempt + 1), openGrid);
				obstacleCells = buildObstacleCells(openGrid, reservedCells);

				if (hasTraversablePath(openGrid, reservedCells, base1Cell, base2Cell))
				{
					break;
				}

				obstacleCells.clear();
			}

			games_types::StaticObstacle obstacleLine{};
			obstacleLine.id = 12000;
			obstacleLine.cells = std::move(obstacleCells);
			staticObstacles[obstacleLine.id] = obstacleLine;
		}

        nextP1BombId = games_types::id_ranges::p1Bombs.minId;
        nextP2BombId = games_types::id_ranges::p2Bombs.minId;
        unitGoldCostByType[games_types::EntityType::Bomb] = arcadeBombCost;
        bombs.clear();

        // Next attacker IDs
        nextP1AttackerId = 1000 + arcadeInitialAttackers;
        nextP2AttackerId = 6000 + arcadeInitialAttackers;

        lastAutoSpawnTime = std::chrono::steady_clock::now();

        return;
	}

	//bases de los jugadores
	structures[0] = UnitPosition{0, 300.0f, 4700.0f};
	structures[5000] = UnitPosition{5000, 4700.0f, 300.0f};
	entityCurrentHp[0] = baseHp;
	entityCurrentHp[5000] = baseHp;
	entityMaxHp[0] = baseHp;
	entityMaxHp[5000] = baseHp;

	//tres recolectores por cada jugador en estado idle
	collectors.clear();
	collectors[3000] = CollectorUnit{3000, player1, games_types::CollectorState::Idle, 600.0f, 4600.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	collectors[3001] = CollectorUnit{3001, player1, games_types::CollectorState::Idle, 600.0f, 4700.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	collectors[3002] = CollectorUnit{3002, player1, games_types::CollectorState::Idle, 600.0f, 4800.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	
	collectors[8000] = CollectorUnit{8000, player2, games_types::CollectorState::Idle, 4500.0f, 200.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	collectors[8001] = CollectorUnit{8001, player2, games_types::CollectorState::Idle, 4500.0f, 300.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	collectors[8002] = CollectorUnit{8002, player2, games_types::CollectorState::Idle, 4500.0f, 400.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	
	entityCurrentHp[3000] = collectorHp;
	entityCurrentHp[3001] = collectorHp;
	entityCurrentHp[3001] = collectorHp;
	
	entityCurrentHp[8000] = collectorHp;
	entityCurrentHp[8001] = collectorHp;
	entityCurrentHp[8002] = collectorHp;
	
	entityMaxHp[3000] = collectorHp;
	entityMaxHp[3001] = collectorHp;
	entityMaxHp[3002] = collectorHp;
	
	entityMaxHp[8000] = collectorHp;
	entityMaxHp[8001] = collectorHp;
	entityMaxHp[8002] = collectorHp;

	//3 minas en el mapa
	resources.clear();
	resources[10000] = ResourceNode{10000, games_types::ResourceType::Gold, 3500.0f, 3500.0f, 60.0f, 4000, 25};
	resources[10001] = ResourceNode{10001, games_types::ResourceType::Gold, 2100.0f, 2900.0f, 60.0f, 4000, 25};
	resources[10002] = ResourceNode{10002, games_types::ResourceType::Gold, 2900.0f, 2100.0f, 60.0f, 4000, 25};
	resources[10003] = ResourceNode{10003, games_types::ResourceType::Gold, 1500.0f, 1500.0f, 60.0f, 4000, 25};

	//atacantes jugador 1
	units[1000] = UnitPosition{1000, 700.0f, 4700.0f};
	entityCurrentHp[1000] = attackerHp;
	entityMaxHp[1000] = attackerHp;
	//recolectores inicial jugador 1
	units[3000] = UnitPosition{3000, 600.0f, 4600.0f};
	units[3001] = UnitPosition{3001, 600.0f, 4700.0f};
	units[3002] = UnitPosition{3002, 600.0f, 4800.0f};
	
	//atacantes jugador 2
	units[6000] = UnitPosition{6000, 4400.0f, 300.0f};
	entityCurrentHp[6000] = attackerHp;
	entityMaxHp[6000] = attackerHp;

	//recolector inicial jugador 2
	units[8000] = UnitPosition{8000, 4500.0f, 200.0f};
	units[8001] = UnitPosition{8001, 4500.0f, 300.0f};
	units[8002] = UnitPosition{8002, 4500.0f, 400.0f};

	//por ahora una unica tienda estatica en el mapa
	shops[11000] = ShopUnit{11000, 2500.0f, 2500.0f, 120.0f};

	std::unordered_set<games_types::CellCoord, CellCoordHash> reservedCells;
	buildReservedCells(structures, resources, units, shops, reservedCells);

	std::vector<std::vector<std::uint8_t>> openGrid;
	std::vector<games_types::CellCoord> obstacleCells;
	const games_types::CellCoord base1Cell = worldToGridCell(structures.at(0).x, structures.at(0).y);
	const games_types::CellCoord base2Cell = worldToGridCell(structures.at(5000).x, structures.at(5000).y);

	for (int attempt = 0; attempt < kMazeAttemptLimit; ++attempt)
	{
		generateObstacleField(static_cast<unsigned int>(sessionId + attempt + 1), openGrid);
		obstacleCells = buildObstacleCells(openGrid, reservedCells);

		if (hasTraversablePath(openGrid, reservedCells, base1Cell, base2Cell))
		{
			break;
		}

		obstacleCells.clear();
	}

	staticObstacles.clear();
	games_types::StaticObstacle obstacleLine{};
	obstacleLine.id = 12000;
	obstacleLine.cells = std::move(obstacleCells);
	staticObstacles[obstacleLine.id] = obstacleLine;

	// para saber que id asignar a las tropas que compren
	nextP1AttackerId = 1003;
	nextP1CollectorId = 3001;
	nextP2AttackerId = 6003;
	nextP2CollectorId = 8001;
}


