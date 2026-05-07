#pragma once

#include <chrono>
#include <cstdint>
#include <string>
#include <vector>
#include "platform_socket.h"

namespace games_types
{
    //estructuras para el spatialGrid:
    struct CellCoord
    {
        int x = 0;
        int y = 0;

        bool operator==(const CellCoord &other) const
        {
            return x == other.x && y == other.y;
        }
    };

    enum class MoveStatus : std::uint8_t
    {
        Ok,
        InvalidEntity,
        OutOfBounds,
        StaticBlocked,
        Occupied,
        ReservedByOther
    };

    struct MoveResult
    {
        MoveStatus status = MoveStatus::Ok;
        CellCoord from{};
        CellCoord to{};
        int blockerEntityId = -1;

        bool accepted() const
        {
            return status == MoveStatus::Ok;
        }
    };

    struct GridDelta
    {
        int entityId = 0;
        CellCoord from{};
        CellCoord to{};
    };
    enum class EntityType : std::uint8_t
    {
        Structure,
        Attacker,
        Collector,
        ResourceMine,
        Shop,
        Unknown,
        Bomb
    };

    enum class ResourceType : std::uint8_t
    {
        Gold,
        Unknown
    };

    enum class CollectorState : std::uint8_t
    {
        Idle,
        Gathering,
        Returning,
        Depositing
    };

    enum class CommandType : std::uint8_t
    {
        MoveUnit,
        AttackUnit,
        BuyUnit,
        GatherResource,
        DepositResource
    };
    enum class CellType : std::uint8_t
    {
        Free,
        OccupiedDynamic,
        Blocked,
        Static,
    };
    struct Cell
    {
        int x;
        int y;
    };

    struct IdRange
    {
        int minId = 0;
        int maxId = 0;

        bool contains(int id) const
        {
            return id >= minId && id <= maxId;
        }
    };

    namespace id_ranges
    {
        inline constexpr IdRange p1Structures{0, 999};
        inline constexpr IdRange p1Attackers{1000, 2999};
        inline constexpr IdRange p1Collectors{3000, 4999};

        inline constexpr IdRange p2Structures{5000, 5999};
        inline constexpr IdRange p2Attackers{6000, 7999};
        inline constexpr IdRange p2Collectors{8000, 9999};

        inline constexpr IdRange resourceMines{10000, 10999};
        inline constexpr IdRange shops{11000, 11999};

        inline constexpr IdRange p1Bombs{12000, 12999};
        inline constexpr IdRange p2Bombs{13000, 13999};
    }

    inline EntityType classifyEntityTypeFromId(int entityId)
    {
        if (id_ranges::p1Structures.contains(entityId) || id_ranges::p2Structures.contains(entityId))
        {
            return EntityType::Structure;
        }
        if (id_ranges::p1Attackers.contains(entityId) || id_ranges::p2Attackers.contains(entityId))
        {
            return EntityType::Attacker;
        }
        if (id_ranges::p1Collectors.contains(entityId) || id_ranges::p2Collectors.contains(entityId))
        {
            return EntityType::Collector;
        }
        if (id_ranges::resourceMines.contains(entityId))
        {
            return EntityType::ResourceMine;
        }
        if (id_ranges::shops.contains(entityId))
        {
            return EntityType::Shop;
        }
        if (id_ranges::p1Bombs.contains(entityId) || id_ranges::p2Bombs.contains(entityId))
        {
            return EntityType::Bomb;
        }

        return EntityType::Unknown;
    }

    inline bool isPlayerControllableUnitId(int playerId, int entityId)
    {
        if (playerId == 1)
        {
            return id_ranges::p1Attackers.contains(entityId) || id_ranges::p1Collectors.contains(entityId);
        }
        if (playerId == 2)
        {
            return id_ranges::p2Attackers.contains(entityId) || id_ranges::p2Collectors.contains(entityId);
        }
        return false;
    }

