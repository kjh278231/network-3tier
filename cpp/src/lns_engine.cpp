#include "lns_engine.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <numeric>

namespace n3t {

LNSEngine::LNSEngine(const ProblemInstance& instance, const LNSConfig& config)
    : inst_(instance),
      config_(config),
      checker_(instance),
      flow_solver_(instance),
      rng_(config.random_seed) {}

// ─── Initial Solution (Greedy) ────────────────────────────────────────────────

Solution LNSEngine::generate_initial_solution() {
    Solution sol;
    int nw = inst_.num_warehouses();
    int nc = inst_.num_customers();
    int np = inst_.num_plants();

    sol.open_warehouses.assign(nw, false);
    sol.customer_assignment.assign(nc, -1);
    sol.flows.assign(np, std::vector<int64_t>(nw, 0));
    sol.warehouse_inbound.assign(nw, 0);
    sol.warehouse_outbound.assign(nw, 0);

    // Step 1: Determine which warehouses must be open (mapping constraints)
    std::vector<int> forced_open;
    for (int c = 0; c < nc; ++c) {
        int mapped = inst_.customers[c].mapped_warehouse;
        if (mapped >= 0) {
            if (!sol.open_warehouses[mapped]) {
                sol.open_warehouses[mapped] = true;
                forced_open.push_back(mapped);
            }
            sol.customer_assignment[c] = mapped;
            sol.warehouse_outbound[mapped] += inst_.customers[c].do_qty;
        }
    }

    // Step 2: Open remaining warehouses greedily (by total eligible customer demand)
    int open_count = static_cast<int>(forced_open.size());
    int remaining_to_open = inst_.warehouse_qty - open_count;

    if (remaining_to_open > 0) {
        // Score each warehouse by total demand of eligible customers
        std::vector<std::pair<int64_t, int>> wh_scores;
        for (int w = 0; w < nw; ++w) {
            if (sol.open_warehouses[w]) continue;
            int64_t score = 0;
            for (int c = 0; c < nc; ++c) {
                const auto& eligible = inst_.eligible_warehouses[c];
                if (std::find(eligible.begin(), eligible.end(), w) != eligible.end()) {
                    score += inst_.customers[c].do_qty;
                }
            }
            wh_scores.push_back({score, w});
        }
        std::sort(wh_scores.rbegin(), wh_scores.rend());

        for (int i = 0; i < remaining_to_open && i < static_cast<int>(wh_scores.size()); ++i) {
            sol.open_warehouses[wh_scores[i].second] = true;
        }
    }

    // Step 3: Assign unassigned customers to cheapest eligible open warehouse
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

    // Step 4: Solve flow sub-problem
    evaluate(sol);

    return sol;
}

// ─── Destroy Operators ────────────────────────────────────────────────────────

std::vector<int> LNSEngine::destroy_random(Solution& sol) {
    int nc = inst_.num_customers();
    int k = std::uniform_int_distribution<int>(
        config_.destroy_min_customers,
        std::min(config_.destroy_max_customers, nc))(rng_);

    std::vector<int> candidates;
    for (int c = 0; c < nc; ++c) {
        // Don't destroy mapped customers
        if (inst_.customers[c].mapped_warehouse < 0) {
            candidates.push_back(c);
        }
    }

    std::shuffle(candidates.begin(), candidates.end(), rng_);
    k = std::min(k, static_cast<int>(candidates.size()));

    std::vector<int> removed(candidates.begin(), candidates.begin() + k);
    for (int c : removed) {
        int w = sol.customer_assignment[c];
        if (w >= 0) {
            sol.warehouse_outbound[w] -= inst_.customers[c].do_qty;
        }
        sol.customer_assignment[c] = -1;
    }

    return removed;
}

std::vector<int> LNSEngine::destroy_worst_cost(Solution& sol) {
    int nc = inst_.num_customers();
    int k = std::uniform_int_distribution<int>(
        config_.destroy_min_customers,
        std::min(config_.destroy_max_customers, nc))(rng_);

    // Compute per-customer cost contribution
    std::vector<std::pair<double, int>> costs;
    for (int c = 0; c < nc; ++c) {
        if (inst_.customers[c].mapped_warehouse >= 0) continue;
        int w = sol.customer_assignment[c];
        if (w < 0) continue;
        double cost = inst_.wc_cost_matrix[w][c] * inst_.customers[c].do_qty +
                      inst_.warehouses[w].operation_cost * inst_.customers[c].do_qty;
        costs.push_back({cost, c});
    }

    std::sort(costs.rbegin(), costs.rend());
    k = std::min(k, static_cast<int>(costs.size()));

    std::vector<int> removed;
    for (int i = 0; i < k; ++i) {
        int c = costs[i].second;
        int w = sol.customer_assignment[c];
        sol.warehouse_outbound[w] -= inst_.customers[c].do_qty;
        sol.customer_assignment[c] = -1;
        removed.push_back(c);
    }

    return removed;
}

std::vector<int> LNSEngine::destroy_warehouse(Solution& sol) {
    // Pick a random open warehouse (not forced by mapping) and remove all its customers
    std::vector<int> removable_warehouses;
    for (int w = 0; w < inst_.num_warehouses(); ++w) {
        if (!sol.open_warehouses[w]) continue;
        // Check if any mapped customer forces this warehouse
        bool forced = false;
        for (int c = 0; c < inst_.num_customers(); ++c) {
            if (inst_.customers[c].mapped_warehouse == w) {
                forced = true;
                break;
            }
        }
        if (!forced) removable_warehouses.push_back(w);
    }

    if (removable_warehouses.empty()) {
        return destroy_random(sol);
    }

    int w_remove = removable_warehouses[
        std::uniform_int_distribution<int>(0, removable_warehouses.size() - 1)(rng_)];

    // Remove all customers assigned to this warehouse
    std::vector<int> removed;
    for (int c = 0; c < inst_.num_customers(); ++c) {
        if (sol.customer_assignment[c] == w_remove) {
            sol.warehouse_outbound[w_remove] -= inst_.customers[c].do_qty;
            sol.customer_assignment[c] = -1;
            removed.push_back(c);
        }
    }

    // Close this warehouse and open a random alternative
    sol.open_warehouses[w_remove] = false;

    std::vector<int> closed_warehouses;
    for (int w = 0; w < inst_.num_warehouses(); ++w) {
        if (!sol.open_warehouses[w]) closed_warehouses.push_back(w);
    }

    if (!closed_warehouses.empty()) {
        int w_new = closed_warehouses[
            std::uniform_int_distribution<int>(0, closed_warehouses.size() - 1)(rng_)];
        sol.open_warehouses[w_new] = true;
    }

    return removed;
}

// ─── Repair Operators ─────────────────────────────────────────────────────────

bool LNSEngine::repair_greedy(Solution& sol, const std::vector<int>& removed) {
    for (int c : removed) {
        double best_cost = std::numeric_limits<double>::infinity();
        int best_w = -1;

        for (int w : inst_.eligible_warehouses[c]) {
            if (!sol.open_warehouses[w]) continue;
            // Quick capacity check
            if (sol.warehouse_outbound[w] + inst_.customers[c].do_qty >
                inst_.warehouses[w].capacity_qty) continue;

            double cost = inst_.wc_cost_matrix[w][c] * inst_.customers[c].do_qty +
                          inst_.warehouses[w].operation_cost * inst_.customers[c].do_qty;
            if (cost < best_cost) {
                best_cost = cost;
                best_w = w;
            }
        }

        if (best_w < 0) return false;  // Infeasible
        sol.customer_assignment[c] = best_w;
        sol.warehouse_outbound[best_w] += inst_.customers[c].do_qty;
    }
    return true;
}

bool LNSEngine::repair_regret(Solution& sol, const std::vector<int>& removed) {
    std::vector<int> unassigned = removed;

    while (!unassigned.empty()) {
        double max_regret = -std::numeric_limits<double>::infinity();
        int best_customer = -1;
        int best_warehouse = -1;

        for (int c : unassigned) {
            double best1 = std::numeric_limits<double>::infinity();
            double best2 = std::numeric_limits<double>::infinity();
            int best1_w = -1;

            for (int w : inst_.eligible_warehouses[c]) {
                if (!sol.open_warehouses[w]) continue;
                if (sol.warehouse_outbound[w] + inst_.customers[c].do_qty >
                    inst_.warehouses[w].capacity_qty) continue;

                double cost = inst_.wc_cost_matrix[w][c] * inst_.customers[c].do_qty +
                              inst_.warehouses[w].operation_cost * inst_.customers[c].do_qty;
                if (cost < best1) {
                    best2 = best1;
                    best1 = cost;
                    best1_w = w;
                } else if (cost < best2) {
                    best2 = cost;
                }
            }

            if (best1_w < 0) return false;  // Infeasible

            double regret = best2 - best1;
            if (best2 == std::numeric_limits<double>::infinity()) {
                regret = 1e12;  // Only one option: highest priority
            }

            if (regret > max_regret) {
                max_regret = regret;
                best_customer = c;
                best_warehouse = best1_w;
            }
        }

        if (best_customer < 0) return false;

        sol.customer_assignment[best_customer] = best_warehouse;
        sol.warehouse_outbound[best_warehouse] += inst_.customers[best_customer].do_qty;
        unassigned.erase(
            std::find(unassigned.begin(), unassigned.end(), best_customer));
    }
    return true;
}

// ─── Evaluation ───────────────────────────────────────────────────────────────

void LNSEngine::evaluate(Solution& sol) {
    auto flow_result = flow_solver_.solve(sol.open_warehouses, sol.customer_assignment);

    sol.flows = flow_result.flows;
    sol.total_inbound = flow_result.total_inbound;
    sol.is_feasible = flow_result.feasible;

    // Update warehouse inbound
    sol.warehouse_inbound.assign(inst_.num_warehouses(), 0);
    for (int p = 0; p < inst_.num_plants(); ++p) {
        for (int w = 0; w < inst_.num_warehouses(); ++w) {
            sol.warehouse_inbound[w] += sol.flows[p][w];
        }
    }

    // Compute total cost
    double total_cost = 0.0;

    // Fixed cost
    for (int w = 0; w < inst_.num_warehouses(); ++w) {
        if (sol.open_warehouses[w]) {
            total_cost += inst_.warehouses[w].fixed_cost;
        }
    }

    // Plant->Warehouse transport cost
    total_cost += flow_result.total_transport_cost;

    // Warehouse->Customer transport cost + operation cost
    for (int c = 0; c < inst_.num_customers(); ++c) {
        int w = sol.customer_assignment[c];
        if (w < 0) continue;
        double do_qty = static_cast<double>(inst_.customers[c].do_qty);
        total_cost += inst_.wc_cost_matrix[w][c] * do_qty;
        total_cost += inst_.warehouses[w].operation_cost * do_qty;
    }

    sol.total_cost = total_cost;
    sol.is_feasible = checker_.is_feasible(sol);
}

// ─── Acceptance (Simulated Annealing) ─────────────────────────────────────────

bool LNSEngine::accept(double current_cost, double new_cost, double temperature) {
    if (new_cost < current_cost) return true;
    double delta = new_cost - current_cost;
    double prob = std::exp(-delta / temperature);
    return std::uniform_real_distribution<double>(0.0, 1.0)(rng_) < prob;
}

// ─── Update Warehouse Aggregates ──────────────────────────────────────────────

void LNSEngine::update_warehouse_aggregates(Solution& sol) {
    sol.warehouse_outbound.assign(inst_.num_warehouses(), 0);
    for (int c = 0; c < inst_.num_customers(); ++c) {
        int w = sol.customer_assignment[c];
        if (w >= 0) {
            sol.warehouse_outbound[w] += inst_.customers[c].do_qty;
        }
    }
}

// ─── Main LNS Loop ───────────────────────────────────────────────────────────

Solution LNSEngine::solve() {
    auto start_time = std::chrono::steady_clock::now();

    // Generate initial solution
    Solution best = generate_initial_solution();
    Solution current = best;

    double temperature = config_.sa_initial_temp;
    int iterations = 0;

    while (iterations < config_.max_iterations) {
        // Check time limit
        auto now = std::chrono::steady_clock::now();
        double elapsed = std::chrono::duration<double>(now - start_time).count();
        if (elapsed >= config_.time_limit_sec) break;

        // Create a copy of current solution
        Solution candidate = current;

        // Select destroy operator
        std::vector<int> removed;
        int op = std::uniform_int_distribution<int>(0, 2)(rng_);
        switch (op) {
            case 0: removed = destroy_random(candidate); break;
            case 1: removed = destroy_worst_cost(candidate); break;
            case 2: removed = destroy_warehouse(candidate); break;
        }

        // Select repair operator
        bool repaired = false;
        if (std::uniform_int_distribution<int>(0, 1)(rng_) == 0) {
            repaired = repair_greedy(candidate, removed);
        } else {
            repaired = repair_regret(candidate, removed);
        }

        if (!repaired) {
            ++iterations;
            temperature *= config_.sa_cooling_rate;
            continue;
        }

        // Evaluate candidate
        evaluate(candidate);

        if (!candidate.is_feasible) {
            ++iterations;
            temperature *= config_.sa_cooling_rate;
            continue;
        }

        // Acceptance criterion (hierarchical: inbound first, then cost)
        bool accepted = false;
        if (candidate.total_inbound > current.total_inbound) {
            accepted = true;
        } else if (candidate.total_inbound == current.total_inbound) {
            accepted = accept(current.total_cost, candidate.total_cost, temperature);
        }

        if (accepted) {
            current = candidate;

            // Update best
            if (current.total_inbound > best.total_inbound ||
                (current.total_inbound == best.total_inbound &&
                 current.total_cost < best.total_cost)) {
                best = current;
            }
        }

        temperature *= config_.sa_cooling_rate;
        ++iterations;
    }

    return best;
}

}  // namespace n3t
