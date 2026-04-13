#include <cassert>
#include <iostream>
#include <memory>

#include "GameEngine.h"
#include "GameSession.h"

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
}

int main()
{
    testPurchaseCollectorSuccess();
    testPurchaseWithoutShopAuthorizationRejected();
    testPurchaseStructureRejected();
    testResourceExtractionFinite();
    testCollectorStateAdvancesWithCollision();
    testShopAuthorizationGrantAndRevoke();

    std::cout << "server_logic_tests: all checks passed\n";
    return 0;
}
