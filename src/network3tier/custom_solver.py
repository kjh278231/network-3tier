"""
Custom C++ Solver adapter for the Network 3-Tier Optimizer.

This module provides a Python interface to the C++ LNS-based solver engine.
It translates the NetworkData domain objects into the C++ ProblemInstance format,
invokes the C++ solver, and translates results back into CaseResult objects.
"""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from .domain import CaseResult, NetworkData
from .loader import get_customer_mapping_requirements
from .logging_utils import get_logger

LOGGER = get_logger()

# Try to import the C++ extension module
try:
    from . import _solver_core
    CPP_SOLVER_AVAILABLE = True
except ImportError:
    CPP_SOLVER_AVAILABLE = False
    LOGGER.warning("C++ solver extension not available. Build with CMake first.")


def _build_problem_instance(
    data: NetworkData,
    forced_open_warehouses: Optional[set[str]] = None,
) -> tuple:
    """Convert NetworkData into C++ ProblemInstance and index mappings."""
    if not CPP_SOLVER_AVAILABLE:
        raise RuntimeError("C++ solver extension not built. Run CMake build first.")

    plants_df = data.plants[["Plant ID", "Product Qty", "Shipment Qty", "Location Name"]].copy()
    warehouses_df = data.warehouses[
        data.warehouses["Active Y/N"] == "Y"
    ][["Warehouse ID", "Capacity Qty", "Fixed Cost", "Operation Cost", "Location Name"]].copy()

    if forced_open_warehouses is not None:
        warehouses_df = warehouses_df[
            warehouses_df["Warehouse ID"].isin(forced_open_warehouses)
        ].reset_index(drop=True)

    customers_df = data.customers[["Customer ID", "Do Qty", "Shipment Qty", "Location Name"]].copy()

    valid_wh_ids = set(warehouses_df["Warehouse ID"])
    pw_df = data.plant_warehouse_cost[
        data.plant_warehouse_cost["Warehouse ID"].isin(valid_wh_ids)
    ][["Plant ID", "Warehouse ID", "Distance (km)", "Trns Cost"]].copy()
    wc_df = data.warehouse_customer_cost[
        data.warehouse_customer_cost["Warehouse ID"].isin(valid_wh_ids)
    ][["Warehouse ID", "Customer ID", "Distance (km)", "Trns Cost"]].copy()

    # Build index mappings
    plant_id_to_idx = {pid: i for i, pid in enumerate(plants_df["Plant ID"])}
    wh_id_to_idx = {wid: i for i, wid in enumerate(warehouses_df["Warehouse ID"])}
    cust_id_to_idx = {cid: i for i, cid in enumerate(customers_df["Customer ID"])}

    # Reverse mappings
    idx_to_plant_id = {i: pid for pid, i in plant_id_to_idx.items()}
    idx_to_wh_id = {i: wid for wid, i in wh_id_to_idx.items()}
    idx_to_cust_id = {i: cid for cid, i in cust_id_to_idx.items()}

    # Build C++ ProblemInstance
    instance = _solver_core.ProblemInstance()

    # Plants
    for _, row in plants_df.iterrows():
        p = _solver_core.Plant()
        p.id = plant_id_to_idx[row["Plant ID"]]
        p.ext_id = str(row["Plant ID"])
        p.name = str(row["Location Name"])
        p.product_qty = int(row["Product Qty"])
        p.shipment_qty = int(row["Shipment Qty"])
        instance.plants.append(p)

    # Warehouses
    for _, row in warehouses_df.iterrows():
        w = _solver_core.Warehouse()
        w.id = wh_id_to_idx[row["Warehouse ID"]]
        w.ext_id = str(row["Warehouse ID"])
        w.name = str(row["Location Name"])
        w.capacity_qty = int(row["Capacity Qty"])
        w.fixed_cost = float(row["Fixed Cost"])
        w.operation_cost = float(row["Operation Cost"])
        w.active = True
        instance.warehouses.append(w)

    # Customers
    customer_mapping = get_customer_mapping_requirements(data)
    for _, row in customers_df.iterrows():
        c = _solver_core.Customer()
        c.id = cust_id_to_idx[row["Customer ID"]]
        c.ext_id = str(row["Customer ID"])
        c.name = str(row["Location Name"])
        c.do_qty = int(row["Do Qty"])
        c.shipment_qty = int(row["Shipment Qty"])
        mapped_wh = customer_mapping.get(row["Customer ID"])
        c.mapped_warehouse = wh_id_to_idx[mapped_wh] if mapped_wh and mapped_wh in wh_id_to_idx else -1
        instance.customers.append(c)

    # Plant-Warehouse arcs
    for _, row in pw_df.iterrows():
        arc = _solver_core.PlantWarehouseArc()
        arc.plant_idx = plant_id_to_idx[row["Plant ID"]]
        arc.warehouse_idx = wh_id_to_idx[row["Warehouse ID"]]
        arc.distance_km = float(row["Distance (km)"])
        arc.trns_cost = float(row["Trns Cost"])
        instance.pw_arcs.append(arc)

    # Warehouse-Customer arcs
    for _, row in wc_df.iterrows():
        arc = _solver_core.WarehouseCustomerArc()
        arc.warehouse_idx = wh_id_to_idx[row["Warehouse ID"]]
        arc.customer_idx = cust_id_to_idx[row["Customer ID"]]
        arc.distance_km = float(row["Distance (km)"])
        arc.trns_cost = float(row["Trns Cost"])
        instance.wc_arcs.append(arc)

    # Simulation parameters
    instance.warehouse_qty = data.simulation.warehouse_qty
    instance.speed_kmh = data.simulation.speed_kmh
    instance.coverage_hours = data.simulation.coverage_hours
    instance.inventory_ratio = 0.3

    instance.build_cost_matrices()

    mappings = {
        "plant_id_to_idx": plant_id_to_idx,
        "wh_id_to_idx": wh_id_to_idx,
        "cust_id_to_idx": cust_id_to_idx,
        "idx_to_plant_id": idx_to_plant_id,
        "idx_to_wh_id": idx_to_wh_id,
        "idx_to_cust_id": idx_to_cust_id,
    }

    return instance, mappings


