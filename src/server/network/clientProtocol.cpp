#include <string>
#include <vector>
#include <utility>
#include <iostream>

#include "third_party/json.hpp"
#include "clientProtocol.h"

using json = nlohmann::json;

/// @brief ESTE ARCHIVO ES PARA FRAMEAR LOS MENSAJES JSON DE IDA Y VUELTA

std::string client_protocol::BuildErrorResponse(const std::string &reason)
{
    json response = {
        {"type", "CONNECTION_ACK"},
        {"status", "rejected"},
        {"reason", reason}
    };
    return response.dump() +"\n"; 
}

std::string client_protocol::BuildOkResponse()
{
    json response = {
        {"type", "CONNECTION_ACK"},
        {"status","accepted"}
    };
    return response.dump() + "\n";

}
std::string client_protocol::BuildQueueStatusResponse(
    int playersWaiting, 
    const std::string& playerId)
{
    json response = {
        {"type", "QUEUE_STATUS"},
        {"payload",{
            {"players_waiting", playersWaiting},
            {"you", playerId}
        }}
    };
    //std::cout <<response << '\n';
    return response.dump() +'\n';
}

std::string client_protocol::BuildMatchFoundResponse(
    const std::string& sessionId,
    const std::string& you,
    const std::string& opponent)
{
    json response = {
        {"type", "MATCH_FOUND"},
        {"payload", {
            {"session_id", sessionId}, 
            {"you", you}, 
            {"opponent", opponent}}}};
    return response.dump() + "\n";
}

std::string client_protocol::BuildMatchStartResponse(const std::string& sessionId)
{
    json response = {
        {"type", "MATCH_START"},
        {"payload", {
            {"session_id",sessionId}
        }}
    };
    return response.dump() + '\n';
}

//framing del buffer por delimitador "\n"
//Recibe bytes crudos de recv, acumula en el carrybuffer y extrae los mensajes completos en outMessages.

bool client_protocol::MessageFramer(
    std::string&              carryBuffer, 
    const char*               chunk, 
    size_t                    chunkSize, 
    std::vector<std::string>& outMessages)
{
    constexpr size_t kMaxFrameSize = 16 * 1024; //16kB por mensaje

    if(chunk!=nullptr && chunkSize > 0)
    {
        carryBuffer.append(chunk,chunkSize);

    };
    //condicion para evitar el crecimiento descontrolado
    if (carryBuffer.size() > kMaxFrameSize * 4)
    {
        carryBuffer.clear();
        return false;
    };
    
    size_t pos= 0;
    while((pos = carryBuffer.find('\n'))  != std::string::npos)
    {
        std::string message = carryBuffer.substr(0,pos);
        carryBuffer.erase(0, pos + 1);

        //para manejar CRLF desde el cliente
        if ( !message.empty() && message.back() == '\r')
        {
            message.pop_back();
        }
        if ( message.empty())
        {
            continue;
        }
        if( message.size() > kMaxFrameSize)
        {
            return false;
        }
        outMessages.push_back(std::move(message));
    }

    return true;
}


//validar y procesar el mensaje Json
//Devolver true si es un initialConnect valido
//siempre llena responseToSend(aceptando/rechazando)

bool client_protocol::MessageProtocol(
    const std::string &rawMessage,
    ParsedMessage &outMessage,
    std::string &responseToSend)
{
    outMessage = ParsedMessage{};
    responseToSend.clear();

    const json data = json::parse(rawMessage, nullptr, false);
    if (data.is_discarded())
    {
        responseToSend = BuildErrorResponse("invalid_json");
        return false;
    }

    if (!data.contains("type") || !data["type"].is_string())
    {
        responseToSend = BuildErrorResponse("missing_or_invalid_type");
        return false;
    }

    const std::string type = data["type"].get<std::string>();

    if (type == "INITIAL_CONNECT")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {   
            std::cout << "llego el json bien\n";
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json &payload = data["payload"];

        if (!payload.contains("player_id") || !payload["player_id"].is_string())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_player_id");
            return false;
        }
        if (!payload.contains("client_version") || !payload["client_version"].is_string())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_client_version");
            return false;
        }
        if (!payload.contains("is_ready") || !payload["is_ready"].is_boolean())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_is_ready");
            return false;
        }

        outMessage.type = ParsedMessageType::InitialConnect;
        outMessage.initialConnect.playerId = payload["player_id"].get<std::string>();
        outMessage.initialConnect.clientVersion = payload["client_version"].get<std::string>();
        outMessage.initialConnect.isReady = payload["is_ready"].get<bool>();
        
        responseToSend = BuildOkResponse();
        return true;
    }

    if (type == "PLAYER_READY")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json &payload = data["payload"];
        if (!payload.contains("session_id") || !payload["session_id"].is_string())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_session_id");
            return false;
        }

        outMessage.type = ParsedMessageType::PlayerReady;
        outMessage.playerReady.sessionId = payload["session_id"].get<std::string>();
        return true;
    }

    responseToSend = BuildErrorResponse("unsupported_message_type");
    return false;
}
