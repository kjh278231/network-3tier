#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace n3t {

// ─── Entity Structures ────────────────────────────────────────────────────────

struct Plant {
    int id;              // internal index
    std::string ext_id;  // external ID from spreadsheet
    std::string name;
    int64_t product_qty;
    int64_t shipment_qty;
};

struct Warehouse {
    int id;
    std::string ext_id;
    std::string name;
    int64_t capacity_qty;       // throughput capacity
    double fixed_cost;
    double operation_cost;
    bool active;
};

struct Customer {
    int id;
    std::string ext_id;
    std::string name;
    int64_t do_qty;             // demand
    int64_t shipment_qty;
    int mapped_warehouse;       // -1 if no mapping
};

// ─── Cost Arc Structures ──────────────────────────────────────────────────────

struct PlantWarehouseArc {
    int plant_idx;
    int warehouse_idx;
    double distance_km;
    double trns_cost;
};

struct WarehouseCustomerArc {
    int warehouse_idx;
    int customer_idx;
    double distance_km;
    double trns_cost;
};

// ─── Problem Instance ─────────────────────────────────────────────────────────

struct ProblemInstance {
    std::vector<Plant> plants;
    std::vector<Warehouse> warehouses;
    std::vector<Customer> customers;

    // Cost arcs
    std::vector<PlantWarehouseArc> pw_arcs;
    std::vector<WarehouseCustomerArc> wc_arcs;

    // Fast lookup: pw_cost_matrix[plant_idx][warehouse_idx] = trns_cost
    std::vector<std::vector<double>> pw_cost_matrix;
    // wc_cost_matrix[warehouse_idx][customer_idx] = trns_cost
    std::vector<std::vector<double>> wc_cost_matrix;

    // Eligible warehouses per customer: eligible_warehouses[customer_idx] = {wh_idx, ...}
    std::vector<std::vector<int>> eligible_warehouses;

    // Simulation parameters
    int warehouse_qty;          // number of warehouses to open
    double speed_kmh;
    double coverage_hours;
    double inventory_ratio;     // default 0.3

    // Derived
    int num_plants() const { return static_cast<int>(plants.size()); }
    int num_warehouses() const { return static_cast<int>(warehouses.size()); }
    int num_customers() const { return static_cast<int>(customers.size()); }

    // Build cost matrices from arcs
    void build_cost_matrices();
};

// ─── Solution Representation ──────────────────────────────────────────────────

struct Solution {
    std::vector<bool> open_warehouses;          // size = num_warehouses
    std::vector<int> customer_assignment;       // size = num_customers, value = warehouse_idx
    std::vector<std::vector<int64_t>> flows;    // flows[plant_idx][warehouse_idx]

    // Cached objective values
    int64_t total_inbound;
    double total_cost;

    // Per-warehouse aggregates
    std::vector<int64_t> warehouse_inbound;     // sum of flows into each warehouse
    std::vector<int64_t> warehouse_outbound;    // sum of customer demand assigned

    bool is_feasible;

    Solution() : total_inbound(0), total_cost(0.0), is_feasible(false) {}
};

}  // namespace n3t
