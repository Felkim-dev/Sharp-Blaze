#include <string>
#include <vector>
#include <utility>
#include <iostream>
#include <memory>

#include "third_party/json.hpp"
#include "clientProtocol.h"
#include "GameSession.h"

using json = nlohmann::json;

namespace
{
    bool isPurchasableTroopType(games_types::EntityType type)
    {
        return type == games_types::EntityType::Collector ||
               type == games_types::EntityType::Attacker;
    }

    bool parseEntityType(const json& value, games_types::EntityType& outType)
    {
        if (value.is_number_integer())
        {
            const int raw = value.get<int>();
            if (raw >= static_cast<int>(games_types::EntityType::Structure) &&
                raw <= static_cast<int>(games_types::EntityType::Unknown))
            {
                outType = static_cast<games_types::EntityType>(raw);
                return true;
            }
            return false;
        }

        if (!value.is_string())
        {
            return false;
        }

        const std::string typeName = value.get<std::string>();
        if (typeName == "Structure")
        {
            outType = games_types::EntityType::Structure;
            return true;
        }
        if (typeName == "Attacker")
        {
            outType = games_types::EntityType::Attacker;
            return true;
        }
        if (typeName == "Collector")
        {
            outType = games_types::EntityType::Collector;
            return true;
        }
        if (typeName == "ResourceMine")
        {
            outType = games_types::EntityType::ResourceMine;
            return true;
        }
        if (typeName == "Shop")
        {
            outType = games_types::EntityType::Shop;
            return true;
        }

        return false;
    }

    bool parseResourceType(const json& value, games_types::ResourceType& outType)
    {
        if (value.is_number_integer())
        {
            const int raw = value.get<int>();
            if (raw >= static_cast<int>(games_types::ResourceType::Gold) &&
                raw <= static_cast<int>(games_types::ResourceType::Unknown))
            {
                outType = static_cast<games_types::ResourceType>(raw);
                return true;
            }
            return false;
        }

        if (!value.is_string())
        {
            return false;
        }

        const std::string typeName = value.get<std::string>();
        if (typeName == "Gold")
        {
            outType = games_types::ResourceType::Gold;
            return true;
        }

        return false;
    }
}

/// @brief ESTE ARCHIVO ES PARA FRAMEAR LOS MENSAJES JSON DE IDA Y VUELTA

