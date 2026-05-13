#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "data_model.h"
#include "solver.h"

namespace py = pybind11;

PYBIND11_MODULE(_solver_core, m) {
    m.doc() = "Network 3-Tier Optimizer C++ Core Engine";

    // ─── Data Model Bindings ──────────────────────────────────────────────────

    py::class_<n3t::Plant>(m, "Plant")
        .def(py::init<>())
        .def_readwrite("id", &n3t::Plant::id)
        .def_readwrite("ext_id", &n3t::Plant::ext_id)
        .def_readwrite("name", &n3t::Plant::name)
        .def_readwrite("product_qty", &n3t::Plant::product_qty)
        .def_readwrite("shipment_qty", &n3t::Plant::shipment_qty);

    py::class_<n3t::Warehouse>(m, "Warehouse")
        .def(py::init<>())
        .def_readwrite("id", &n3t::Warehouse::id)
        .def_readwrite("ext_id", &n3t::Warehouse::ext_id)
        .def_readwrite("name", &n3t::Warehouse::name)
        .def_readwrite("capacity_qty", &n3t::Warehouse::capacity_qty)
        .def_readwrite("fixed_cost", &n3t::Warehouse::fixed_cost)
        .def_readwrite("operation_cost", &n3t::Warehouse::operation_cost)
        .def_readwrite("active", &n3t::Warehouse::active);

    py::class_<n3t::Customer>(m, "Customer")
        .def(py::init<>())
        .def_readwrite("id", &n3t::Customer::id)
        .def_readwrite("ext_id", &n3t::Customer::ext_id)
        .def_readwrite("name", &n3t::Customer::name)
        .def_readwrite("do_qty", &n3t::Customer::do_qty)
        .def_readwrite("shipment_qty", &n3t::Customer::shipment_qty)
        .def_readwrite("mapped_warehouse", &n3t::Customer::mapped_warehouse);

    py::class_<n3t::PlantWarehouseArc>(m, "PlantWarehouseArc")
        .def(py::init<>())
        .def_readwrite("plant_idx", &n3t::PlantWarehouseArc::plant_idx)
        .def_readwrite("warehouse_idx", &n3t::PlantWarehouseArc::warehouse_idx)
        .def_readwrite("distance_km", &n3t::PlantWarehouseArc::distance_km)
        .def_readwrite("trns_cost", &n3t::PlantWarehouseArc::trns_cost);

    py::class_<n3t::WarehouseCustomerArc>(m, "WarehouseCustomerArc")
        .def(py::init<>())
        .def_readwrite("warehouse_idx", &n3t::WarehouseCustomerArc::warehouse_idx)
        .def_readwrite("customer_idx", &n3t::WarehouseCustomerArc::customer_idx)
        .def_readwrite("distance_km", &n3t::WarehouseCustomerArc::distance_km)
        .def_readwrite("trns_cost", &n3t::WarehouseCustomerArc::trns_cost);

    py::class_<n3t::ProblemInstance>(m, "ProblemInstance")
        .def(py::init<>())
        .def_readwrite("plants", &n3t::ProblemInstance::plants)
        .def_readwrite("warehouses", &n3t::ProblemInstance::warehouses)
        .def_readwrite("customers", &n3t::ProblemInstance::customers)
        .def_readwrite("pw_arcs", &n3t::ProblemInstance::pw_arcs)
        .def_readwrite("wc_arcs", &n3t::ProblemInstance::wc_arcs)
        .def_readwrite("warehouse_qty", &n3t::ProblemInstance::warehouse_qty)
        .def_readwrite("speed_kmh", &n3t::ProblemInstance::speed_kmh)
        .def_readwrite("coverage_hours", &n3t::ProblemInstance::coverage_hours)
        .def_readwrite("inventory_ratio", &n3t::ProblemInstance::inventory_ratio)
        .def("build_cost_matrices", &n3t::ProblemInstance::build_cost_matrices)
        .def("num_plants", &n3t::ProblemInstance::num_plants)
        .def("num_warehouses", &n3t::ProblemInstance::num_warehouses)
        .def("num_customers", &n3t::ProblemInstance::num_customers);

    // ─── Solution Bindings ────────────────────────────────────────────────────

    py::class_<n3t::Solution>(m, "Solution")
        .def(py::init<>())
        .def_readwrite("open_warehouses", &n3t::Solution::open_warehouses)
        .def_readwrite("customer_assignment", &n3t::Solution::customer_assignment)
        .def_readwrite("flows", &n3t::Solution::flows)
        .def_readwrite("total_inbound", &n3t::Solution::total_inbound)
        .def_readwrite("total_cost", &n3t::Solution::total_cost)
        .def_readwrite("warehouse_inbound", &n3t::Solution::warehouse_inbound)
        .def_readwrite("warehouse_outbound", &n3t::Solution::warehouse_outbound)
        .def_readwrite("is_feasible", &n3t::Solution::is_feasible);

    // ─── Solver Config Bindings ───────────────────────────────────────────────

    py::class_<n3t::LNSConfig>(m, "LNSConfig")
        .def(py::init<>())
        .def_readwrite("max_iterations", &n3t::LNSConfig::max_iterations)
        .def_readwrite("time_limit_sec", &n3t::LNSConfig::time_limit_sec)
        .def_readwrite("destroy_min_customers", &n3t::LNSConfig::destroy_min_customers)
        .def_readwrite("destroy_max_customers", &n3t::LNSConfig::destroy_max_customers)
        .def_readwrite("sa_initial_temp", &n3t::LNSConfig::sa_initial_temp)
        .def_readwrite("sa_cooling_rate", &n3t::LNSConfig::sa_cooling_rate)
        .def_readwrite("random_seed", &n3t::LNSConfig::random_seed);

    py::class_<n3t::SolverConfig>(m, "SolverConfig")
        .def(py::init<>())
        .def_readwrite("lns_config", &n3t::SolverConfig::lns_config)
        .def_readwrite("enable_inventory_capacity", &n3t::SolverConfig::enable_inventory_capacity);

    // ─── Solver Result Bindings ───────────────────────────────────────────────

    py::class_<n3t::SolverResult>(m, "SolverResult")
        .def(py::init<>())
        .def_readwrite("best_solution", &n3t::SolverResult::best_solution)
        .def_readwrite("elapsed_seconds", &n3t::SolverResult::elapsed_seconds)
        .def_readwrite("iterations_performed", &n3t::SolverResult::iterations_performed)
        .def_readwrite("status", &n3t::SolverResult::status);

    // ─── Solver Bindings ──────────────────────────────────────────────────────

    py::class_<n3t::Solver>(m, "Solver")
        .def(py::init<const n3t::ProblemInstance&, const n3t::SolverConfig&>())
        .def("solve", &n3t::Solver::solve, "Run LNS optimization for best model")
        .def("solve_fixed", &n3t::Solver::solve_fixed,
             py::arg("forced_open_warehouses"),
             "Run optimization with fixed warehouse set");
}
