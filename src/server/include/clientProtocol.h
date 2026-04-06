#include <string>
#include <vector>
#include <memory>

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
    enum class ParsedMessageType
    {
        InitialConnect,
        PlayerReady,
        MoveUnit,
        Unsuported
    };
    
    struct ParsedMessage
    {
        ParsedMessageType type = ParsedMessageType::Unsuported;
        InitialConnectData initialConnect;
        PlayerReadyData playerReady;
        MoveUnitData moveUnit;
    };
    
    std::string BuildErrorResponse(const std::string& reason);
    std::string BuildOkResponse();

    std::string BuildQueueStatusResponse(int playerWaiting, const std::string& playerId);
    std::string BuildMatchFoundResponse(
        const std::string& sessionId,
        const std::string& you,
        const std::string& opponent);
    
    std::string BuildMatchStartResponse(const std::string& sessionId, std::shared_ptr<GameSession> session);
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