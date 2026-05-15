#include "min_cost_flow.h"
#include <queue>
#include <limits>
#include <algorithm>
#include <iostream>

namespace n3t {

MinCostFlowSolver::MinCostFlowSolver(const ProblemInstance& instance)
    : inst_(instance) {}

void MinCostFlowSolver::add_edge(int from, int to, int64_t cap, double cost, std::vector<std::vector<Edge>>& local_graph) const {
    local_graph[from].push_back({to, cap, 0, cost, static_cast<int>(local_graph[to].size())});
    local_graph[to].push_back({from, 0, 0, -cost, static_cast<int>(local_graph[from].size()) - 1});
}

FlowResult MinCostFlowSolver::solve(const std::vector<bool>& open_warehouses, const std::vector<int>& customer_assignment) const {
    int np = inst_.num_plants();
    int nw = inst_.num_warehouses();
    int nc = inst_.num_customers();
    int S = 0, T = np + nw + 1;
    int N = T + 1;

    std::vector<std::vector<Edge>> local_graph(N);
    
    for (int p = 0; p < np; ++p) {
        add_edge(S, p + 1, inst_.plants[p].product_qty, 0.0, local_graph);
    }
    
    for (int p = 0; p < np; ++p) {
        for (int w = 0; w < nw; ++w) {
            if (!open_warehouses[w]) continue;
            double cost = inst_.pw_cost_matrix[p][w];
            if (cost == std::numeric_limits<double>::infinity()) continue;
            add_edge(p + 1, np + 1 + w, std::numeric_limits<int64_t>::max(), cost, local_graph);
        }
    }
    
    double big_negative = -1e6; 
    for (int w = 0; w < nw; ++w) {
        if (!open_warehouses[w]) continue;
        add_edge(np + 1 + w, T, inst_.warehouses[w].capacity_qty, big_negative, local_graph);
    }

    int64_t total_flow = 0;
    double total_cost_with_neg = 0.0;
    
    while (true) {
        std::vector<double> dist(N, std::numeric_limits<double>::infinity());
        std::vector<int> prev_node(N, -1);
        std::vector<int> prev_edge(N, -1);
        std::vector<bool> in_queue(N, false);
        std::queue<int> q;

        dist[S] = 0.0;
        q.push(S);
        in_queue[S] = true;

        while (!q.empty()) {
            int u = q.front();
            q.pop();
            in_queue[u] = false;
            for (int i = 0; i < static_cast<int>(local_graph[u].size()); ++i) {
                const Edge& e = local_graph[u][i];
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

        int64_t path_flow = std::numeric_limits<int64_t>::max();
        for (int v = T; v != S; v = prev_node[v]) {
            int u = prev_node[v];
            int idx = prev_edge[v];
            path_flow = std::min(path_flow, local_graph[u][idx].cap - local_graph[u][idx].flow);
        }

        for (int v = T; v != S; v = prev_node[v]) {
            int u = prev_node[v];
            int idx = prev_edge[v];
            local_graph[u][idx].flow += path_flow;
            local_graph[v][local_graph[u][idx].rev].flow -= path_flow;
        }
        total_flow += path_flow;
        total_cost_with_neg += static_cast<double>(path_flow) * dist[T];
    }

    FlowResult result;
    result.flows.assign(np, std::vector<int64_t>(nw, 0));
    result.total_inbound = total_flow;
    result.total_transport_cost = total_cost_with_neg - static_cast<double>(total_flow) * big_negative;
    
    if (result.total_transport_cost < 0) result.total_transport_cost = 0;

    int64_t total_outbound = 0;
    for (int c = 0; c < nc; ++c) {
        if (customer_assignment[c] >= 0) total_outbound += inst_.customers[c].do_qty;
    }
    result.feasible = (total_flow >= total_outbound);

    for (int p = 0; p < np; ++p) {
        for (const auto& e : local_graph[p + 1]) {
            if (e.to >= np + 1 && e.to <= np + nw && e.flow > 0) {
                result.flows[p][e.to - np - 1] = e.flow;
            }
        }
    }

    return result;
}

}  // namespace n3t
