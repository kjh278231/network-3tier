#pragma once

#include "data_model.h"
#include "lns_engine.h"

namespace n3t {

// ─── Solver Interface ─────────────────────────────────────────────────────────
// Top-level interface that orchestrates the optimization process.

struct SolverConfig {
    LNSConfig lns_config;
    bool enable_inventory_capacity = true;
};

struct SolverResult {
    Solution best_solution;
    double elapsed_seconds;
    int iterations_performed;
    std::string status;  // "OPTIMAL", "FEASIBLE", "INFEASIBLE"
};

class Solver {
public:
    Solver(const ProblemInstance& instance, const SolverConfig& config);

    // Solve the full problem (best_model)
    SolverResult solve();

    // Solve with forced open warehouses (designated model)
    SolverResult solve_fixed(const std::vector<int>& forced_open_warehouses);

private:
    ProblemInstance inst_;
    SolverConfig config_;
};

}  // namespace n3t
