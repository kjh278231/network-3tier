#include "data_model.h"
#include <limits>

namespace n3t {

void ProblemInstance::build_cost_matrices() {
    const double INF = std::numeric_limits<double>::infinity();
    int np = num_plants();
    int nw = num_warehouses();
    int nc = num_customers();

    // Initialize cost matrices with INF (no arc)
    pw_cost_matrix.assign(np, std::vector<double>(nw, INF));
    wc_cost_matrix.assign(nw, std::vector<double>(nc, INF));

    // Fill plant-warehouse cost matrix
    for (const auto& arc : pw_arcs) {
        pw_cost_matrix[arc.plant_idx][arc.warehouse_idx] = arc.trns_cost;
    }

    // Fill warehouse-customer cost matrix
    for (const auto& arc : wc_arcs) {
        wc_cost_matrix[arc.warehouse_idx][arc.customer_idx] = arc.trns_cost;
    }

    // Build eligible warehouses per customer
    eligible_warehouses.assign(nc, std::vector<int>());
    for (const auto& arc : wc_arcs) {
        eligible_warehouses[arc.customer_idx].push_back(arc.warehouse_idx);
    }
}

}  // namespace n3t
