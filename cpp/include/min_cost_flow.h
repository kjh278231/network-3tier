#pragma once

#include "data_model.h"
#include <vector>

namespace n3t {

// ─── Min-Cost Flow Solver ─────────────────────────────────────────────────────
// Given a fixed warehouse-customer assignment and open warehouse set,
// computes the optimal plant->warehouse flows that:
//   1. Maximize total inbound (Phase 1)
//   2. Minimize total transport cost while maintaining max inbound (Phase 2)

struct FlowResult {
    std::vector<std::vector<int64_t>> flows;  // flows[plant_idx][warehouse_idx]
    int64_t total_inbound;
    double total_transport_cost;
    bool feasible;
};

class MinCostFlowSolver {
public:
    explicit MinCostFlowSolver(const ProblemInstance& instance);

    // Solve the flow sub-problem given current assignment
    FlowResult solve(const std::vector<bool>& open_warehouses,
                     const std::vector<int>& customer_assignment) const;

private:
    const ProblemInstance& inst_;

    // Internal: compute demand per open warehouse from assignment
    std::vector<int64_t> compute_warehouse_demand(
        const std::vector<bool>& open_warehouses,
        const std::vector<int>& customer_assignment) const;

    // Successive Shortest Path based min-cost flow
    FlowResult solve_ssp(const std::vector<int64_t>& warehouse_demand,
                         const std::vector<bool>& open_warehouses) const;
};

}  // namespace n3t
