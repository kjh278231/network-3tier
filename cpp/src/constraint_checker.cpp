#include "constraint_checker.h"
#include <algorithm>
#include <numeric>

namespace n3t {

ConstraintChecker::ConstraintChecker(const ProblemInstance& instance)
    : inst_(instance) {}

bool ConstraintChecker::is_feasible(const Solution& sol) const {
    return check_single_assignment(sol) &&
           check_warehouse_count(sol) &&
           check_mapping_constraints(sol) &&
           check_min_one_customer(sol) &&
           check_capacity(sol) &&
           check_inbound_geq_outbound(sol) &&
           check_inventory_capacity(sol) &&
           check_plant_supply(sol);
}

bool ConstraintChecker::check_single_assignment(const Solution& sol) const {
    for (int c = 0; c < inst_.num_customers(); ++c) {
        int w = sol.customer_assignment[c];
        if (w < 0 || w >= inst_.num_warehouses()) return false;
        if (!sol.open_warehouses[w]) return false;
    }
    return true;
}

bool ConstraintChecker::check_warehouse_count(const Solution& sol) const {
    int count = 0;
    for (bool open : sol.open_warehouses) {
        if (open) ++count;
    }
    return count == inst_.warehouse_qty;
}

bool ConstraintChecker::check_capacity(const Solution& sol) const {
    for (int w = 0; w < inst_.num_warehouses(); ++w) {
        if (!sol.open_warehouses[w]) continue;
        if (sol.warehouse_inbound[w] > inst_.warehouses[w].capacity_qty) {
            return false;
        }
    }
    return true;
}

bool ConstraintChecker::check_inventory_capacity(const Solution& sol) const {
    for (int w = 0; w < inst_.num_warehouses(); ++w) {
        if (!sol.open_warehouses[w]) continue;
        int64_t inventory = sol.warehouse_inbound[w] - sol.warehouse_outbound[w];
        int64_t inv_cap = static_cast<int64_t>(
            inst_.warehouses[w].capacity_qty * inst_.inventory_ratio);
        if (inventory > inv_cap) {
            return false;
        }
    }
    return true;
}

bool ConstraintChecker::check_plant_supply(const Solution& sol) const {
    for (int p = 0; p < inst_.num_plants(); ++p) {
        int64_t total_out = 0;
        for (int w = 0; w < inst_.num_warehouses(); ++w) {
            total_out += sol.flows[p][w];
        }
        if (total_out > inst_.plants[p].product_qty) {
            return false;
        }
    }
    return true;
}

bool ConstraintChecker::check_mapping_constraints(const Solution& sol) const {
    for (int c = 0; c < inst_.num_customers(); ++c) {
        int mapped = inst_.customers[c].mapped_warehouse;
        if (mapped >= 0) {
            if (sol.customer_assignment[c] != mapped) return false;
            if (!sol.open_warehouses[mapped]) return false;
        }
    }
    return true;
}

bool ConstraintChecker::check_inbound_geq_outbound(const Solution& sol) const {
    for (int w = 0; w < inst_.num_warehouses(); ++w) {
        if (!sol.open_warehouses[w]) continue;
        if (sol.warehouse_inbound[w] < sol.warehouse_outbound[w]) {
            return false;
        }
    }
    return true;
}

bool ConstraintChecker::check_min_one_customer(const Solution& sol) const {
    std::vector<int> customer_count(inst_.num_warehouses(), 0);
    for (int c = 0; c < inst_.num_customers(); ++c) {
        int w = sol.customer_assignment[c];
        if (w >= 0) ++customer_count[w];
    }
    for (int w = 0; w < inst_.num_warehouses(); ++w) {
        if (sol.open_warehouses[w] && customer_count[w] == 0) {
            return false;
        }
    }
    return true;
}

bool ConstraintChecker::can_assign(const Solution& sol, int customer_idx, int warehouse_idx) const {
    // Check if warehouse is open
    if (!sol.open_warehouses[warehouse_idx]) return false;

    // Check if this customer is eligible for this warehouse
    const auto& eligible = inst_.eligible_warehouses[customer_idx];
    if (std::find(eligible.begin(), eligible.end(), warehouse_idx) == eligible.end()) {
        return false;
    }

    // Check mapping constraint
    int mapped = inst_.customers[customer_idx].mapped_warehouse;
    if (mapped >= 0 && mapped != warehouse_idx) return false;

    // Check capacity (quick estimate: current outbound + this customer's demand <= capacity)
    int64_t new_outbound = sol.warehouse_outbound[warehouse_idx] +
                           inst_.customers[customer_idx].do_qty;
    if (new_outbound > inst_.warehouses[warehouse_idx].capacity_qty) {
        return false;
    }

    return true;
}

}  // namespace n3t
