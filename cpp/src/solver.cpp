#include "solver.h"
#include <chrono>
#include <random>
#include <limits>

namespace n3t {

Solver::Solver(const ProblemInstance& instance, const SolverConfig& config)
    : inst_(instance), config_(config) {
    inst_.build_cost_matrices();
}

SolverResult Solver::solve() {
    auto start = std::chrono::steady_clock::now();

    LNSEngine engine(inst_, config_.lns_config);
    Solution best = engine.solve();

    auto end = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(end - start).count();

    SolverResult result;
    result.best_solution = best;
    result.elapsed_seconds = elapsed;
    result.iterations_performed = config_.lns_config.max_iterations;

    if (best.is_feasible) {
        result.status = "FEASIBLE";
    } else {
        result.status = "INFEASIBLE";
    }

    return result;
}

SolverResult Solver::solve_fixed(const std::vector<int>& forced_open_warehouses) {
    auto start = std::chrono::steady_clock::now();

    // Create a modified LNS config that fixes warehouse selection
    LNSConfig fixed_config = config_.lns_config;
    fixed_config.max_iterations = std::max(1000, config_.lns_config.max_iterations / 5);

    LNSEngine engine(inst_, fixed_config);

    // Generate initial solution with forced warehouses
    int nw = inst_.num_warehouses();
    int nc = inst_.num_customers();
    int np = inst_.num_plants();

    Solution sol;
    sol.open_warehouses.assign(nw, false);
    for (int w : forced_open_warehouses) {
        if (w >= 0 && w < nw) {
            sol.open_warehouses[w] = true;
        }
    }
    sol.customer_assignment.assign(nc, -1);
    sol.flows.assign(np, std::vector<int64_t>(nw, 0));
    sol.warehouse_inbound.assign(nw, 0);
    sol.warehouse_outbound.assign(nw, 0);

    // Assign mapped customers
    for (int c = 0; c < nc; ++c) {
        int mapped = inst_.customers[c].mapped_warehouse;
        if (mapped >= 0 && sol.open_warehouses[mapped]) {
            sol.customer_assignment[c] = mapped;
            sol.warehouse_outbound[mapped] += inst_.customers[c].do_qty;
        }
    }

    // Greedy assignment for remaining customers
    for (int c = 0; c < nc; ++c) {
        if (sol.customer_assignment[c] >= 0) continue;
        double best_cost = std::numeric_limits<double>::infinity();
        int best_w = -1;
        for (int w : inst_.eligible_warehouses[c]) {
            if (!sol.open_warehouses[w]) continue;
            double cost = inst_.wc_cost_matrix[w][c];
            if (cost < best_cost) {
                best_cost = cost;
                best_w = w;
            }
        }
        if (best_w >= 0) {
            sol.customer_assignment[c] = best_w;
            sol.warehouse_outbound[best_w] += inst_.customers[c].do_qty;
        }
    }

    // Evaluate initial solution
    engine.evaluate(sol);
    Solution best = sol;

    // Simple local search: try reassigning customers
    std::mt19937 rng(fixed_config.random_seed);
    for (int iter = 0; iter < fixed_config.max_iterations; ++iter) {
        Solution candidate = best;
        // Random customer swap
        int c = std::uniform_int_distribution<int>(0, nc - 1)(rng);
        if (inst_.customers[c].mapped_warehouse >= 0) continue;

        int current_w = candidate.customer_assignment[c];
        const auto& eligible = inst_.eligible_warehouses[c];
        if (eligible.size() <= 1) continue;

        int new_w = eligible[std::uniform_int_distribution<int>(0, static_cast<int>(eligible.size()) - 1)(rng)];
        if (new_w == current_w || !candidate.open_warehouses[new_w]) continue;

        candidate.warehouse_outbound[current_w] -= inst_.customers[c].do_qty;
        candidate.customer_assignment[c] = new_w;
        candidate.warehouse_outbound[new_w] += inst_.customers[c].do_qty;

        engine.evaluate(candidate);
        if (candidate.is_feasible &&
            (candidate.total_inbound > best.total_inbound ||
             (candidate.total_inbound == best.total_inbound &&
              candidate.total_cost < best.total_cost))) {
            best = candidate;
        }
    }

    auto end = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(end - start).count();

    SolverResult result;
    result.best_solution = best;
    result.elapsed_seconds = elapsed;
    result.iterations_performed = fixed_config.max_iterations;
    result.status = best.is_feasible ? "FEASIBLE" : "INFEASIBLE";

    return result;
}

}  // namespace n3t
