#include "GameSession.h"

#include <limits>

GameSession::GameSession(int player1, int player2, std::string sessionId)
	: player1(player1), player2(player2), sessionId(sessionId)
{
	initializeGameState();
}

std::string GameSession::getSessionId() const
{
	return sessionId;
}

bool GameSession::hasPlayer(int playerId) const
{
	return playerId == player1 || playerId == player2;
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
	else
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
		snapshot.push_back(entry.second);
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

void GameSession::initializeGameState()
{
	std::lock_guard<std::mutex> lock(sessionMutex);

	unitGoldCostByType.clear();
	unitGoldCostByType[games_types::EntityType::Attacker] = 200;
	unitGoldCostByType[games_types::EntityType::Collector] = 100;

	playerGold[player1] = kInitialGold;
	playerGold[player2] = kInitialGold;
	playerGoldSpent[player1] = 0;
	playerGoldSpent[player2] = 0;

	structures[0] = UnitPosition{0, 300.0f, 4700.0f};
	structures[5000] = UnitPosition{5000, 4700.0f, 300.0f};

	collectors.clear();
	collectors[3000] = CollectorUnit{3000, player1, games_types::CollectorState::Idle, 380.0f, 4550.0f, -1, 0, 200, 1000, 500, 0};
	collectors[8000] = CollectorUnit{8000, player2, games_types::CollectorState::Idle, 4620.0f, 450.0f, -1, 0, 200, 1000, 500, 0};

	resources.clear();
	resources[10000] = ResourceNode{10000, games_types::ResourceType::Gold, 2500.0f, 2500.0f, 60.0f, 4000, 25};
	resources[10001] = ResourceNode{10001, games_types::ResourceType::Gold, 2100.0f, 2900.0f, 60.0f, 4000, 25};
	resources[10002] = ResourceNode{10002, games_types::ResourceType::Gold, 2900.0f, 2100.0f, 60.0f, 4000, 25};

	units[1000] = UnitPosition{1000, 400.0f, 4600.0f};
	units[1001] = UnitPosition{1001, 500.0f, 4500.0f};
	units[1002] = UnitPosition{1002, 600.0f, 4400.0f};
	units[3000] = UnitPosition{3000, 380.0f, 4550.0f};
	
	units[6000] = UnitPosition{6000, 4600.0f, 400.0f};
	units[6001] = UnitPosition{6001, 4500.0f, 500.0f};
	units[6002] = UnitPosition{6002, 4400.0f, 600.0f};
	units[8000] = UnitPosition{8000, 4620.0f, 450.0f};

	nextP1AttackerId = 1003;
	nextP1CollectorId = 3001;
	nextP2AttackerId = 6003;
	nextP2CollectorId = 8001;
}


