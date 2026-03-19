from __future__ import annotations

import math
import os

import pandas as pd
from ortools.linear_solver import pywraplp

from .domain import CaseResult, NetworkData
from .loader import DataValidationError, get_customer_mapping_requirements
from .logging_utils import get_logger


LOGGER = get_logger()


def configure_solver_threads(solver: pywraplp.Solver, solver_name: str) -> int:
    cpu_threads = max(1, os.cpu_count() or 1)
    configured = solver.SetNumThreads(cpu_threads)
    if configured:
        LOGGER.info("Configured solver '%s' to use %d thread(s)", solver_name, cpu_threads)
    else:
        LOGGER.warning(
            "Solver '%s' did not confirm thread configuration; requested %d thread(s)",
            solver_name,
            cpu_threads,
        )
    return cpu_threads


def build_solver(
    data: NetworkData,
    solver_name: str,
    forced_open_warehouses: set[str] | None = None,
):
    solver = pywraplp.Solver.CreateSolver(solver_name)
    if solver is None:
        raise RuntimeError(f"Failed to create OR-Tools solver: {solver_name}")
    configure_solver_threads(solver, solver_name)

    plants = data.plants[["Plant ID", "Product Qty", "Shipment Qty", "Location Name"]].copy()
    warehouses = data.warehouses[
        ["Warehouse ID", "Capacity Qty", "Fixed Cost", "Operation Cost", "Location Name"]
    ].copy()
    customers = data.customers[["Customer ID", "Do Qty", "Shipment Qty", "Location Name"]].copy()

    if forced_open_warehouses is not None:
        warehouses = warehouses[warehouses["Warehouse ID"].isin(forced_open_warehouses)].reset_index(drop=True)

    valid_warehouse_ids = set(warehouses["Warehouse ID"])
    pw = data.plant_warehouse_cost[
        data.plant_warehouse_cost["Warehouse ID"].isin(valid_warehouse_ids)
    ][["Plant ID", "Warehouse ID", "Distance (km)", "Trns Cost"]].copy()
    wc = data.warehouse_customer_cost[
        data.warehouse_customer_cost["Warehouse ID"].isin(valid_warehouse_ids)
    ][["Warehouse ID", "Customer ID", "Distance (km)", "Trns Cost"]].copy()

    demand_by_customer = customers.set_index("Customer ID")["Do Qty"].to_dict()
    supply_by_plant = plants.set_index("Plant ID")["Product Qty"].to_dict()
    capacity_by_warehouse = warehouses.set_index("Warehouse ID")["Capacity Qty"].to_dict()
    fixed_cost_by_warehouse = warehouses.set_index("Warehouse ID")["Fixed Cost"].to_dict()
    op_cost_by_warehouse = warehouses.set_index("Warehouse ID")["Operation Cost"].to_dict()
    customer_mapping = get_customer_mapping_requirements(data)
    pw_cost = {(row["Plant ID"], row["Warehouse ID"]): float(row["Trns Cost"]) for _, row in pw.iterrows()}
    wc_cost = {(row["Warehouse ID"], row["Customer ID"]): float(row["Trns Cost"]) for _, row in wc.iterrows()}

    total_supply = float(plants["Product Qty"].sum())
    warehouse_ids = list(warehouses["Warehouse ID"])
    plant_ids = list(plants["Plant ID"])
    customer_ids = list(customers["Customer ID"])

    if forced_open_warehouses is not None and set(warehouse_ids) != forced_open_warehouses:
        missing = sorted(forced_open_warehouses - set(warehouse_ids))
        raise DataValidationError(f"Forced-open warehouse rows not found: {missing}")

    mapped_warehouse_ids = set(customer_mapping.values())
    if forced_open_warehouses is not None and not mapped_warehouse_ids.issubset(forced_open_warehouses):
        missing_mapped = sorted(mapped_warehouse_ids - forced_open_warehouses)
        raise DataValidationError(
            f"Forced-open warehouse set is missing mapped warehouses required by customer Mapping ID: {missing_mapped}"
        )

    y = {w: solver.BoolVar(f"open[{w}]") for w in warehouse_ids}
    x = {(w, c): solver.BoolVar(f"assign[{w},{c}]") for (w, c) in wc_cost}
    f = {
        (p, w): solver.IntVar(
            0,
            int(float(supply_by_plant[p])),
            f"flow[{p},{w}]",
        )
        for (p, w) in pw_cost
    }

    for c in customer_ids:
        eligible = [x[(w, c)] for (w, c2) in x if c2 == c]
        if not eligible:
            raise DataValidationError(f"Customer '{c}' has no eligible warehouse arc.")
        solver.Add(sum(eligible) == 1)
        mapped_warehouse = customer_mapping.get(c)
        if mapped_warehouse is not None:
            if (mapped_warehouse, c) not in x:
                raise DataValidationError(
                    f"Customer '{c}' is mapped to warehouse '{mapped_warehouse}' but no eligible assignment arc exists."
                )
            solver.Add(x[(mapped_warehouse, c)] == 1)

    inbound_expr = {}
    outbound_expr = {}
    customer_count_expr = {}
    for w in warehouse_ids:
        assigned_qty = [demand_by_customer[c] * x[(w, c)] for (w2, c) in x if w2 == w]
        assigned_count = [x[(w, c)] for (w2, c) in x if w2 == w]
        outbound = sum(assigned_qty) if assigned_qty else 0
        outbound_expr[w] = outbound
        customer_count_expr[w] = sum(assigned_count) if assigned_count else 0
        inbound = sum(f[(p, w)] for (p, w2) in f if w2 == w)
        inbound_expr[w] = inbound
        solver.Add(outbound <= inbound)
        solver.Add(outbound <= capacity_by_warehouse[w] * y[w])
        solver.Add(customer_count_expr[w] >= y[w])

    for p in plant_ids:
        outbound = [f[(p, w)] for (p2, w) in f if p2 == p]
        solver.Add(sum(outbound) <= supply_by_plant[p])

    if forced_open_warehouses is None:
        solver.Add(sum(y.values()) == data.simulation.warehouse_qty)
    else:
        if len(forced_open_warehouses) != data.simulation.warehouse_qty:
            raise DataValidationError(
                f"Forced-open warehouse count ({len(forced_open_warehouses)}) does not match simulation warehouse qty ({data.simulation.warehouse_qty})."
            )
        for w in warehouse_ids:
            solver.Add(y[w] == 1)
    for w in mapped_warehouse_ids:
        if w in y:
            solver.Add(y[w] == 1)

    solver.Add((sum(f.values()) if f else 0) == total_supply)

    objective = solver.Objective()

    def set_total_cost_objective() -> None:
        objective.Clear()
        for w in warehouse_ids:
            objective.SetCoefficient(y[w], float(fixed_cost_by_warehouse[w]))
        for (w, c), var in x.items():
            objective.SetCoefficient(
                var,
                float(demand_by_customer[c]) * (float(wc_cost[(w, c)]) + float(op_cost_by_warehouse[w])),
            )
        for (p, w), var in f.items():
            objective.SetCoefficient(var, float(pw_cost[(p, w)]))
        objective.SetMinimization()

    set_total_cost_objective()

    return (
        solver,
        y,
        x,
        f,
        demand_by_customer,
        op_cost_by_warehouse,
        pw_cost,
        wc_cost,
        capacity_by_warehouse,
        total_supply,
    )