std::string client_protocol::BuildErrorResponse(const std::string &reason)
{
    json response = {
        {"type", "CONNECTION_ACK"},
        {"status", "rejected"},
        {"reason", reason}
    };
    std::cout << "error en el msj\n";
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

std::string client_protocol::BuildMatchStartResponse(const std::string& sessionId, std::shared_ptr<GameSession> session)
{
    json structures = json::object();
    json units = json::object();

    if (session)
    {
        auto structuresSnapshot = session->getStructuresSnapshot();
        for (const auto& structure : structuresSnapshot)
        {
            structures[std::to_string(structure.entity_id)] = json::array({structure.x, structure.y});
        }

        auto unitsSnapshot = session->getUnitsSnapshot();
        for (const auto& unit : unitsSnapshot)
        {
            units[std::to_string(unit.entity_id)] = json::array({unit.x, unit.y});
        }
    }

    json response = {
        {"type", "START_GAME"},
        {"payload", {
            {"session_id", sessionId},
            {"start", true},
            {"structures", structures},
            {"units", units}
        }}
    };
    return response.dump() + '\n';
}

std::string client_protocol::BuildShopAuthorizationResponse(
    int playerId,
    const games_types::ShopAuthorizationState& state)
{
    json response = {
        {"type", "SHOP_AUTHORIZATION"},
        {"payload", {
            {"player_id", playerId},
            {"authorized", state.authorized},
            {"shop_id", state.authorized ? state.shopId : -1},
            {"unit_id", state.authorized ? state.unitId : -1}
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

    if (type == "START_GAME")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json& payload = data["payload"];
        if (!payload.contains("start") || !payload["start"].is_boolean  ())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_start");
            return false;
        }

        // El cliente usa start=false para solicitar el inicio de partida.
        if (payload["start"].get<bool>() != false)
        {
            responseToSend = BuildErrorResponse("invalid_start_value");
            return false;
        }

        outMessage.type = ParsedMessageType::PlayerReady;
        if (payload.contains("session_id") && payload["session_id"].is_string())
        {
            outMessage.playerReady.sessionId = payload["session_id"].get<std::string>();
        }
        else
        {
            outMessage.playerReady.sessionId.clear();
        }
        return true;
    }

    if (type == "MOVE_ORDER")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json& payload = data["payload"];
        if (!payload.contains("unit_id") || !payload["unit_id"].is_number_integer())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_unit_id");
            return false;
        }
        if (!payload.contains("target_x") || !payload["target_x"].is_number())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_target_x");
            return false;
        }
        if (!payload.contains("target_y") || !payload["target_y"].is_number())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_target_y");
            return false;
        }

        outMessage.type = ParsedMessageType::MoveUnit;
        outMessage.moveUnit.unitId = payload["unit_id"].get<int>();
        outMessage.moveUnit.destX = payload["target_x"].get<float>();
        outMessage.moveUnit.destY = payload["target_y"].get<float>();
        responseToSend = BuildOkResponse();
        std::cout << outMessage.moveUnit.unitId << "," << outMessage.moveUnit.destX << "," << outMessage.moveUnit.destY<< '\n';
        return true;
    }

    if (type == "BUY_UNIT")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json& payload = data["payload"];
        if (!payload.contains("unit_type"))
        {
            responseToSend = BuildErrorResponse("missing_unit_type");
            return false;
        }

        games_types::EntityType unitType = games_types::EntityType::Unknown;
        if (!parseEntityType(payload["unit_type"], unitType) ||
            unitType == games_types::EntityType::Unknown)
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_unit_type");
            return false;
        }

        if (!isPurchasableTroopType(unitType))
        {
            responseToSend = BuildErrorResponse("unit_type_not_purchasable");
            return false;
        }

        int quantity = 1;
        if (payload.contains("quantity"))
        {
            if (!payload["quantity"].is_number_integer())
            {
                responseToSend = BuildErrorResponse("missing_or_invalid_quantity");
                return false;
            }
            quantity = payload["quantity"].get<int>();
        }

        if (quantity <= 0)
        {
            responseToSend = BuildErrorResponse("invalid_quantity_value");
            return false;
        }

        outMessage.type = ParsedMessageType::BuyUnit;
        outMessage.buyUnit.unitType = unitType;
        outMessage.buyUnit.quantity = quantity;
        responseToSend = BuildOkResponse();
        return true;
    }

    if (type == "DEPOSIT_RESOURCE")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json& payload = data["payload"];
        if (!payload.contains("collector_id") || !payload["collector_id"].is_number_integer())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_collector_id");
            return false;
        }
        if (!payload.contains("resource_type"))
        {
            responseToSend = BuildErrorResponse("missing_resource_type");
            return false;
        }
        if (!payload.contains("amount") || !payload["amount"].is_number_integer())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_amount");
            return false;
        }

        games_types::ResourceType resourceType = games_types::ResourceType::Unknown;
        if (!parseResourceType(payload["resource_type"], resourceType) ||
            resourceType == games_types::ResourceType::Unknown)
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_resource_type");
            return false;
        }

        const int amount = payload["amount"].get<int>();
        if (amount <= 0)
        {
            responseToSend = BuildErrorResponse("invalid_amount_value");
            return false;
        }

        outMessage.type = ParsedMessageType::DepositResource;
        outMessage.deposit.collectorId = payload["collector_id"].get<int>();
        outMessage.deposit.resourceType = resourceType;
        outMessage.deposit.amount = amount;
        responseToSend = BuildOkResponse();
        return true;
    }

    responseToSend = BuildErrorResponse("unsupported_message_type");
    return false;
}
