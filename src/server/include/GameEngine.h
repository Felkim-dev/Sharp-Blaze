#pragma once

#include <memory>
#include <mutex>
#include <queue>
#include <string>

#include "GameTypes.h"

class GameSession;
class PathFinder;

class GameEngine
{
	public:
		struct PurchaseResult
		{
			bool success = false;
			std::string reason;
			int unitId = -1;
			games_types::EntityType unitType = games_types::EntityType::Unknown;
			float spawnX = 0.0f;
			float spawnY = 0.0f;
			int newBalance = 0;
		};

		explicit GameEngine(std::shared_ptr<GameSession> session,
							std::shared_ptr<PathFinder> pathFinder = nullptr);
		~GameEngine() = default;

		void tcpCommandEnqueue(const games_types::PlayerCommand& cmd);
		void commandQueueProcess();
		void advanceCollectors(int deltaMs);
		bool reconcileShopAuthorization(int playerId, games_types::ShopAuthorizationState& outState);
		bool hasShopAuthorization(int playerId) const;
		PurchaseResult processUnitPurchase(int playerId, games_types::EntityType unitType, int quantity);

	private:
		bool propertyValidation(int playerId, int unitId) const;
		void setNewRoute(const games_types::PlayerCommand& cmd);

		std::shared_ptr<GameSession> session;
		std::shared_ptr<PathFinder> pathFinder;
		std::queue<games_types::PlayerCommand> commandQueue;
		mutable std::mutex mtxCommands;
};