def solve_case(
    data: NetworkData,
    solver_name: str,
    case_name: str,
    case_type: str,
    forced_open_warehouses: set[str] | None = None,
) -> CaseResult:
    LOGGER.info("Solving case '%s' (%s)", case_name, case_type)
    (
        solver,
        y,
        x,
        f,
        demand_by_customer,
        op_cost_by_warehouse,
        pw_cost,
        wc_cost,
        capacity_by_warehouse,
        total_supply,
    ) = build_solver(data, solver_name, forced_open_warehouses)

    cost_status = solver.Solve()
    if cost_status != pywraplp.Solver.OPTIMAL:
        raise RuntimeError(
            f"Optimization failed for case '{case_name}' during cost minimization with total inbound fixed to "
            f"total supply ({total_supply}). Solver status: {cost_status}"
        )

    selected_warehouses = sorted([w for w, var in y.items() if var.solution_value() > 0.5])
    warehouse_lookup = data.warehouses.set_index("Warehouse ID")
    pw_lookup = data.plant_warehouse_cost.set_index(["Plant ID", "Warehouse ID"])
    wc_lookup = data.warehouse_customer_cost.set_index(["Warehouse ID", "Customer ID"])
    customer_lookup = data.customers.set_index("Customer ID")
    plant_lookup = data.plants.set_index("Plant ID")
    speed_kmh = data.simulation.speed_kmh
    coverage_hours = data.simulation.coverage_hours
    inbound_qty_by_warehouse = {w: 0.0 for w in selected_warehouses}
    outbound_qty_by_warehouse = {w: 0.0 for w in selected_warehouses}
    plant_warehouse_rows = []
    plant_warehouse_leadtime_by_warehouse = {}
    inbound_cost_total = 0.0
    inbound_leadtime_total_sec = 0.0

    for (p, w), var in f.items():
        do_qty = float(var.solution_value())
        if do_qty <= 1e-6:
            continue
        inbound_qty_by_warehouse[w] = inbound_qty_by_warehouse.get(w, 0.0) + do_qty
        distance_km = float(pw_lookup.loc[(p, w), "Distance (km)"])
        plant_shipment_qty = float(plant_lookup.loc[p, "Shipment Qty"])
        trips_ratio = do_qty / plant_shipment_qty if plant_shipment_qty else 0.0
        leadtime_sec = ((distance_km / speed_kmh) * trips_ratio * 3600.0) if speed_kmh else math.inf
        cost = do_qty * float(pw_cost[(p, w)])
        plant_warehouse_leadtime_by_warehouse[w] = leadtime_sec
        inbound_cost_total += cost
        inbound_leadtime_total_sec += leadtime_sec
        plant_warehouse_rows.append(
            {
                "Plant Id": p,
                "Plant Location Name": plant_lookup.loc[p, "Location Name"],
                "Warehouse Id": w,
                "Warehouse Location Name": warehouse_lookup.loc[w, "Location Name"],
                "Do Qty": do_qty,
                "Cost": cost,
                "Shipment Qty Ratio": trips_ratio,
                "Lead Time (Sec.)": leadtime_sec,
                "Distance (km)": distance_km,
                "Carbon Emission(tCO2-eq)": 0.0,
            }
        )

    warehouse_customer_rows = []
    coverage_rows = []
    outbound_cost_total = 0.0
    operation_cost_total = 0.0
    outbound_leadtime_total_sec = 0.0

    for (w, c), var in x.items():
        if var.solution_value() <= 0.5:
            continue
        do_qty = float(demand_by_customer[c])
        outbound_qty_by_warehouse[w] = outbound_qty_by_warehouse.get(w, 0.0) + do_qty
        distance_km = float(wc_lookup.loc[(w, c), "Distance (km)"])
        customer_shipment_qty = float(customer_lookup.loc[c, "Shipment Qty"])
        one_way_time_sec = ((distance_km / speed_kmh) * 3600.0) if speed_kmh else math.inf
        route_leadtime_sec = ((distance_km / speed_kmh) * customer_shipment_qty * 3600.0) if speed_kmh else math.inf
        within_coverage = one_way_time_sec <= coverage_hours * 3600.0
        route_cost = do_qty * float(wc_cost[(w, c)])
        operation_cost = do_qty * float(op_cost_by_warehouse[w])
        outbound_cost_total += route_cost
        operation_cost_total += operation_cost
        outbound_leadtime_total_sec += route_leadtime_sec

        warehouse_customer_rows.append(
            {
                "Warehouse Id": w,
                "Warehouse Location Name": warehouse_lookup.loc[w, "Location Name"],
                "Customer Id": c,
                "Customer Location Name": customer_lookup.loc[c, "Location Name"],
                "Do Qty": do_qty,
                "Cost": route_cost,
                "Shipment Qty": customer_shipment_qty,
                "Lead Time (Sec.)": route_leadtime_sec,
                "Distance (km)": distance_km,
                "One-way Time (Sec.)": one_way_time_sec,
                "Coverage YN": "Y" if within_coverage else "N",
                "Operation Cost": operation_cost,
                "Carbon Emission(tCO2-eq)": 0.0,
            }
        )
        coverage_rows.append(
            {
                "Warehouse Id": w,
                "Customer Id": c,
                "Assigned Do Qty": do_qty,
                "Customer Shipment Qty": customer_shipment_qty,
                "Plant-Warehouse Lead Time (Sec.)": plant_warehouse_leadtime_by_warehouse.get(w, 0.0),
                "Warehouse-Customer Lead Time (Sec.)": route_leadtime_sec,
                "Total Lead Time (Sec.)": plant_warehouse_leadtime_by_warehouse.get(w, 0.0) + route_leadtime_sec,
                "Coverage Hour": coverage_hours,
                "One-way Time (Sec.)": one_way_time_sec,
                "Coverage YN": "Y" if within_coverage else "N",
            }
        )

    plant_warehouse_df = pd.DataFrame(plant_warehouse_rows).sort_values(["Plant Id", "Warehouse Id"], ignore_index=True)
    warehouse_customer_df = pd.DataFrame(warehouse_customer_rows).sort_values(["Warehouse Id", "Customer Id"], ignore_index=True)
    coverage_detail_df = pd.DataFrame(coverage_rows).sort_values(["Warehouse Id", "Customer Id"], ignore_index=True)
    warehouse_summary_rows = []
    for w in selected_warehouses:
        inbound_qty = inbound_qty_by_warehouse.get(w, 0.0)
        outbound_qty = outbound_qty_by_warehouse.get(w, 0.0)
        warehouse_summary_rows.append(
            {
                "Warehouse Id": w,
                "Warehouse Location Name": warehouse_lookup.loc[w, "Location Name"],
                "Inbound Qty": inbound_qty,
                "Outbound Qty": outbound_qty,
                "Throughput Capacity Qty": float(capacity_by_warehouse[w]),
                "Fixed Cost": float(warehouse_lookup.loc[w, "Fixed Cost"]),
                "Operation Cost": float(
                    sum(row["Operation Cost"] for row in warehouse_customer_rows if row["Warehouse Id"] == w)
                ),
            }
        )
    warehouse_summary_df = pd.DataFrame(warehouse_summary_rows).sort_values(["Warehouse Id"], ignore_index=True)

    total_inbound_qty = float(sum(inbound_qty_by_warehouse.values()))
    total_outbound_qty = float(sum(outbound_qty_by_warehouse.values()))
    fixed_cost_total = float(
        data.warehouses[data.warehouses["Warehouse ID"].isin(selected_warehouses)]["Fixed Cost"].sum()
    )
    total_do_qty = float(coverage_detail_df["Assigned Do Qty"].sum()) if not coverage_detail_df.empty else 0.0
    covered_customer_count = int((coverage_detail_df["Coverage YN"] == "Y").sum()) if not coverage_detail_df.empty else 0
    customer_count = len(coverage_detail_df)
    covered_do_qty = (
        float(coverage_detail_df.loc[coverage_detail_df["Coverage YN"] == "Y", "Assigned Do Qty"].sum())
        if not coverage_detail_df.empty
        else 0.0
    )
    warehouse_cost_total = fixed_cost_total + operation_cost_total

    summary_df = pd.DataFrame(
        [
            {
                "Case Name": case_name,
                "Case Type": case_type,
                "Total Rank": None,
                "Cost Rank": None,
                "Optimal Cost": float(solver.Objective().Value()),
                "Optimal Total Inbound Qty": total_inbound_qty,
                "Optimal Total Outbound Qty": total_outbound_qty,
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
            }
        ]
    )

    LOGGER.info(
        "Solved case '%s': total_inbound=%.2f total_cost=%.2f selected_warehouses=%d",
        case_name,
        total_inbound_qty,
        float(solver.Objective().Value()),
        len(selected_warehouses),
    )
    return CaseResult(
        case_name=case_name,
        case_type=case_type,
        total_cost=float(solver.Objective().Value()),
        selected_warehouses=selected_warehouses,
        plant_warehouse_routes=plant_warehouse_df,
        warehouse_summary=warehouse_summary_df,
        warehouse_customer_routes=warehouse_customer_df,
        coverage_detail=coverage_detail_df,
        summary=summary_df,
    )
