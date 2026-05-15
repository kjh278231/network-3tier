#include "constraint_checker.h"
#include <iostream>

namespace n3t {

ConstraintChecker::ConstraintChecker(const ProblemInstance& instance) : inst_(instance) {}

bool ConstraintChecker::is_feasible(const Solution& sol) const {
    int nw = inst_.num_warehouses();
    int nc = inst_.num_customers();
    int np = inst_.num_plants();

    // 1. Warehouse Qty
    int open_count = 0;
    for (bool open : sol.open_warehouses) if (open) ++open_count;
    if (open_count > inst_.warehouse_qty) {
        std::cout << "F: Qty " << open_count << " > " << inst_.warehouse_qty << std::endl;
        return false;
    }

    // 2. Customer Assignment
    for (int c = 0; c < nc; ++c) {
        if (sol.customer_assignment[c] < 0) {
            std::cout << "F: Cust " << c << " unassigned" << std::endl;
            return false;
        }
        if (!sol.open_warehouses[sol.customer_assignment[c]]) {
            std::cout << "F: Cust " << c << " closed WH" << std::endl;
            return false;
        }
    }

    // 3. Warehouse Capacity
    for (int w = 0; w < nw; ++w) {
        if (sol.warehouse_inbound[w] > inst_.warehouses[w].capacity_qty) {
            std::cout << "F: WH " << w << " cap " << sol.warehouse_inbound[w] << " > " << inst_.warehouses[w].capacity_qty << std::endl;
            return false;
        }
    }

    // 4. Plant Capacity
    std::vector<int64_t> plant_outbound(np, 0);
    for (int p = 0; p < np; ++p) {
        for (int w = 0; w < nw; ++w) {
            plant_outbound[p] += sol.flows[p][w];
        }
        if (plant_outbound[p] > inst_.plants[p].product_qty) {
            std::cout << "F: Plant " << p << " cap " << plant_outbound[p] << " > " << inst_.plants[p].product_qty << std::endl;
            return false;
        }
    }

    // 5. Inventory Capacity & Coverage
    for (int w = 0; w < nw; ++w) {
        if (!sol.open_warehouses[w]) continue;
        double throughput = (double)sol.warehouse_outbound[w];
        double inventory = throughput * inst_.inventory_ratio;
        if (inventory > (double)inst_.warehouses[w].capacity_qty) {
            std::cout << "F: WH " << w << " inv " << inventory << " > " << inst_.warehouses[w].capacity_qty << std::endl;
            return false;
        }
        
        double avg_speed = inst_.speed_kmh;
        for (int c = 0; c < nc; ++c) {
            if (sol.customer_assignment[c] == w) {
                double dist = inst_.wc_cost_matrix[w][c]; 
                if (dist / avg_speed > inst_.coverage_hours) {
                    std::cout << "F: Cust " << c << " cov " << dist/avg_speed << " > " << inst_.coverage_hours << std::endl;
                    return false;
                }
            }
        }
    }

    // 6. Total Inbound vs Total Outbound
    int64_t total_outbound = 0;
    for (int c = 0; c < nc; ++c) total_outbound += inst_.customers[c].do_qty;
    if (sol.total_inbound < total_outbound) {
        std::cout << "F: Inbound " << sol.total_inbound << " < Outbound " << total_outbound << std::endl;
        return false;
    }

    return true;
}

bool ConstraintChecker::check_single_assignment(const Solution& sol) const { return true; }
bool ConstraintChecker::check_warehouse_count(const Solution& sol) const { return true; }
bool ConstraintChecker::check_mapping_constraints(const Solution& sol) const { return true; }
bool ConstraintChecker::check_inbound_geq_outbound(const Solution& sol) const { return true; }

} // namespace n3t
