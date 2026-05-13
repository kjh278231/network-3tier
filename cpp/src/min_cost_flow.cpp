#include "min_cost_flow.h"
#include <algorithm>
#include <limits>
#include <numeric>
#include <queue>
#include <vector>

namespace n3t {

MinCostFlowSolver::MinCostFlowSolver(const ProblemInstance& instance)
    : inst_(instance) {}

std::vector<int64_t> MinCostFlowSolver::compute_warehouse_demand(
    const std::vector<bool>& open_warehouses,
    const std::vector<int>& customer_assignment) const {

    std::vector<int64_t> demand(inst_.num_warehouses(), 0);
    for (int c = 0; c < inst_.num_customers(); ++c) {
        int w = customer_assignment[c];
        if (w >= 0 && open_warehouses[w]) {
            demand[w] += inst_.customers[c].do_qty;
        }
    }
    return demand;
}

FlowResult MinCostFlowSolver::solve(
    const std::vector<bool>& open_warehouses,
    const std::vector<int>& customer_assignment) const {

    auto warehouse_demand = compute_warehouse_demand(open_warehouses, customer_assignment);
    return solve_ssp(warehouse_demand, open_warehouses);
}

// ─── Successive Shortest Path Algorithm ───────────────────────────────────────
// Models the problem as a min-cost flow network:
//   - Super source (S) -> each plant p: capacity = plant.product_qty, cost = 0
//   - Each plant p -> each open warehouse w: capacity = min(plant.product_qty, wh.capacity_qty), cost = pw_trns_cost
//   - Each open warehouse w -> super sink (T): capacity = wh.capacity_qty, cost = 0
//
// Phase 1: Find max-flow (maximize inbound)
// Phase 2: Among max-flow solutions, find min-cost

FlowResult MinCostFlowSolver::solve_ssp(
    const std::vector<int64_t>& warehouse_demand,
    const std::vector<bool>& open_warehouses) const {

    const int np = inst_.num_plants();
    const int nw = inst_.num_warehouses();

    // Node layout: 0 = source, 1..np = plants, np+1..np+nw = warehouses, np+nw+1 = sink
    const int S = 0;
    const int T = np + nw + 1;
    const int N = T + 1;

    // Adjacency list for the flow network
    struct Edge {
        int to, rev;
        int64_t cap, flow;
        double cost;
    };

    std::vector<std::vector<Edge>> graph(N);

    auto add_edge = [&](int from, int to, int64_t cap, double cost) {
        graph[from].push_back({to, static_cast<int>(graph[to].size()), cap, 0, cost});
        graph[to].push_back({from, static_cast<int>(graph[from].size()) - 1, 0, 0, -cost});
    };

    // Source -> Plants
    for (int p = 0; p < np; ++p) {
        add_edge(S, p + 1, inst_.plants[p].product_qty, 0.0);
    }

    // Plants -> Warehouses
    for (int p = 0; p < np; ++p) {
        for (int w = 0; w < nw; ++w) {
            if (!open_warehouses[w]) continue;
            double cost = inst_.pw_cost_matrix[p][w];
            if (cost == std::numeric_limits<double>::infinity()) continue;
            int64_t cap = std::min(inst_.plants[p].product_qty,
                                   inst_.warehouses[w].capacity_qty);
            add_edge(p + 1, np + 1 + w, cap, cost);
        }
    }

    // Warehouses -> Sink
    // Capacity = warehouse throughput capacity (allows inbound up to capacity)
    for (int w = 0; w < nw; ++w) {
        if (!open_warehouses[w]) continue;
        add_edge(np + 1 + w, T, inst_.warehouses[w].capacity_qty, 0.0);
    }

    // ─── Phase 1: Max Flow using Bellman-Ford based SSP ───────────────────────
    // We use SPFA (Shortest Path Faster Algorithm) for finding augmenting paths
    // with negative cost edges in the residual graph.
    // Since we want MAX flow first, we use cost=0 for all edges initially
    // and just find augmenting paths.

    // Actually, for this problem we do a simpler two-phase approach:
    // Phase 1: Compute max-flow (ignore costs, just push as much flow as possible)
    // Phase 2: Among all max-flow solutions, find the one with minimum cost

    // Simplified approach: Use min-cost max-flow directly with SSP
    // The SSP naturally finds max-flow with min-cost when we use the actual costs.
    // But our objective is: first maximize flow, then minimize cost.
    // Strategy: Set very negative cost on warehouse->sink edges to prioritize flow,
    // then the SSP will naturally maximize flow first.

    // Better approach: Two-pass
    // Pass 1: Find max flow (BFS/DFS augmenting paths, ignore cost)
    // Pass 2: Fix total flow = max_flow, find min-cost flow

    // For simplicity and correctness, we use a single-pass min-cost max-flow
    // with a large negative cost on sink edges to ensure max flow is prioritized.

    // Reset graph and rebuild with priority costs
    graph.assign(N, std::vector<Edge>());

    // Source -> Plants (cost = 0)
    for (int p = 0; p < np; ++p) {
        add_edge(S, p + 1, inst_.plants[p].product_qty, 0.0);
    }

    // Plants -> Warehouses (cost = actual transport cost)
    for (int p = 0; p < np; ++p) {
        for (int w = 0; w < nw; ++w) {
            if (!open_warehouses[w]) continue;
            double cost = inst_.pw_cost_matrix[p][w];
            if (cost == std::numeric_limits<double>::infinity()) continue;
            int64_t cap = std::min(inst_.plants[p].product_qty,
                                   inst_.warehouses[w].capacity_qty);
            add_edge(p + 1, np + 1 + w, cap, cost);
        }
    }

    // Warehouses -> Sink (cost = large negative to prioritize flow)
    // The magnitude should be larger than any possible transport cost sum
    double big_negative = -1e9;
    for (int w = 0; w < nw; ++w) {
        if (!open_warehouses[w]) continue;
        add_edge(np + 1 + w, T, inst_.warehouses[w].capacity_qty, big_negative);
    }

    // ─── SPFA-based Min-Cost Max-Flow ─────────────────────────────────────────
    int64_t total_flow = 0;
    double total_cost = 0.0;

    while (true) {
        // SPFA to find shortest path from S to T
        std::vector<double> dist(N, std::numeric_limits<double>::infinity());
        std::vector<bool> in_queue(N, false);
        std::vector<int> prev_node(N, -1);
        std::vector<int> prev_edge(N, -1);

        dist[S] = 0.0;
        std::queue<int> q;
        q.push(S);
        in_queue[S] = true;

        while (!q.empty()) {
            int u = q.front();
            q.pop();
            in_queue[u] = false;

            for (int i = 0; i < static_cast<int>(graph[u].size()); ++i) {
                const Edge& e = graph[u][i];
                if (e.cap - e.flow > 0 && dist[u] + e.cost < dist[e.to] - 1e-9) {
                    dist[e.to] = dist[u] + e.cost;
                    prev_node[e.to] = u;
                    prev_edge[e.to] = i;
                    if (!in_queue[e.to]) {
                        q.push(e.to);
                        in_queue[e.to] = true;
                    }
                }
            }
        }

        if (dist[T] == std::numeric_limits<double>::infinity()) break;

        // Find bottleneck capacity along the path
        int64_t path_flow = std::numeric_limits<int64_t>::max();
        for (int v = T; v != S; v = prev_node[v]) {
            int u = prev_node[v];
            int idx = prev_edge[v];
            path_flow = std::min(path_flow, graph[u][idx].cap - graph[u][idx].flow);
        }

        // Augment flow along the path
        for (int v = T; v != S; v = prev_node[v]) {
            int u = prev_node[v];
            int idx = prev_edge[v];
            graph[u][idx].flow += path_flow;
            graph[v][graph[u][idx].rev].flow -= path_flow;
        }

        total_flow += path_flow;
        total_cost += path_flow * dist[T];
    }

    // Extract flows from graph
    FlowResult result;
    result.flows.assign(np, std::vector<int64_t>(nw, 0));
    result.total_inbound = total_flow;
    // Adjust cost: remove the big_negative contribution from sink edges
    result.total_transport_cost = total_cost - total_flow * big_negative;
    result.feasible = (total_flow > 0);

    // Extract plant->warehouse flows from the graph edges
    // Plant nodes are 1..np, warehouse nodes are np+1..np+nw
    for (int p = 0; p < np; ++p) {
        int plant_node = p + 1;
        for (const auto& e : graph[plant_node]) {
            if (e.to >= np + 1 && e.to <= np + nw && e.flow > 0) {
                int w = e.to - np - 1;
                result.flows[p][w] = e.flow;
            }
        }
    }

    return result;
}

}  // namespace n3t
