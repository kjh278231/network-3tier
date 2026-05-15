#pragma once

#include "constraint_checker.h"
#include "data_model.h"
#include "min_cost_flow.h"

#include <functional>
#include <random>
#include <vector>

namespace n3t {

// ─── LNS Configuration ───────────────────────────────────────────────────────

struct LNSConfig {
    int max_iterations = 10000;
    double time_limit_sec = 60.0;
    int destroy_min_customers = 3;
    int destroy_max_customers = 20;
    double sa_initial_temp = 1000.0;
    double sa_cooling_rate = 0.9995;
    unsigned int random_seed = 42;
};

// ─── LNS Engine ──────────────────────────────────────────────────────────────

class LNSEngine {
public:
    LNSEngine(const ProblemInstance& instance, const LNSConfig& config);

    // Run the full LNS optimization and return best solution found
    Solution solve();

    // Generate initial feasible solution using greedy heuristic
    Solution generate_initial_solution();

    // ─── Evaluation ───────────────────────────────────────────────────────────
    // Evaluate full cost of a solution (calls flow solver)
    void evaluate(Solution& sol);

private:
    const ProblemInstance& inst_;
    LNSConfig config_;
    ConstraintChecker checker_;
    MinCostFlowSolver flow_solver_;
    std::mt19937 rng_;

    // ─── Destroy Operators ────────────────────────────────────────────────────
    // Returns indices of customers whose assignments are removed
    std::vector<int> destroy_random(Solution& sol);
    std::vector<int> destroy_worst_cost(Solution& sol);
    std::vector<int> destroy_warehouse(Solution& sol);

    // ─── Repair Operators ─────────────────────────────────────────────────────
    // Reassigns unassigned customers (assignment[c] == -1)
    bool repair_greedy(Solution& sol, const std::vector<int>& removed);
    bool repair_regret(Solution& sol, const std::vector<int>& removed);

    // ─── Acceptance ───────────────────────────────────────────────────────────
    bool accept(double current_cost, double new_cost, double temperature);

    // ─── Utilities ────────────────────────────────────────────────────────────
    void update_warehouse_aggregates(Solution& sol);
};

}  // namespace n3t
