#pragma once

#include <memory>
#include <mutex>
#include <deque>
#include <queue>
#include <string>
#include <unordered_map>
#include <vector>

#include "GameTypes.h"

class GameSession;
class PathFinder;

class GameEngine
{
	public:
		struct AttackRequestResult
		{
			int playerId = 0;
			int attackerId = 0;
			int targetId = 0;
			bool accepted = false;
			std::string reason;
			int targetCurrentHp = -1;
			int impactDelayMs = 0;
		};

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
		void advanceMovement(int deltaMs);
		void advanceCollectors(int deltaMs);
		void advanceCombat(int deltaMs);
		std::vector<games_types::EconomyTransaction> drainEconomyTransactions();
		std::vector<games_types::CombatEvent> drainCombatEvents();
		std::vector<AttackRequestResult> drainAttackResults();
		bool reconcileShopAuthorization(int playerId, games_types::ShopAuthorizationState& outState);
		bool hasShopAuthorization(int playerId) const;
		PurchaseResult processUnitPurchase(int playerId, games_types::EntityType unitType, int quantity);
		std::shared_ptr<GameSession> getSession() const { return session; }

	private:
		struct FormationAssignment
		{
			games_types::CellCoord groupTarget{};
			games_types::CellCoord slotTarget{};
			int groupSize = 0;
			int slotIndex = -1;
			std::uint64_t epoch = 0;
		};

		bool propertyValidation(int playerId, int unitId) const;
		void setNewRoute(const games_types::PlayerCommand& cmd);
		void setNewRouteToCell(const games_types::PlayerCommand& cmd, const games_types::CellCoord& destinationCell);
		void repathUnit(int unitId, const games_types::CellCoord& destinationCell);
		void processMoveCommandsWithFormation(const std::vector<games_types::PlayerCommand>& moveCommands);
		void processAttackCommand(const games_types::PlayerCommand& cmd);
			AttackRequestResult executeAttackAttempt(int playerId, int attackerId, int targetId, bool applyDamage = true);
		bool shouldKeepAttackLock(const AttackRequestResult& result) const;

		std::shared_ptr<GameSession> session;
		std::shared_ptr<PathFinder> pathFinder;
		std::queue<games_types::PlayerCommand> commandQueue;
		std::unordered_map<int, std::deque<games_types::CellCoord>> movementRoutes;
		std::unordered_map<int, int> attackLockTargetByAttacker;
			std::unordered_map<int, int> attackImpactRemainingMs;
		std::unordered_map<int, FormationAssignment> formationByUnit;
		std::uint64_t formationEpoch = 0;
		std::unordered_map<int, int> attackerCooldownRemainingMs;
		std::unordered_map<int, int> movementCooldownRemainingMs;
		std::vector<games_types::CombatEvent> pendingCombatEvents;
		std::vector<AttackRequestResult> pendingAttackResults;
		mutable std::mutex mtxCommands;
		mutable std::mutex mtxCombatEvents;
		mutable std::mutex mtxAttackResults;
};
