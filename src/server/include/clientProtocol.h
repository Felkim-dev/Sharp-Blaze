#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <memory>

#include "GameTypes.h"

class GameSession;

namespace client_protocol
{
    struct InitialConnectData
    {
        std::string playerId;
        std::string clientVersion;
        bool isReady = false;
        int sessionId = 0;
        std::string token;
        int internalPlayerId = 0;
    };

    struct PlayerReadyData
    {
        int sessionId;
    };
    struct MoveUnitData
    {
        int unitId = 0;
        games_types::CellCoord destination{};
    };

    struct BuyUnitData
    {
        games_types::EntityType unitType = games_types::EntityType::Unknown;
        int quantity = 1;
    };

    struct AttackData
    {
        int attackerId = 0;
        int targetId = 0;
    };

    struct DepositResourceData
    {
        int collectorId = 0;
        games_types::ResourceType resourceType = games_types::ResourceType::Gold;
        int amount = 0;
    };

    struct PauseGameData
    {
        bool paused = false;
        int pausedByPlayerId = -1;
    };

    struct SurrenderData
    {
        int surrenderingPlayerId = -1;
    };

    enum class ParsedMessageType
    {
        InitialConnect,
        PlayerReady,
        MoveUnit,
        Attack,
        BuyUnit,
        DepositResource,
        PauseGame,
        Surrender,
        Unsuported
    };
    
    struct ParsedMessage
    {
        ParsedMessageType type = ParsedMessageType::Unsuported;
        InitialConnectData initialConnect;
        PlayerReadyData playerReady;
        MoveUnitData moveUnit;
        AttackData attack;
        BuyUnitData buyUnit;
        DepositResourceData deposit;
        PauseGameData pauseGame;
        SurrenderData surrender;
    };
    
    std::string BuildErrorResponse(const std::string& reason);
    std::string BuildOkResponse();

    std::string BuildQueueStatusResponse(int playerWaiting, const std::string& playerId);
    std::string BuildMatchFoundResponse(
        const int& sessionId,
        const int& playerId,
        const std::string& you,
        const std::string& opponent);
    // std::string BuildEconomyResponse(const int playerId,
    //     const std::string& sessionId,
    //      )
    
    std::string BuildMatchStartResponse(
        const int& sessionId,
        int playerId,
        std::uint16_t udpPort,
        std::shared_ptr<GameSession> session);
    std::string BuildShopAuthorizationResponse(int playerId, const games_types::ShopAuthorizationState& state);
    std::string BuildResourcesResponse(int newBalance);
    std::string BuildAttackResultResponse(
        int attackerId,
        int targetId,
        bool accepted,
        const std::string& reason,
        int currentHp = -1);
    std::string BuildUnitDamagedResponse(
        int sessionId,
        int targetPlayerId,
        int targetEntityId,
        int attackerPlayerId,
        int attackerEntityId,
        int currentHp,
        int maxHp = 0);
    std::string BuildEntityDestroyedResponse(
        int sessionId,
        int entityId,
        int ownerPlayerId,
        int attackerPlayerId);
    std::string BuildGameOverResponse(int sessionId, int playerId);
    std::string BuildPauseBroadcast(int pausedByPlayerId);
    std::string BuildGameOverWithReasonResponse(
        const std::string& sessionId, int winnerPlayerId, const std::string& reason);
    bool MessageFramer(
    std::string&              carryBuffer, 
    const char*               chunk, 
    size_t                    chunkSize, 
    std::vector<std::string>& outMessages);
    
    bool MessageProtocol(
    const std::string&  rawMessage,
    ParsedMessage& outMessage,
    std::string& responseToSend);
}