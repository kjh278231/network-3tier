from __future__ import annotations

import json
from typing import Optional

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from data_loader import RunData


def make_tools(run_data: RunData) -> list:
    best_case_name = run_data.best_case().case_name

    def _get_case(case_name: str | None):
        name = case_name or best_case_name
        for c in run_data.cases:
            if c.case_name == name:
                return c
        return run_data.best_case()

    def _get_summary_rows(case_name: str | None) -> list[dict]:
        if case_name:
            return [r for r in run_data.summary_rows if r.get("Case Name") == case_name]
        return run_data.summary_rows

    # -------------------------------------------------------------------------
    # 기존 Tool
    # -------------------------------------------------------------------------

    @tool
    def get_network_overview() -> str:
        """Returns a complete overview of the input network: simulation config,
        ALL warehouse candidates (including non-selected ones), plant supply,
        total demand, and capacity balance. Call this first to understand the
        problem scale before analyzing results."""
        sim = run_data.simulation
        total_demand = sum(float(c.get("doQty") or 0) for c in run_data.customers)
        total_supply = sum(float(p.get("productQty") or 0) for p in run_data.plants)
        total_capacity = sum(float(w.get("capacityQty") or 0) for w in run_data.warehouses)
        total_default_inv = sum(float(w.get("defaultInventoryQty") or 0) for w in run_data.warehouses)

        candidates = []
        for w in run_data.warehouses:
            candidates.append({
                "warehouse_id": w.get("warehouseId", ""),
                "location": w.get("locationName", ""),
                "capacity_qty": w.get("capacityQty"),
                "default_inventory_qty": w.get("defaultInventoryQty", 0),
                "fixed_cost": w.get("fixedCost"),
                "operation_cost": w.get("operationCost"),
            })

        plants = []
        for p in run_data.plants:
            plants.append({
                "plant_id": p.get("plantId", ""),
                "location": p.get("locationName", ""),
                "product_qty": p.get("productQty"),
                "shipment_qty": p.get("shipmentQty"),
            })

        return json.dumps({
            "simulation": {
                "name": sim.get("simulationName", ""),
                "warehouse_qty_required": sim.get("warehouseQty"),
                "speed_kmh": sim.get("speedKmh"),
                "coverage_hours": sim.get("coverageHours"),
            },
            "supply_demand_balance": {
                "total_supply": total_supply,
                "total_demand": total_demand,
                "supply_surplus": round(total_supply - total_demand, 2),
                "total_capacity": total_capacity,
                "total_default_inventory": total_default_inv,
                "theoretical_capacity_util_pct": round(total_demand / total_capacity * 100, 1) if total_capacity else 0,
            },
            "plants": plants,
            "warehouse_candidates": candidates,
            "customer_count": len(run_data.customers),
        }, ensure_ascii=False)

    @tool
    def get_cross_case_ranking(sort_by: str = "total_rank", top_n: int = 20) -> str:
        """Returns ranked comparison of all cases with scores and key metrics.
        sort_by options: 'total_rank', 'cost_rank', 'lead_time_rank', 'coverage_rank'"""
        col_map = {
            "total_rank": "Total Rank",
            "cost_rank": "Cost Rank",
            "lead_time_rank": "Lead Time Rank",
            "coverage_rank": "Coverage Rank(Time)",
        }
        sort_col = col_map.get(sort_by, "Total Rank")
        rows = sorted(run_data.summary_rows, key=lambda r: (r.get(sort_col) or 9999))[:top_n]

        cases = []
        for row in rows:
            cases.append({
                "case_name": row.get("Case Name", ""),
                "case_type": row.get("Case Type", ""),
                "total_rank": row.get("Total Rank"),
                "cost_rank": row.get("Cost Rank"),
                "lead_time_rank": row.get("Lead Time Rank"),
                "optimal_cost": row.get("Optimal Cost"),
                "lead_time_sec": row.get("Optimal Lead Time (Sec.)"),
                "coverage_time_pct": row.get("Coverage Time (%)"),
                "coverage_vol_pct": row.get("Coverage Vol (%)"),
                "total_score": row.get("Total Score"),
                "selected_warehouses": row.get("Selected Warehouses", ""),
                "selected_count": row.get("Selected Warehouse Count"),
            })
        return json.dumps({"total_cases": len(run_data.summary_rows), "cases": cases}, ensure_ascii=False)

    @tool
    def get_cost_breakdown(case_name: Optional[str] = None) -> str:
        """Returns cost breakdown by component (inbound/warehouse/outbound) for one or all cases.
        Pass case_name=None for all cases."""
        rows = _get_summary_rows(case_name)
        if not rows:
            rows = [_get_case(case_name).summary]

        result = []
        for row in rows:
            total = row.get("Optimal Cost") or 0
            inbound = row.get("Inbound Cost") or 0
            warehouse = row.get("Warehouse Cost") or 0
            outbound = row.get("Outbound Cost") or 0
            result.append({
                "case_name": row.get("Case Name", ""),
                "total_cost": total,
                "inbound_cost": inbound,
                "warehouse_cost": warehouse,
                "outbound_cost": outbound,
                "inbound_pct": round(inbound / total * 100, 1) if total else 0,
                "warehouse_pct": round(warehouse / total * 100, 1) if total else 0,
                "outbound_pct": round(outbound / total * 100, 1) if total else 0,
                "cost_score": row.get("Cost Score"),
            })
        return json.dumps({"cases": result}, ensure_ascii=False)

    @tool
    def get_warehouse_utilization(case_name: Optional[str] = None) -> str:
        """Returns warehouse utilization rates (outbound qty vs throughput capacity) for a case."""
        c = _get_case(case_name)
        warehouses = []
        for w in c.warehouse_summary:
            outbound = w.get("Outbound Qty") or 0
            capacity = w.get("Throughput Capacity Qty") or 0
            util = round(outbound / capacity * 100, 1) if capacity else 0
            warehouses.append({
                "warehouse_id": w.get("Warehouse Id", ""),
                "location": w.get("Warehouse Location Name", ""),
                "inbound_qty": w.get("Inbound Qty"),
                "outbound_qty": outbound,
                "capacity_qty": capacity,
                "utilization_pct": util,
                "fixed_cost": w.get("Fixed Cost"),
                "operation_cost": w.get("Operation Cost"),
            })
        return json.dumps({"case_name": c.case_name, "warehouses": warehouses}, ensure_ascii=False)

    @tool
    def get_coverage_stats(case_name: Optional[str] = None) -> str:
        """Returns coverage statistics per warehouse and overall for a case.
        Includes both customer count coverage and DoQty volume coverage."""
        c = _get_case(case_name)
        s = c.summary
        overall = {
            "case_name": c.case_name,
            "overall_coverage_time_pct": s.get("Coverage Time (%)"),
            "overall_coverage_vol_pct": s.get("Coverage Vol (%)"),
        }
        wh_location_map = {
            str(w.get("Warehouse Id", w.get("warehouseId", ""))): w.get("Warehouse Location Name", w.get("locationName", ""))
            for w in (c.warehouse_summary or run_data.warehouses)
        }

        per_warehouse = []
        if c.coverage_details:
            df = pd.DataFrame(c.coverage_details)
            for wid, grp in df.groupby("Warehouse Id"):
                covered = (grp["Coverage YN"] == "Y").sum()
                covered_vol = grp.loc[grp["Coverage YN"] == "Y", "Assigned Do Qty"].sum()
                total_vol = grp["Assigned Do Qty"].sum()
                per_warehouse.append({
                    "warehouse_id": wid,
                    "location": wh_location_map.get(str(wid), ""),
                    "assigned_customers": len(grp),
                    "covered_customers": int(covered),
                    "covered_customers_pct": round(covered / len(grp) * 100, 1) if len(grp) else 0,
                    "covered_doqty_pct": round(float(covered_vol) / float(total_vol) * 100, 1) if total_vol else 0,
                    "total_doqty": float(total_vol),
                })
        return json.dumps({**overall, "per_warehouse": per_warehouse}, ensure_ascii=False)

    @tool
    def get_lead_time_distribution(
        case_name: Optional[str] = None,
        breakdown_by_warehouse: bool = False,
    ) -> str:
        """Returns lead time distribution statistics (mean, median, p90, p95) for outbound routes.
        Set breakdown_by_warehouse=True to get per-warehouse breakdown."""
        c = _get_case(case_name)
        s = c.summary
        result: dict = {
            "case_name": c.case_name,
            "total_leadtime_sec": s.get("Optimal Lead Time (Sec.)"),
            "inbound_lt_sec": s.get("Inbound Lead Time (Sec.)"),
            "outbound_lt_sec": s.get("Outbound Lead Time (Sec.)"),
        }
        if c.warehouse_customer_routes:
            df = pd.DataFrame(c.warehouse_customer_routes)
            lt_col = "Lead Time (Sec.)"
            if lt_col in df.columns:
                lts = df[lt_col].dropna().values
                if len(lts) > 0:
                    p50, p90, p95 = np.percentile(lts, [50, 90, 95])
                    result["distribution"] = {
                        "mean": round(float(lts.mean()), 1),
                        "median": round(float(p50), 1),
                        "p90": round(float(p90), 1),
                        "p95": round(float(p95), 1),
                        "min": round(float(lts.min()), 1),
                        "max": round(float(lts.max()), 1),
                    }
                    if breakdown_by_warehouse:
                        per_wh = []
                        for wid, grp in df.groupby("Warehouse Id"):
                            wh_lts = grp[lt_col].dropna().values
                            if len(wh_lts) > 0:
                                per_wh.append({
                                    "warehouse_id": wid,
                                    "mean_lt_sec": round(float(wh_lts.mean()), 1),
                                    "p90_lt_sec": round(float(np.percentile(wh_lts, 90)), 1),
                                    "max_lt_sec": round(float(wh_lts.max()), 1),
                                    "route_count": len(wh_lts),
                                })
                        result["per_warehouse"] = per_wh
        return json.dumps(result, ensure_ascii=False)

    @tool
    def get_route_efficiency(case_name: Optional[str] = None) -> str:
        """Returns outbound route cost efficiency per warehouse: cost per DoQty unit and avg distance."""
        c = _get_case(case_name)
        if not c.warehouse_customer_routes:
            return json.dumps({"case_name": c.case_name, "per_warehouse": []})

        df = pd.DataFrame(c.warehouse_customer_routes)
        per_wh = []
        for wid, grp in df.groupby("Warehouse Id"):
            total_cost = float(grp["Cost"].sum()) if "Cost" in grp.columns else 0
            total_do = float(grp["Do Qty"].sum()) if "Do Qty" in grp.columns else 0
            avg_dist = float(grp["Distance (km)"].mean()) if "Distance (km)" in grp.columns else 0
            per_wh.append({
                "warehouse_id": wid,
                "location": grp.iloc[0].get("Warehouse Location Name", ""),
                "route_count": len(grp),
                "total_cost": total_cost,
                "total_doqty": total_do,
                "cost_per_doqty": round(total_cost / total_do, 2) if total_do else 0,
                "avg_distance_km": round(avg_dist, 1),
            })
        per_wh.sort(key=lambda x: x["cost_per_doqty"])
        return json.dumps({"case_name": c.case_name, "per_warehouse": per_wh}, ensure_ascii=False)

    @tool
    def get_customer_demand_concentration(
        case_name: Optional[str] = None,
        top_n_customers: int = 10,
        concentration_threshold_pct: float = 80.0,
    ) -> str:
        """Returns customer demand distribution: top-N customers and how many customers
        account for the threshold% of total DoQty (concentration analysis)."""
        c = _get_case(case_name)
        customers_df = pd.DataFrame(run_data.customers)
        if customers_df.empty:
            return json.dumps({"error": "No customer data"})

        id_col = "customerId" if "customerId" in customers_df.columns else "Customer ID"
        do_col = "doQty" if "doQty" in customers_df.columns else "Do Qty"
        loc_col = "locationName" if "locationName" in customers_df.columns else "Location Name"

        customers_df = customers_df.rename(columns={id_col: "cid", do_col: "doqty", loc_col: "loc"})
        customers_df["doqty"] = pd.to_numeric(customers_df["doqty"], errors="coerce").fillna(0)
        customers_df = customers_df.sort_values("doqty", ascending=False).reset_index(drop=True)

        total_doqty = float(customers_df["doqty"].sum())
        total_customers = len(customers_df)

        wc_df = pd.DataFrame(c.warehouse_customer_routes) if c.warehouse_customer_routes else pd.DataFrame()
        wc_map = {}
        if not wc_df.empty and "Customer Id" in wc_df.columns:
            wc_map = dict(zip(wc_df["Customer Id"].astype(str), wc_df["Warehouse Id"].astype(str)))

        top_customers = []
        for _, row in customers_df.head(top_n_customers).iterrows():
            cid = str(row["cid"])
            top_customers.append({
                "customer_id": cid,
                "location": str(row.get("loc", "")),
                "doqty": float(row["doqty"]),
                "pct_of_total": round(float(row["doqty"]) / total_doqty * 100, 2) if total_doqty else 0,
                "assigned_warehouse": wc_map.get(cid, "N/A"),
            })

        cumsum = customers_df["doqty"].cumsum()
        threshold_count = int((cumsum < total_doqty * concentration_threshold_pct / 100).sum()) + 1

        return json.dumps({
            "case_name": c.case_name,
            "total_customers": total_customers,
            "total_doqty": total_doqty,
            "top_customers": top_customers,
            "concentration": {
                "threshold_pct": concentration_threshold_pct,
                "customers_needed": threshold_count,
                "customers_pct_of_total": round(threshold_count / total_customers * 100, 1) if total_customers else 0,
            },
        }, ensure_ascii=False)

    # -------------------------------------------------------------------------
    # 신규 Tool 3개
    # -------------------------------------------------------------------------

    @tool
    def get_plant_warehouse_flow(case_name: Optional[str] = None) -> str:
        """Returns plant-to-warehouse inbound flow details for a case.
        Shows how plant supply is distributed across open warehouses:
        inbound qty, cost, distance, lead time, and share of total supply."""
        c = _get_case(case_name)
        if not c.plant_warehouse_routes:
            return json.dumps({"case_name": c.case_name, "routes": []})

        total_inbound = sum(float(r.get("Do Qty") or 0) for r in c.plant_warehouse_routes)
        routes = []
        for r in c.plant_warehouse_routes:
            do_qty = float(r.get("Do Qty") or 0)
            routes.append({
                "plant_id": r.get("Plant Id", ""),
                "plant_location": r.get("Plant Location Name", ""),
                "warehouse_id": r.get("Warehouse Id", ""),
                "warehouse_location": r.get("Warehouse Location Name", ""),
                "inbound_qty": do_qty,
                "inbound_share_pct": round(do_qty / total_inbound * 100, 1) if total_inbound else 0,
                "cost": r.get("Cost"),
                "lead_time_sec": r.get("Lead Time (Sec.)"),
                "distance_km": r.get("Distance (km)"),
                "shipment_qty_ratio": r.get("Shipment Qty Ratio"),
            })
        routes.sort(key=lambda x: x["inbound_qty"], reverse=True)

        return json.dumps({
            "case_name": c.case_name,
            "total_inbound_qty": total_inbound,
            "routes": routes,
        }, ensure_ascii=False)

    @tool
    def get_warehouse_selection_diff(base_case: Optional[str] = None) -> str:
        """Compares warehouse selection between the base case (default: best_model) and
        all other cases. For each case shows which warehouses were swapped in/out and
        the resulting cost delta. This is the core sensitivity analysis for 1-swap
        neighborhood search — answers 'which warehouse swap costs how much extra?'"""
        base_name = base_case or best_case_name
        base = _get_case(base_name)

        base_wh_str = base.summary.get("Selected Warehouses", "")
        base_warehouses = {w.strip() for w in base_wh_str.split(",") if w.strip()}
        base_cost = float(base.summary.get("Optimal Cost") or 0)

        comparisons = []
        for c in run_data.cases:
            if c.case_name == base_name:
                continue
            case_wh_str = c.summary.get("Selected Warehouses", "")
            case_warehouses = {w.strip() for w in case_wh_str.split(",") if w.strip()}

            removed = sorted(base_warehouses - case_warehouses)
            added = sorted(case_warehouses - base_warehouses)
            case_cost = float(c.summary.get("Optimal Cost") or 0)
            cost_delta = case_cost - base_cost

            comparisons.append({
                "case_name": c.case_name,
                "case_type": c.case_type,
                "total_rank": c.summary.get("Total Rank"),
                "warehouses_removed_vs_base": removed,
                "warehouses_added_vs_base": added,
                "swap_count": len(removed),
                "case_cost": case_cost,
                "cost_delta": round(cost_delta, 2),
                "cost_delta_pct": round(cost_delta / base_cost * 100, 2) if base_cost else 0,
                "total_score": c.summary.get("Total Score"),
            })

        comparisons.sort(key=lambda x: x["cost_delta"])

        return json.dumps({
            "base_case": base_name,
            "base_warehouses": sorted(base_warehouses),
            "base_cost": base_cost,
            "comparisons": comparisons,
        }, ensure_ascii=False)

    return [
        get_network_overview,
        get_cross_case_ranking,
        get_cost_breakdown,
        get_warehouse_utilization,
        get_coverage_stats,
        get_lead_time_distribution,
        get_route_efficiency,
        get_customer_demand_concentration,
        get_plant_warehouse_flow,
        get_warehouse_selection_diff,
    ]