    struct RegisteredClient // estructura para registrar a los clientes
    {
        sockaddr_in addr;
        int sessionId;
        std::chrono::steady_clock::time_point lastSeen;
    };

    struct UdpHelloMessage
    {
        static constexpr std::uint32_t protocolVersion = 1;

        std::uint32_t version = protocolVersion;
        int playerId           = 0;
        int sessionId;
        std::uint32_t checksum = 0;
    };

    struct UdpEndpoint
    {
        sockaddr_in addr{};
        int sessionId;
        int playerId = 0;
        std::chrono::steady_clock::time_point lastSeen{};
    };
    struct UnitPosition // estructure para los paquetes udp de cada unidad
    {
        int entity_id;
        float x, y;
    };

    struct EntityRef
    {
        int entityId          = 0;
        int ownerPlayerId     = 0;
        EntityType entityType = EntityType::Unknown;
    };

    struct ResourceNode
    {
        int entityId          = 0;
        ResourceType resourceType = ResourceType::Gold;
        float x               = 0.0f;
        float y               = 0.0f;
        float radius          = 400.0f;
        int remainingCapacity = 0;
        int extractionPerTick = 0;
    };

    struct CollectorUnit
    {
        int entityId             = 0;
        int ownerPlayerId        = 0;
        CollectorState state = CollectorState::Idle;
        float x                  = 0.0f;
        float y                  = 0.0f;
        int targetResourceId     = -1;
        int carriedAmount        = 0;
        int carryCapacity        = 200;
        int gatherDurationMs     = 1000;
        int depositDurationMs    = 500;
        int stateTimeRemainingMs = 0;
        int maxHp;
        int currentHp;
    };
    struct ShopUnit
    {
        int entityId = 0;
        float x      = 0.0f;
        float y      = 0.0f;
        float radius = 400.0f;
    };

    struct StaticObstacle
    {
        int id = 0;
        std::vector<CellCoord> cells;
    };

    // struct StaticObstacle
    // {
    //     int id = 0;
    //     std::vector<CellCoord> cells;
    // };

    struct ShopAuthorizationState
    {
        bool authorized = false;
        int shopId = -1;
        int unitId = -1;
    };
    struct BuyUnitPayload
    {
        EntityType unitType = EntityType::Collector;
        int quantity = 1;
    };

    struct DepositResourcePayload
    {
        int collectorId = 0;
        ResourceType resourceType = ResourceType::Gold;
        int amount      = 0;
    };

    struct AttackPayload
    {
        int attackerId = 0;
        int targetId = 0;
    };

    struct GatherResourcePayload
    {
        int collectorId    = 0;
        int resourceNodeId = 0;
    };

    struct EconomyTransaction
    {
        int playerId       = 0;
        int deltaGold      = 0;
        int resultingGold  = 0;
        std::string reason;
    };

    enum class CombatEventType : std::uint8_t
    {
        UnitDamaged,
        EntityDestroyed,
        GameOver
    };

    struct CombatEvent
    {
        CombatEventType type = CombatEventType::UnitDamaged;
        int sessionId = 0;
        int attackerPlayerId = 0;
        int attackerEntityId = 0;
        int targetPlayerId   = 0;
        int targetEntityId   = 0;
        int currentHp        = 0;
        int maxHp            = 0;
        int winnerPlayerId   = 0;
    };

    struct DamageResolution
    {
        bool applied       = false;
        int entityId       = 0;
        int ownerPlayerId  = 0;
        int currentHp      = 0;
        int maxHp          = 0;
        bool destroyed     = false;
        bool gameOver      = false;
        int winnerPlayerId = 0;
    };

    struct PlayerCommand
    {
        CommandType type = CommandType::MoveUnit;
        int playerId     = 0;
        int unitId       = 0;
        CellCoord destCell{};

        BuyUnitPayload buyUnit;
        DepositResourcePayload deposit;
        AttackPayload attack;
        GatherResourcePayload gather;
    };
}