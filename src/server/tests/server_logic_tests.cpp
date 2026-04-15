#include <cassert>
#include <iostream>
#include <memory>

#include "GameEngine.h"
#include "GameSession.h"
#include "spatialGrid.h"

namespace
{
    void testPurchaseCollectorSuccess()
    {
        auto session = std::make_shared<GameSession>(1, 2, 1);
        GameEngine engine(session);

        session->upsertUnitPosition(3000, 2500.0f, 2500.0f);
        games_types::ShopAuthorizationState shopState{};
        const bool authChanged = engine.reconcileShopAuthorization(1, shopState);
        assert(authChanged);
        assert(shopState.authorized);
        assert(shopState.shopId == 11000);
        assert(shopState.unitId == 3000);

        const auto result = engine.processUnitPurchase(1, games_types::EntityType::Collector, 1);
        assert(result.success);
        assert(result.unitId >= games_types::id_ranges::p1Collectors.minId);
        assert(result.unitId <= games_types::id_ranges::p1Collectors.maxId);
        assert(result.newBalance == 400);
    }

    void testPurchaseWithoutShopAuthorizationRejected()
    {
        auto session = std::make_shared<GameSession>(1, 2, 2);
        GameEngine engine(session);

        const auto result = engine.processUnitPurchase(1, games_types::EntityType::Collector, 1);
        assert(!result.success);
        assert(result.reason == "shop_not_authorized");
    }

    void testPurchaseStructureRejected()
    {
        auto session = std::make_shared<GameSession>(1, 2, 3);
        GameEngine engine(session);

        const auto result = engine.processUnitPurchase(1, games_types::EntityType::Structure, 1);
        assert(!result.success);
        assert(result.reason == "unit_type_not_purchasable");
    }

    void testResourceExtractionFinite()
    {
        GameSession session(1, 2, 4);
        const int first = session.extractResource(10000, 3900);
        const int second = session.extractResource(10000, 500);
        const int third = session.extractResource(10000, 10);

        assert(first == 3900);
        assert(second == 100);
        assert(third == 0);
    }

    void testCollectorStateAdvancesWithCollision()
    {
        auto session = std::make_shared<GameSession>(1, 2, 5);
        GameEngine engine(session);

        // Place collector on top of a mine so collision immediately starts gathering.
        session->upsertUnitPosition(3000, 2500.0f, 2500.0f);
        engine.advanceCollectors(16);

        games_types::CollectorUnit collector{};
        const bool foundAfterStart = session->getCollector(3000, collector);
        assert(foundAfterStart);
        assert(collector.state == games_types::CollectorState::Gathering ||
               collector.state == games_types::CollectorState::Returning);

        // Advance enough time to finish gathering at least once.
        engine.advanceCollectors(1200);
        const bool foundAfterGather = session->getCollector(3000, collector);
        assert(foundAfterGather);
        assert(collector.state == games_types::CollectorState::Returning ||
               collector.state == games_types::CollectorState::Depositing ||
               collector.state == games_types::CollectorState::Idle);
    }

    void testShopAuthorizationGrantAndRevoke()
    {
        auto session = std::make_shared<GameSession>(1, 2, 6);
        GameEngine engine(session);

        session->upsertUnitPosition(1000, 2500.0f, 2500.0f);

        games_types::ShopAuthorizationState shopState{};
        bool changed = engine.reconcileShopAuthorization(1, shopState);
        assert(changed);
        assert(shopState.authorized);
        assert(engine.hasShopAuthorization(1));

        session->upsertUnitPosition(1000, 100.0f, 100.0f);
        changed = engine.reconcileShopAuthorization(1, shopState);
        assert(changed);
        assert(!shopState.authorized);
        assert(!engine.hasShopAuthorization(1));
    }

    void testSpatialGridPlaceAndMove()
    {
        SpatialGrid grid(100, 100);

        const bool placed = grid.placeEntity(1000, games_types::CellCoord{10, 10});
        assert(placed);

        auto moveResult = grid.tryReserveMove(1000, games_types::CellCoord{11, 10});
        assert(moveResult.accepted());

        const auto deltas = grid.commitReservedMoves();
        assert(deltas.size() == 1);
        assert(deltas.front().entityId == 1000);
        assert(deltas.front().to.x == 11);
        assert(deltas.front().to.y == 10);

        games_types::CellCoord currentCell{};
        const bool found = grid.getEntityCell(1000, currentCell);
        assert(found);
        assert(currentCell.x == 11);
        assert(currentCell.y == 10);
    }

    void testSpatialGridRejectsOccupiedCell()
    {
        SpatialGrid grid(100, 100);
        assert(grid.placeEntity(1000, SpatialGrid::CellCoord{5, 5}));
        assert(grid.placeEntity(1001, SpatialGrid::CellCoord{5, 6}));

        const auto moveResult = grid.tryReserveMove(1001, games_types::CellCoord{5, 5});
        assert(moveResult.status == games_types::MoveStatus::Occupied);
        assert(moveResult.blockerEntityId == 1000);
    }

    void testSpatialGridReservationConflict()
    {
        SpatialGrid grid(100, 100);
        assert(grid.placeEntity(2000, games_types::CellCoord{1, 1}));
        assert(grid.placeEntity(2001, games_types::CellCoord{1, 2}));

        const auto first = grid.tryReserveMove(2000, games_types::CellCoord{2, 2});
        assert(first.accepted());

        const auto second = grid.tryReserveMove(2001, games_types::CellCoord{2, 2});
        assert(second.status == games_types::MoveStatus::ReservedByOther);
        assert(second.blockerEntityId == 2000);
    }
}

int main()
{
    testPurchaseCollectorSuccess();
    testPurchaseWithoutShopAuthorizationRejected();
    testPurchaseStructureRejected();
    testResourceExtractionFinite();
    testCollectorStateAdvancesWithCollision();
    testShopAuthorizationGrantAndRevoke();
    testSpatialGridPlaceAndMove();
    testSpatialGridRejectsOccupiedCell();
    testSpatialGridReservationConflict();

    std::cout << "server_logic_tests: all checks passed\n";
    return 0;
}
