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
    bool isAttackerTroop(int entityId)
    {
        return games_types::id_ranges::p1Attackers.contains(entityId) ||
               games_types::id_ranges::p2Attackers.contains(entityId);
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
    std::cout << reason << std::endl;
    std::cout << "error en el msj" << std::endl;
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
    const int& sessionId,
    const int& playerId,
    const std::string& you,
    const std::string& opponent)
{
    json response = {
        {"type", "MATCH_FOUND"},
        {"payload", {
            {"session_id", sessionId},
            {"global_player_id",playerId}, 
            {"you", you}, 
            {"opponent", opponent}}}};
    return response.dump() + "\n";
}

std::string client_protocol::BuildMatchStartResponse(
    const int& sessionId,
    int playerId,
    std::uint16_t udpPort,
    std::shared_ptr<GameSession> session)
{
    constexpr float kCellSize = 50.0f;
    constexpr int kGridMaxIndex = 99;

    auto worldToGrid = [](float value) -> int {
        int cell = static_cast<int>(value / kCellSize);
        if (cell < 0)
        {
            return 0;
        }
        if (cell > kGridMaxIndex)
        {
            return kGridMaxIndex;
        }
        return cell;
    };

    json structures = json::object();
    json units = json::object();
    json obstacles = json::array();

    if (session)
    {
        auto structuresSnapshot = session->getStructuresSnapshot();
        for (const auto& structure : structuresSnapshot)
        {
            structures[std::to_string(structure.entity_id)] = json::array({
                worldToGrid(structure.x),
                worldToGrid(structure.y)
            });
        }

        auto unitsSnapshot = session->getUnitsSnapshot();
        for (const auto& unit : unitsSnapshot)
        {
            units[std::to_string(unit.entity_id)] = json::array({
                worldToGrid(unit.x),
                worldToGrid(unit.y)
            });
        }
        
        auto shopSnapShot = session->getShopsSnapshot();
        for (const auto& shop : shopSnapShot)
        {
            structures[std::to_string(shop.entityId)] = json::array({
                worldToGrid(shop.x),
                worldToGrid(shop.y)
            });
        }

        auto resourcesSnapShot = session->getResourcesSnapshot();
        for (const auto &resource : resourcesSnapShot)
        {
            structures[std::to_string(resource.entityId)] = json::array({
                worldToGrid(resource.x),
                worldToGrid(resource.y)
            });
        }

        auto obstaclesSnapshot = session->getStaticObstaclesSnapshot();
        for (const auto& obstacle : obstaclesSnapshot)
        {
            for (const auto& cell : obstacle.cells)
            {
                obstacles.push_back(json::array({cell.x, cell.y}));
            }
        }
    }

    json response = {
        {"type", "START_GAME"},
        {"payload", {
            {"session_id", sessionId},
            {"player_id", playerId},
            {"udp_port", udpPort},
            {"udp_protocol_version", 1},
            {"start", true},
            {"structures", structures},
            {"units", units},
            {"obstacles", obstacles},
            {"gold",500}
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

std::string client_protocol::BuildResourcesResponse(int newBalance)
{
    json response = {
        {"type", "RESOURCES"},
        {"payload", {
            {"new_balance", newBalance}
        }}
    };

    return response.dump() + '\n';
}

std::string client_protocol::BuildAttackResultResponse(
    int attackerId,
    int targetId,
    bool accepted,
    const std::string& reason,
    int currentHp)
{
    json payload = {
        {"attacker_id", attackerId},
        {"target_id", targetId},
        {"reason", reason}
    };

    if (currentHp >= 0)
    {
        payload["current_hp"] = currentHp;
    }

    json response = {
        {"type", "ATTACK_RESULT"},
        {"status", accepted ? "accepted" : "rejected"},
        {"payload", payload}
    };

    return response.dump() + '\n';
}

std::string client_protocol::BuildUnitDamagedResponse(
    int sessionId,
    int targetPlayerId,
    int targetEntityId,
    int attackerPlayerId,
    int attackerEntityId,
    int currentHp,
    int maxHp)
{
    (void)maxHp;

    json response = {
        {"type", "UNIT_DAMAGED"},
        {"payload", {
            {"session_id", sessionId},
            {"target_player_id", targetPlayerId},
            {"target_entity_id", targetEntityId},
            {"attacker_player_id", attackerPlayerId},
            {"attacker_entity_id", attackerEntityId},
            {"current_hp", currentHp},
        }}
    };

    return response.dump() + '\n';
}

std::string client_protocol::BuildEntityDestroyedResponse(
    int sessionId,
    int entityId,
    int ownerPlayerId,
    int attackerPlayerId)
{
    json response = {
        {"type", "ENTITY_DESTROYED"},
        {"payload", {
            {"session_id", sessionId},
            {"entity_id", entityId},
            {"owner_player_id", ownerPlayerId},
            {"attacker_player_id", attackerPlayerId}
        }}
    };

    return response.dump() + '\n';
}

std::string client_protocol::BuildGameOverResponse(int sessionId, int playerId)
{
    json response = {
        {"type", "GAME_OVER"},
        {"payload", {
            {"session_id", sessionId},
            {"winner_player_id", playerId},
            {"reason", "base_destroyed"}
        }}
    };

    return response.dump() + '\n';
}

std::string client_protocol::BuildPauseBroadcast(int pausedByPlayerId)
{
    json message;
    message["type"] = "GAME_PAUSED";
    message["payload"]["paused_by"] = pausedByPlayerId;
    return message.dump() + '\n';
}

std::string client_protocol::BuildGameOverWithReasonResponse(
    const std::string& sessionId, int winnerPlayerId, const std::string& reason)
{
    json message;
    message["type"] = "GAME_OVER";
    message["payload"]["session_id"] = sessionId;
    message["payload"]["winner_player_id"] = winnerPlayerId;
    message["payload"]["reason"] = reason;
    return message.dump() + '\n';
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
            std::cout << "llego el json bien" << std::endl;
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
        
        // Optional fields for dedicated sessions
        if (payload.contains("session_id") && payload["session_id"].is_number_integer())
        {
            outMessage.initialConnect.sessionId = payload["session_id"].get<int>();
        }
        if (payload.contains("match_token") && payload["match_token"].is_string())
        {
            outMessage.initialConnect.token = payload["match_token"].get<std::string>();
        }
        if (payload.contains("internal_player_id") && payload["internal_player_id"].is_number_integer())
        {
            outMessage.initialConnect.internalPlayerId = payload["internal_player_id"].get<int>();
        }
        
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
        outMessage.playerReady.sessionId = payload["session_id"].get<int>();
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
        if (payload.contains("session_id") && payload["session_id"].is_number_integer())
        {
            outMessage.playerReady.sessionId = payload["session_id"].get<int>();
        }
        else
        {
            outMessage.playerReady.sessionId = 0;
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
        if (!payload.contains("target_x") || !payload["target_x"].is_number_integer())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_target_x");
            return false;
        }
        if (!payload.contains("target_y") || !payload["target_y"].is_number_integer())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_target_y");
            return false;
        }

        const int targetX = payload["target_x"].get<int>();
        const int targetY = payload["target_y"].get<int>();
        if (targetX < 0 || targetX > 99)
        {
            responseToSend = BuildErrorResponse("target_x_out_of_range");
            return false;
        }
        if (targetY < 0 || targetY > 99)
        {
            responseToSend = BuildErrorResponse("target_y_out_of_range");
            return false;
        }

        outMessage.type = ParsedMessageType::MoveUnit;
        outMessage.moveUnit.unitId = payload["unit_id"].get<int>();
        outMessage.moveUnit.destination = games_types::CellCoord{targetX, targetY};
        responseToSend = BuildOkResponse();
        return true;
    }
    if (type == "ATTACK")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json& payload = data["payload"];
        if (!payload.contains("attacker_id") || !payload["attacker_id"].is_number_integer())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_attacker_id");
            return false;
        }

        if (!payload.contains("target_id") || !payload["target_id"].is_number_integer())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_target_id");
            return false;
        }

        const int attackerId = payload["attacker_id"].get<int>();
        const int targetId = payload["target_id"].get<int>();
        if (attackerId <= 0)
        {
            responseToSend = BuildErrorResponse("invalid_attacker_id_value");
            return false;
        }

        if (targetId < 0)
        {
            responseToSend = BuildErrorResponse("invalid_target_id_value");
            return false;
        }

        if (!isAttackerTroop(attackerId))
        {
            responseToSend = BuildErrorResponse("attacker_id_not_attacker_unit");
            return false;
        }

        outMessage.type = ParsedMessageType::Attack;
        outMessage.attack.attackerId = attackerId;
        outMessage.attack.targetId = targetId;
        responseToSend = BuildOkResponse();
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

    if (type == "PAUSE_GAME")
    {
        if (!data.contains("payload") || !data["payload"].is_object())
        {
            responseToSend = BuildErrorResponse("missing_or_invalid_payload");
            return false;
        }

        const json& payload = data["payload"];
        bool paused = false;
        if (payload.contains("paused") && payload["paused"].is_boolean())
        {
            paused = payload["paused"].get<bool>();
        }
        int pausedByPlayerId = -1;
        if (payload.contains("paused_by") && payload["paused_by"].is_number_integer())
        {
            pausedByPlayerId = payload["paused_by"].get<int>();
        }

        outMessage.type = ParsedMessageType::PauseGame;
        outMessage.pauseGame.paused = paused;
        outMessage.pauseGame.pausedByPlayerId = pausedByPlayerId;
        responseToSend = BuildOkResponse();
        return true;
    }

    if (type == "SURRENDER")
    {
        outMessage.type = ParsedMessageType::Surrender;
        responseToSend = BuildOkResponse();
        return true;
    }

    responseToSend = BuildErrorResponse("unsupported_message_type");
    return false;
}
