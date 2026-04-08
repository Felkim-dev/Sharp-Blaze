#include <cassert>
#include <iostream>
#include <memory>

#include "GameEngine.h"
#include "GameSession.h"

namespace
{
    void testPurchaseCollectorSuccess()
    {
        auto session = std::make_shared<GameSession>(1, 2, "test_session_a");
        GameEngine engine(session);

        const auto result = engine.processUnitPurchase(1, games_types::EntityType::Collector, 1);
        assert(result.success);
        assert(result.unitId >= games_types::id_ranges::p1Collectors.minId);
        assert(result.unitId <= games_types::id_ranges::p1Collectors.maxId);
        assert(result.newBalance == 400);
    }

    void testPurchaseStructureRejected()
    {
        auto session = std::make_shared<GameSession>(1, 2, "test_session_b");
        GameEngine engine(session);

        const auto result = engine.processUnitPurchase(1, games_types::EntityType::Structure, 1);
        assert(!result.success);
        assert(result.reason == "unit_type_not_purchasable");
    }

    void testResourceExtractionFinite()
    {
        GameSession session(1, 2, "test_session_c");
        const int first = session.extractResource(10000, 3900);
        const int second = session.extractResource(10000, 500);
        const int third = session.extractResource(10000, 10);

        assert(first == 3900);
        assert(second == 100);
        assert(third == 0);
    }

    void testCollectorStateAdvancesWithCollision()
    {
        auto session = std::make_shared<GameSession>(1, 2, "test_session_d");
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
}

int main()
{
    testPurchaseCollectorSuccess();
    testPurchaseStructureRejected();
    testResourceExtractionFinite();
    testCollectorStateAdvancesWithCollision();

    std::cout << "server_logic_tests: all checks passed\n";
    return 0;
}
