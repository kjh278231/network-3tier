#pragma once
#include "data_model.h"
#include <vector>

namespace n3t {

struct FlowResult {
    std::vector<std::vector<int64_t>> flows;
    int64_t total_inbound;
    double total_transport_cost;
    bool feasible;
};

struct Edge {
    int to;
    int64_t cap;
    int64_t flow;
    double cost;
    int rev;
};

class MinCostFlowSolver {
public:
    MinCostFlowSolver(const ProblemInstance& instance);
    FlowResult solve(const std::vector<bool>& open_warehouses,
                    const std::vector<int>& customer_assignment) const;

private:
    const ProblemInstance& inst_;
    void add_edge(int from, int to, int64_t cap, double cost, std::vector<std::vector<Edge>>& local_graph) const;
};

}  // namespace n3t
