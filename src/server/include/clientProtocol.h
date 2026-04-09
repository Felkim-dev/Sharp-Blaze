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
    };

    struct PlayerReadyData
    {
        std::string sessionId;
    };
    struct MoveUnitData
    {
        int unitId = 0;
        float destX = 0.0f;
        float destY = 0.0f;
    };

    struct BuyUnitData
    {
        games_types::EntityType unitType = games_types::EntityType::Unknown;
        int quantity = 1;
    };

    struct DepositResourceData
    {
        int collectorId = 0;
        games_types::ResourceType resourceType = games_types::ResourceType::Gold;
        int amount = 0;
    };

    enum class ParsedMessageType
    {
        InitialConnect,
        PlayerReady,
        MoveUnit,
        BuyUnit,
        DepositResource,
        Unsuported
    };
    
    struct ParsedMessage
    {
        ParsedMessageType type = ParsedMessageType::Unsuported;
        InitialConnectData initialConnect;
        PlayerReadyData playerReady;
        MoveUnitData moveUnit;
        BuyUnitData buyUnit;
        DepositResourceData deposit;
    };
    
    std::string BuildErrorResponse(const std::string& reason);
    std::string BuildOkResponse();

    std::string BuildQueueStatusResponse(int playerWaiting, const std::string& playerId);
    std::string BuildMatchFoundResponse(
        const std::string& sessionId,
        const std::string& you,
        const std::string& opponent);
    // std::string BuildEconomyResponse(const int playerId,
    //     const std::string& sessionId,
    //      )
    
    std::string BuildMatchStartResponse(const std::string& sessionId, std::shared_ptr<GameSession> session);
    std::string BuildShopAuthorizationResponse(int playerId, const games_types::ShopAuthorizationState& state);
    std::string BuildResourcesResponse(int newBalance);
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