#include "GameSession.h"

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

void GameSession::initializeGameState()
{
	std::lock_guard<std::mutex> lock(sessionMutex);

	structures[100] = UnitPosition{100, 300.0f, 4700.0f};
	structures[101] = UnitPosition{101, 4700.0f, 300.0f};
    structures[102] = UnitPosition{102, 2500.0f, 2500.0f};

    units[1] = UnitPosition{1, 400.0f, 4600.0f};
    units[2] = UnitPosition{2, 500.0f, 4500.0f};
	units[3] = UnitPosition{3, 600.0f, 4400.0f};
	
    units[4] = UnitPosition{4, 4600.0f, 400.0f};
    units[5] = UnitPosition{5, 4500.0f, 500.0f};
    units[6] = UnitPosition{6, 4400.0f, 600.0f};
}


