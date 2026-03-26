#include <string>
#include <vector>

namespace client_protocol
{
    struct InitialConnectData
    {
        std::string playerId;
        std::string clientVersion;
        bool isReady = false;
    };
    
    std::string BuildErrorResponse(const std::string& reason);

    std::string BuildOkResponse();

    bool MessageFramer(
    std::string&              carryBuffer, 
    const char*               chunk, 
    size_t                    chunkSize, 
    std::vector<std::string>& outMessages);
    
    bool MessageProtocol(
    const std::string&  rawMessage,
    InitialConnectData& outData,
    std::string&        responseToSend);
}