#pragma once

#include <memory>
#include <mutex>
#include <queue>

#include "GameTypes.h"

class GameSession;
class PathFinder;

class GameEngine
{
	public:
		explicit GameEngine(std::shared_ptr<GameSession> session,
							std::shared_ptr<PathFinder> pathFinder = nullptr);
		~GameEngine() = default;

		void tcpCommandEnqueue(const games_types::PlayerCommand& cmd);
		void commandQueueProcess();

	private:
		bool propertyValidation(int playerId, int unitId) const;
		void setNewRoute(const games_types::PlayerCommand& cmd);

		std::shared_ptr<GameSession> session;
		std::shared_ptr<PathFinder> pathFinder;
		std::queue<games_types::PlayerCommand> commandQueue;
		mutable std::mutex mtxCommands;
};
