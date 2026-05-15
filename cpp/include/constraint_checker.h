#pragma once

#include "data_model.h"

namespace n3t {

// ─── Constraint Checker ───────────────────────────────────────────────────────
// Fast feasibility checks for a given solution against the problem instance.

class ConstraintChecker {
public:
    explicit ConstraintChecker(const ProblemInstance& instance);

    // Full feasibility check
    bool is_feasible(const Solution& sol) const;

    // Individual constraint checks
    bool check_single_assignment(const Solution& sol) const;
    bool check_warehouse_count(const Solution& sol) const;
    bool check_capacity(const Solution& sol) const;
    bool check_inventory_capacity(const Solution& sol) const;
    bool check_plant_supply(const Solution& sol) const;
    bool check_mapping_constraints(const Solution& sol) const;
    bool check_inbound_geq_outbound(const Solution& sol) const;
    bool check_min_one_customer(const Solution& sol) const;

    // Incremental: check if reassigning customer c to warehouse w is feasible
    bool can_assign(const Solution& sol, int customer_idx, int warehouse_idx) const;

private:
    const ProblemInstance& inst_;
};

}  // namespace n3t
