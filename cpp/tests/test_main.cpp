#include "data_model.h"
#include "constraint_checker.h"
#include "min_cost_flow.h"
#include "lns_engine.h"
#include "solver.h"

#include <cassert>
#include <iostream>
#include <vector>

using namespace n3t;

// ─── Helper: Create a small test instance ─────────────────────────────────────
ProblemInstance create_test_instance() {
    ProblemInstance inst;

    // 2 plants
    inst.plants.push_back({0, "P1", "Plant A", 100, 10});
    inst.plants.push_back({1, "P2", "Plant B", 80, 10});

    // 3 warehouses
    inst.warehouses.push_back({0, "W1", "Warehouse 1", 120, 1000.0, 5.0, true});
    inst.warehouses.push_back({1, "W2", "Warehouse 2", 100, 800.0, 4.0, true});
    inst.warehouses.push_back({2, "W3", "Warehouse 3", 90, 900.0, 6.0, true});

    // 5 customers
    inst.customers.push_back({0, "C1", "Customer 1", 30, 5, -1});
    inst.customers.push_back({1, "C2", "Customer 2", 25, 5, -1});
    inst.customers.push_back({2, "C3", "Customer 3", 20, 5, -1});
    inst.customers.push_back({3, "C4", "Customer 4", 35, 5, -1});
    inst.customers.push_back({4, "C5", "Customer 5", 15, 5, 0});  // mapped to W1

    // Plant-Warehouse arcs
    inst.pw_arcs.push_back({0, 0, 100.0, 2.0});
    inst.pw_arcs.push_back({0, 1, 150.0, 3.0});
    inst.pw_arcs.push_back({0, 2, 200.0, 4.0});
    inst.pw_arcs.push_back({1, 0, 120.0, 2.5});
    inst.pw_arcs.push_back({1, 1, 80.0, 1.5});
    inst.pw_arcs.push_back({1, 2, 180.0, 3.5});

    // Warehouse-Customer arcs (all warehouses can serve all customers)
    for (int w = 0; w < 3; ++w) {
        for (int c = 0; c < 5; ++c) {
            double dist = 50.0 + w * 20.0 + c * 10.0;
            double cost = 1.0 + w * 0.5 + c * 0.3;
            inst.wc_arcs.push_back({w, c, dist, cost});
        }
    }

    // Simulation parameters
    inst.warehouse_qty = 2;
    inst.speed_kmh = 60.0;
    inst.coverage_hours = 4.0;
    inst.inventory_ratio = 0.8;  // relaxed for test feasibility

    inst.build_cost_matrices();
    return inst;
}

// ─── Test: Data Model ─────────────────────────────────────────────────────────
void test_data_model() {
    std::cout << "Test: Data Model... ";
    auto inst = create_test_instance();

    assert(inst.num_plants() == 2);
    assert(inst.num_warehouses() == 3);
    assert(inst.num_customers() == 5);
    assert(inst.pw_cost_matrix[0][0] == 2.0);
    assert(inst.eligible_warehouses[0].size() == 3);

    std::cout << "PASSED" << std::endl;
}

// ─── Test: Constraint Checker ─────────────────────────────────────────────────
void test_constraint_checker() {
    std::cout << "Test: Constraint Checker... ";
    auto inst = create_test_instance();
    ConstraintChecker checker(inst);

    // Create a valid solution
    Solution sol;
    sol.open_warehouses = {true, true, false};
    sol.customer_assignment = {0, 0, 1, 1, 0};  // C5 mapped to W1(idx=0)
    sol.warehouse_outbound = {30 + 25 + 15, 20 + 35, 0};  // W1=70, W2=55
    sol.warehouse_inbound = {80, 60, 0};
    sol.flows = {{80, 0, 0}, {0, 60, 0}};

    assert(checker.check_single_assignment(sol));
    assert(checker.check_warehouse_count(sol));
    assert(checker.check_mapping_constraints(sol));
    assert(checker.check_inbound_geq_outbound(sol));

    std::cout << "PASSED" << std::endl;
}

// ─── Test: Min-Cost Flow ──────────────────────────────────────────────────────
void test_min_cost_flow() {
    std::cout << "Test: Min-Cost Flow... ";
    auto inst = create_test_instance();
    MinCostFlowSolver flow_solver(inst);

    std::vector<bool> open_wh = {true, true, false};
    std::vector<int> assignment = {0, 0, 1, 1, 0};

    auto result = flow_solver.solve(open_wh, assignment);

    assert(result.feasible);
    assert(result.total_inbound > 0);

    // Check that total flow to each warehouse >= outbound demand
    int64_t wh0_flow = 0, wh1_flow = 0;
    for (int p = 0; p < 2; ++p) {
        wh0_flow += result.flows[p][0];
        wh1_flow += result.flows[p][1];
    }
    assert(wh0_flow >= 70);  // W1 outbound = 30+25+15 = 70
    assert(wh1_flow >= 55);  // W2 outbound = 20+35 = 55

    std::cout << "PASSED (inbound=" << result.total_inbound
              << ", cost=" << result.total_transport_cost << ")" << std::endl;
}

// ─── Test: LNS Engine ─────────────────────────────────────────────────────────
void test_lns_engine() {
    std::cout << "Test: LNS Engine... ";
    auto inst = create_test_instance();

    LNSConfig config;
    config.max_iterations = 100;
    config.time_limit_sec = 5.0;
    config.random_seed = 42;

    LNSEngine engine(inst, config);
    Solution sol = engine.solve();

    assert(sol.is_feasible);
    assert(sol.total_inbound > 0);
    assert(sol.total_cost > 0);

    // Check warehouse count
    int open_count = 0;
    for (bool open : sol.open_warehouses) {
        if (open) ++open_count;
    }
    assert(open_count == inst.warehouse_qty);

    // Check mapping constraint
    assert(sol.customer_assignment[4] == 0);  // C5 mapped to W1

    std::cout << "PASSED (inbound=" << sol.total_inbound
              << ", cost=" << sol.total_cost << ")" << std::endl;
}

// ─── Test: Full Solver ────────────────────────────────────────────────────────
void test_solver() {
    std::cout << "Test: Full Solver... ";
    auto inst = create_test_instance();

    SolverConfig config;
    config.lns_config.max_iterations = 200;
    config.lns_config.time_limit_sec = 5.0;

    Solver solver(inst, config);
    auto result = solver.solve();

    assert(result.status == "FEASIBLE");
    assert(result.best_solution.is_feasible);
    assert(result.elapsed_seconds > 0.0);

    std::cout << "PASSED (status=" << result.status
              << ", inbound=" << result.best_solution.total_inbound
              << ", cost=" << result.best_solution.total_cost
              << ", time=" << result.elapsed_seconds << "s)" << std::endl;
}

// ─── Main ─────────────────────────────────────────────────────────────────────
int main() {
    std::cout << "=== Network 3-Tier Custom Solver Tests ===" << std::endl;
    std::cout << std::endl;

    test_data_model();
    test_constraint_checker();
    test_min_cost_flow();
    test_lns_engine();
    test_solver();

    std::cout << std::endl;
    std::cout << "All tests PASSED!" << std::endl;
    return 0;
}
