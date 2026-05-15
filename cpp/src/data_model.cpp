#include "data_model.h"
#include <cmath>
#include <algorithm>
#include <limits>

namespace n3t {

void ProblemInstance::build_cost_matrices() {
    int nw = num_warehouses();
    int nc = num_customers();
    int np = num_plants();

    pw_cost_matrix.assign(np, std::vector<double>(nw, std::numeric_limits<double>::infinity()));
    for (const auto& arc : pw_arcs) {
        if (arc.plant_idx < np && arc.warehouse_idx < nw) {
            pw_cost_matrix[arc.plant_idx][arc.warehouse_idx] = arc.trns_cost;
        }
    }

    wc_cost_matrix.assign(nw, std::vector<double>(nc, std::numeric_limits<double>::infinity()));
    for (const auto& arc : wc_arcs) {
        if (arc.warehouse_idx < nw && arc.customer_idx < nc) {
            wc_cost_matrix[arc.warehouse_idx][arc.customer_idx] = arc.trns_cost;
        }
    }

    eligible_warehouses.assign(nc, std::vector<int>());
    for (int c = 0; c < nc; ++c) {
        for (int w = 0; w < nw; ++w) {
            if (wc_cost_matrix[w][c] != std::numeric_limits<double>::infinity()) {
                eligible_warehouses[c].push_back(w);
            }
        }
    }
}

}  // namespace n3t
