#include "GameSession.h"

#include <filesystem>
#include <fstream>
#include <limits>

#include "third_party/json.hpp"

using json = nlohmann::json;

namespace
{
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
}

GameSession::GameSession(int player1, int player2, int sessionId)
	: player1(player1), player2(player2), sessionId(sessionId)
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
		recentlyDestroyedUnitIds.insert(entityId);
		if (!games_types::id_ranges::p1Structures.contains(entityId) &&
			!games_types::id_ranges::p2Structures.contains(entityId))
		{
			entityCurrentHp.erase(entityId);
			entityMaxHp.erase(entityId);
		}

		if (games_types::id_ranges::p1Structures.contains(entityId) ||
			games_types::id_ranges::p2Structures.contains(entityId))
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

void GameSession::initializeGameState()
{
	std::lock_guard<std::mutex> lock(sessionMutex);
	loadCombatConfigNoLock();

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

	//bases de los jugadores
	structures[0] = UnitPosition{0, 300.0f, 4700.0f};
	structures[5000] = UnitPosition{5000, 4700.0f, 300.0f};
	entityCurrentHp[0] = baseHp;
	entityCurrentHp[5000] = baseHp;
	entityMaxHp[0] = baseHp;
	entityMaxHp[5000] = baseHp;

	//un recolector por cada jugador en estado idle
	collectors.clear();
	collectors[3000] = CollectorUnit{3000, player1, games_types::CollectorState::Idle, 500.0f, 4550.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	collectors[8000] = CollectorUnit{8000, player2, games_types::CollectorState::Idle, 4575.0f, 375.0f, -1, 0, 200, 1000, 500, 0, collectorHp, collectorHp};
	entityCurrentHp[3000] = collectorHp;
	entityCurrentHp[8000] = collectorHp;
	entityMaxHp[3000] = collectorHp;
	entityMaxHp[8000] = collectorHp;

	//3 minas en el mapa
	resources.clear();
	resources[10000] = ResourceNode{10000, games_types::ResourceType::Gold, 3500.0f, 3500.0f, 60.0f, 4000, 25};
	resources[10001] = ResourceNode{10001, games_types::ResourceType::Gold, 2100.0f, 2900.0f, 60.0f, 4000, 25};
	resources[10002] = ResourceNode{10002, games_types::ResourceType::Gold, 2900.0f, 2100.0f, 60.0f, 4000, 25};
	resources[10003] = ResourceNode{10003, games_types::ResourceType::Gold, 1500.0f, 1500.0f, 60.0f, 4000, 25};

	//atacantes jugador 1
	units[1000] = UnitPosition{1000, 400.0f, 4600.0f};
	units[1001] = UnitPosition{1001, 500.0f, 4500.0f};
	units[1002] = UnitPosition{1002, 600.0f, 4400.0f};
	entityCurrentHp[1000] = attackerHp;
	entityCurrentHp[1001] = attackerHp;
	entityCurrentHp[1002] = attackerHp;
	entityMaxHp[1000] = attackerHp;
	entityMaxHp[1001] = attackerHp;
	entityMaxHp[1002] = attackerHp;
	//recolector inicial jugador 1
	units[3000] = UnitPosition{3000, 380.0f, 4550.0f};
	
	//atacantes jugador 2
	units[6000] = UnitPosition{6000, 4600.0f, 400.0f};
	units[6001] = UnitPosition{6001, 4500.0f, 500.0f};
	units[6002] = UnitPosition{6002, 4400.0f, 600.0f};
	entityCurrentHp[6000] = attackerHp;
	entityCurrentHp[6001] = attackerHp;
	entityCurrentHp[6002] = attackerHp;
	entityMaxHp[6000] = attackerHp;
	entityMaxHp[6001] = attackerHp;
	entityMaxHp[6002] = attackerHp;
	
	//recolector inicial jugador 2
	units[8000] = UnitPosition{8000, 4575.0f, 375.0f};

	//por ahora una unica tienda estatica en el mapa
	shops[11000] = ShopUnit{11000, 2500.0f, 2500.0f, 120.0f};

	// obstaculo inicial para pruebas de A*: linea horizontal de 25 celdas
	staticObstacles.clear();
	games_types::StaticObstacle obstacleLine{};
	obstacleLine.id = 12000;
	for (int x = 40; x <= 64; ++x)
	{
		obstacleLine.cells.push_back(games_types::CellCoord{x, 25});
	}
	staticObstacles[obstacleLine.id] = obstacleLine;
	
	// para saber que id asignar a las tropas que compren
	nextP1AttackerId = 1003;
	nextP1CollectorId = 3001;
	nextP2AttackerId = 6003;
	nextP2CollectorId = 8001;
}