def solve_case_cpp(
    data: NetworkData,
    case_name: str,
    case_type: str,
    forced_open_warehouses: Optional[set[str]] = None,
    enable_inventory_capacity: bool = True,
    max_iterations: int = 10000,
    time_limit_sec: float = 60.0,
    random_seed: int = 42,
) -> CaseResult:
    """
    Solve a case using the C++ LNS-based solver.

    This is a drop-in replacement for solve_case() in optimizer.py.
    """
    LOGGER.info("Solving case '%s' (%s) with C++ solver", case_name, case_type)

    instance, mappings = _build_problem_instance(data, forced_open_warehouses)

    # Configure solver
    config = _solver_core.SolverConfig()
    config.lns_config.max_iterations = max_iterations
    config.lns_config.time_limit_sec = time_limit_sec
    config.lns_config.random_seed = random_seed
    config.enable_inventory_capacity = enable_inventory_capacity

    # Run solver
    solver = _solver_core.Solver(instance, config)

    if forced_open_warehouses is not None:
        forced_indices = [mappings["wh_id_to_idx"][wid] for wid in forced_open_warehouses]
        result = solver.solve_fixed(forced_indices)
    else:
        result = solver.solve()

    LOGGER.info(
        "C++ solver finished: status=%s, inbound=%d, cost=%.2f, time=%.3fs",
        result.status,
        result.best_solution.total_inbound,
        result.best_solution.total_cost,
        result.elapsed_seconds,
    )

    if result.status == "INFEASIBLE":
        raise RuntimeError(f"C++ solver returned INFEASIBLE for case '{case_name}'")

    # Convert solution back to domain objects
    sol = result.best_solution
    return _build_case_result(data, sol, mappings, case_name, case_type)


def _build_case_result(
    data: NetworkData,
    sol,
    mappings: dict,
    case_name: str,
    case_type: str,
) -> CaseResult:
    """Convert C++ Solution back into a CaseResult with all required DataFrames."""
    idx_to_plant_id = mappings["idx_to_plant_id"]
    idx_to_wh_id = mappings["idx_to_wh_id"]
    idx_to_cust_id = mappings["idx_to_cust_id"]

    selected_warehouses = sorted([
        idx_to_wh_id[w] for w in range(len(sol.open_warehouses)) if sol.open_warehouses[w]
    ])

    warehouse_lookup = data.warehouses.set_index("Warehouse ID")
    pw_lookup = data.plant_warehouse_cost.set_index(["Plant ID", "Warehouse ID"])
    wc_lookup = data.warehouse_customer_cost.set_index(["Warehouse ID", "Customer ID"])
    customer_lookup = data.customers.set_index("Customer ID")
    plant_lookup = data.plants.set_index("Plant ID")
    speed_kmh = data.simulation.speed_kmh
    coverage_hours = data.simulation.coverage_hours

    # Build plant-warehouse routes
    plant_warehouse_rows = []
    inbound_qty_by_warehouse = {w: 0.0 for w in selected_warehouses}
    inbound_cost_total = 0.0
    inbound_leadtime_total_sec = 0.0
    plant_warehouse_leadtime_by_warehouse = {}

    for p_idx in range(len(sol.flows)):
        for w_idx in range(len(sol.flows[p_idx])):
            do_qty = float(sol.flows[p_idx][w_idx])
            if do_qty <= 1e-6:
                continue
            p_id = idx_to_plant_id[p_idx]
            w_id = idx_to_wh_id[w_idx]
            inbound_qty_by_warehouse[w_id] = inbound_qty_by_warehouse.get(w_id, 0.0) + do_qty
            distance_km = float(pw_lookup.loc[(p_id, w_id), "Distance (km)"])
            plant_shipment_qty = float(plant_lookup.loc[p_id, "Shipment Qty"])
            trips_ratio = do_qty / plant_shipment_qty if plant_shipment_qty else 0.0
            leadtime_sec = ((distance_km / speed_kmh) * trips_ratio * 3600.0) if speed_kmh else math.inf
            cost = do_qty * float(pw_lookup.loc[(p_id, w_id), "Trns Cost"])
            plant_warehouse_leadtime_by_warehouse[w_id] = leadtime_sec
            inbound_cost_total += cost
            inbound_leadtime_total_sec += leadtime_sec
            plant_warehouse_rows.append({
                "Plant Id": p_id,
                "Plant Location Name": plant_lookup.loc[p_id, "Location Name"],
                "Warehouse Id": w_id,
                "Warehouse Location Name": warehouse_lookup.loc[w_id, "Location Name"],
                "Do Qty": do_qty,
                "Cost": cost,
                "Shipment Qty Ratio": trips_ratio,
                "Lead Time (Sec.)": leadtime_sec,
                "Distance (km)": distance_km,
                "Carbon Emission(tCO2-eq)": 0.0,
            })

    # Build warehouse-customer routes
    warehouse_customer_rows = []
    coverage_rows = []
    outbound_qty_by_warehouse = {w: 0.0 for w in selected_warehouses}
    outbound_cost_total = 0.0
    operation_cost_total = 0.0
    outbound_leadtime_total_sec = 0.0

    for c_idx in range(len(sol.customer_assignment)):
        w_idx = sol.customer_assignment[c_idx]
        if w_idx < 0:
            continue
        c_id = idx_to_cust_id[c_idx]
        w_id = idx_to_wh_id[w_idx]
        do_qty = float(customer_lookup.loc[c_id, "Do Qty"])
        outbound_qty_by_warehouse[w_id] = outbound_qty_by_warehouse.get(w_id, 0.0) + do_qty
        distance_km = float(wc_lookup.loc[(w_id, c_id), "Distance (km)"])
        customer_shipment_qty = float(customer_lookup.loc[c_id, "Shipment Qty"])
        one_way_time_sec = ((distance_km / speed_kmh) * 3600.0) if speed_kmh else math.inf
        route_leadtime_sec = ((distance_km / speed_kmh) * customer_shipment_qty * 3600.0) if speed_kmh else math.inf
        within_coverage = one_way_time_sec <= coverage_hours * 3600.0
        route_cost = do_qty * float(wc_lookup.loc[(w_id, c_id), "Trns Cost"])
        operation_cost = do_qty * float(warehouse_lookup.loc[w_id, "Operation Cost"])
        outbound_cost_total += route_cost
        operation_cost_total += operation_cost
        outbound_leadtime_total_sec += route_leadtime_sec

        warehouse_customer_rows.append({
            "Warehouse Id": w_id,
            "Warehouse Location Name": warehouse_lookup.loc[w_id, "Location Name"],
            "Customer Id": c_id,
            "Customer Location Name": customer_lookup.loc[c_id, "Location Name"],
            "Do Qty": do_qty,
            "Cost": route_cost,
            "Shipment Qty": customer_shipment_qty,
            "Lead Time (Sec.)": route_leadtime_sec,
            "Distance (km)": distance_km,
            "One-way Time (Sec.)": one_way_time_sec,
            "Coverage YN": "Y" if within_coverage else "N",
            "Operation Cost": operation_cost,
            "Carbon Emission(tCO2-eq)": 0.0,
        })
        coverage_rows.append({
            "Warehouse Id": w_id,
            "Customer Id": c_id,
            "Assigned Do Qty": do_qty,
            "Customer Shipment Qty": customer_shipment_qty,
            "Plant-Warehouse Lead Time (Sec.)": plant_warehouse_leadtime_by_warehouse.get(w_id, 0.0),
            "Warehouse-Customer Lead Time (Sec.)": route_leadtime_sec,
            "Total Lead Time (Sec.)": plant_warehouse_leadtime_by_warehouse.get(w_id, 0.0) + route_leadtime_sec,
            "Coverage Hour": coverage_hours,
            "One-way Time (Sec.)": one_way_time_sec,
            "Coverage YN": "Y" if within_coverage else "N",
        })

    plant_warehouse_df = pd.DataFrame(plant_warehouse_rows).sort_values(
        ["Plant Id", "Warehouse Id"], ignore_index=True) if plant_warehouse_rows else pd.DataFrame()
    warehouse_customer_df = pd.DataFrame(warehouse_customer_rows).sort_values(
        ["Warehouse Id", "Customer Id"], ignore_index=True) if warehouse_customer_rows else pd.DataFrame()
    coverage_detail_df = pd.DataFrame(coverage_rows).sort_values(
        ["Warehouse Id", "Customer Id"], ignore_index=True) if coverage_rows else pd.DataFrame()

    # Build warehouse summary
    inventory_capacity_by_warehouse = {
        w: float(warehouse_lookup.loc[w, "Capacity Qty"]) * 0.3 for w in selected_warehouses
    }
    warehouse_summary_rows = []
    for w in selected_warehouses:
        inbound_qty = inbound_qty_by_warehouse.get(w, 0.0)
        outbound_qty = outbound_qty_by_warehouse.get(w, 0.0)
        inventory_qty = inbound_qty - outbound_qty
        inventory_capacity = inventory_capacity_by_warehouse[w]
        warehouse_summary_rows.append({
            "Warehouse Id": w,
            "Warehouse Location Name": warehouse_lookup.loc[w, "Location Name"],
            "Inbound Qty": inbound_qty,
            "Outbound Qty": outbound_qty,
            "Inventory Qty": inventory_qty,
            "Throughput Capacity Qty": float(warehouse_lookup.loc[w, "Capacity Qty"]),
            "Inventory Capacity Qty": inventory_capacity,
            "Inventory Utilization (%)": (inventory_qty / inventory_capacity * 100.0) if inventory_capacity else 0.0,
            "Fixed Cost": float(warehouse_lookup.loc[w, "Fixed Cost"]),
            "Operation Cost": float(sum(
                row["Operation Cost"] for row in warehouse_customer_rows if row["Warehouse Id"] == w
            )),
        })
    warehouse_summary_df = pd.DataFrame(warehouse_summary_rows).sort_values(
        ["Warehouse Id"], ignore_index=True) if warehouse_summary_rows else pd.DataFrame()

    # Build summary
    total_inbound_qty = sum(inbound_qty_by_warehouse.values())
    total_outbound_qty = sum(outbound_qty_by_warehouse.values())
    total_inventory_qty = total_inbound_qty - total_outbound_qty
    total_inventory_capacity = sum(inventory_capacity_by_warehouse.values())
    fixed_cost_total = float(
        data.warehouses[data.warehouses["Warehouse ID"].isin(selected_warehouses)]["Fixed Cost"].sum()
    )
    total_do_qty = float(coverage_detail_df["Assigned Do Qty"].sum()) if not coverage_detail_df.empty else 0.0
    covered_customer_count = int((coverage_detail_df["Coverage YN"] == "Y").sum()) if not coverage_detail_df.empty else 0
    customer_count = len(coverage_detail_df)
    covered_do_qty = (
        float(coverage_detail_df.loc[coverage_detail_df["Coverage YN"] == "Y", "Assigned Do Qty"].sum())
        if not coverage_detail_df.empty else 0.0
    )
    warehouse_cost_total = fixed_cost_total + operation_cost_total

    summary_df = pd.DataFrame([{
        "Case Name": case_name,
        "Case Type": case_type,
        "Total Rank": None,
        "Cost Rank": None,
        "Optimal Cost": sol.total_cost,
        "Optimal Total Inbound Qty": total_inbound_qty,
        "Optimal Total Outbound Qty": total_outbound_qty,
        "Optimal Total Inventory Qty": total_inventory_qty,
        "Total Inventory Capacity Qty": total_inventory_capacity,
        "Inventory Utilization (%)": (total_inventory_qty / total_inventory_capacity * 100.0) if total_inventory_capacity else 0.0,
        "Inbound Cost": inbound_cost_total,
        "Warehouse Cost": warehouse_cost_total,
        "Outbound Cost": outbound_cost_total,
        "Lead Time Rank": None,
        "Optimal Lead Time (Sec.)": inbound_leadtime_total_sec + outbound_leadtime_total_sec,
        "Inbound Lead Time (Sec.)": inbound_leadtime_total_sec,
        "Outbound Lead Time (Sec.)": outbound_leadtime_total_sec,
        "Coverage Rank(Time)": None,
        "Coverage Time (%)": (covered_customer_count / customer_count * 100.0) if customer_count else 0.0,
        "Coverage Rank(Vol)": None,
        "Coverage Vol (%)": (covered_do_qty / total_do_qty * 100.0) if total_do_qty else 0.0,
        "Cost Score": None,
        "Lead Time Score": None,
        "Coverage Time Score": None,
        "Coverage Vol Score": None,
        "Coverage Score": None,
        "Total Score": None,
        "Selected Warehouse Count": len(selected_warehouses),
        "Selected Warehouses": ",".join(selected_warehouses),
        "Carbon Emission(tCO2-eq)": 0.0,
    }])

    return CaseResult(
        case_name=case_name,
        case_type=case_type,
        total_cost=sol.total_cost,
        selected_warehouses=selected_warehouses,
        plant_warehouse_routes=plant_warehouse_df,
        warehouse_summary=warehouse_summary_df,
        warehouse_customer_routes=warehouse_customer_df,
        coverage_detail=coverage_detail_df,
        summary=summary_df,
    )
