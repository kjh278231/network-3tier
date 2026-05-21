from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.tools import tool

from network3tier.loader import get_customer_mapping_requirements
from network3tier.optimizer import SolveOverrides, build_and_solve


def make_tools(run_data):
    nd = run_data.network_data
    solver_name = run_data.solver

    @tool
    def check_aggregate_balance() -> str:
        """총 공급량, 수요량, 창고 용량을 집계하여 전반적인 불균형을 확인합니다."""
        total_demand = float(nd.customers["Do Qty"].sum())
        total_supply = float(nd.plants["Product Qty"].sum())
        total_capacity = float(nd.warehouses["Capacity Qty"].sum())
        total_default_inv = float(nd.warehouses["Default Inventory Qty"].fillna(0).sum())
        return json.dumps(
            {
                "total_demand": total_demand,
                "total_supply": total_supply,
                "total_capacity": total_capacity,
                "total_default_inventory": total_default_inv,
                "supply_deficit": max(0.0, total_demand - total_supply - total_default_inv),
                "capacity_deficit": max(0.0, total_demand - total_capacity),
                "supply_covers_demand": bool(total_supply + total_default_inv >= total_demand),
                "capacity_covers_demand": bool(total_capacity >= total_demand),
            },
            ensure_ascii=False,
        )

    @tool
    def check_customer_arc_eligibility() -> str:
        """각 고객에게 배정 가능한 창고 아크가 존재하는지 확인합니다."""
        wc = nd.warehouse_customer_cost
        customer_ids = sorted(nd.customers["Customer ID"].astype(str).tolist())
        covered = set(wc["Customer ID"].astype(str))
        uncovered = [cid for cid in customer_ids if cid not in covered]
        coverage_counts = wc.groupby("Customer ID")["Warehouse ID"].nunique().to_dict()
        per_customer = [
            {"customer_id": cid, "eligible_warehouse_count": int(coverage_counts.get(cid, 0))}
            for cid in customer_ids
        ]
        return json.dumps(
            {
                "total_customers": len(customer_ids),
                "customers_with_no_arc": uncovered,
                "no_arc_count": len(uncovered),
                "per_customer": per_customer,
            },
            ensure_ascii=False,
        )

    @tool
    def check_mapping_constraints() -> str:
        """Mapping ID 제약 고객의 창고 존재 여부 및 아크 유효성을 검사합니다."""
        customer_mapping = get_customer_mapping_requirements(nd)
        active_wh_ids = set(nd.warehouses["Warehouse ID"].astype(str))
        wc_pairs = set(
            zip(
                nd.warehouse_customer_cost["Warehouse ID"].astype(str),
                nd.warehouse_customer_cost["Customer ID"].astype(str),
            )
        )
        issues = []
        for cid, wid in customer_mapping.items():
            missing_wh = wid not in active_wh_ids
            missing_arc = (wid, cid) not in wc_pairs
            issues.append(
                {
                    "customer_id": cid,
                    "mapped_warehouse_id": wid,
                    "warehouse_active": not missing_wh,
                    "arc_exists": not missing_arc,
                    "has_issue": missing_wh or missing_arc,
                }
            )
        return json.dumps(
            {
                "mapped_customer_count": len(customer_mapping),
                "issues": issues,
                "issue_count": sum(1 for i in issues if i["has_issue"]),
            },
            ensure_ascii=False,
        )

    @tool
    def check_mapped_warehouse_capacity() -> str:
        """매핑된 고객의 수요 합산이 강제 개방 창고의 용량을 초과하는지 확인합니다."""
        customer_mapping = get_customer_mapping_requirements(nd)
        demand_map = nd.customers.set_index("Customer ID")["Do Qty"].to_dict()
        capacity_map = nd.warehouses.set_index("Warehouse ID")["Capacity Qty"].to_dict()
        default_inv_map = (
            nd.warehouses.set_index("Warehouse ID")["Default Inventory Qty"].fillna(0).to_dict()
        )

        per_warehouse: dict = {}
        for cid, wid in customer_mapping.items():
            if wid not in per_warehouse:
                per_warehouse[wid] = {
                    "warehouse_id": wid,
                    "mapped_customers": [],
                    "total_mapped_demand": 0.0,
                    "capacity": float(capacity_map.get(wid, 0)),
                    "default_inventory": float(default_inv_map.get(wid, 0)),
                }
            d = float(demand_map.get(cid, 0))
            per_warehouse[wid]["mapped_customers"].append({"customer_id": cid, "demand": d})
            per_warehouse[wid]["total_mapped_demand"] += d

        rows = []
        for wid, info in per_warehouse.items():
            effective_cap = info["capacity"] + info["default_inventory"]
            rows.append(
                {
                    **info,
                    "effective_capacity": effective_cap,
                    "feasible": bool(info["total_mapped_demand"] <= effective_cap),
                    "excess": max(0.0, info["total_mapped_demand"] - effective_cap),
                }
            )
        return json.dumps(
            {
                "warehouses": rows,
                "infeasible_count": sum(1 for r in rows if not r["feasible"]),
            },
            ensure_ascii=False,
        )

    @tool
    def check_warehouse_count_feasibility() -> str:
        """warehouse_qty 설정이 창고 수 및 매핑 제약과 양립 가능한지 확인합니다."""
        total_active = len(nd.warehouses)
        required = nd.simulation.warehouse_qty
        mapped_wh = set(get_customer_mapping_requirements(nd).values())
        min_required = len(mapped_wh)
        return json.dumps(
            {
                "warehouse_qty_required": required,
                "total_active_warehouses": total_active,
                "min_required_by_mapping": min_required,
                "qty_exceeds_active": bool(required > total_active),
                "qty_below_mapping_minimum": bool(required < min_required),
                "feasible": bool(min_required <= required <= total_active),
            },
            ensure_ascii=False,
        )

    @tool
    def experiment_relax_capacity() -> str:
        """창고 용량 상한을 제거한 후 재최적화하여 용량이 불가능성의 원인인지 확인합니다."""
        feasible, status = build_and_solve(
            nd, solver_name, SolveOverrides(remove_capacity_upper_bound=True)
        )
        return json.dumps(
            {
                "experiment": "capacity_relaxation",
                "feasible_after_relaxation": feasible,
                "status": status,
                "interpretation": "창고 용량 제약이 불가능성의 원인입니다."
                if feasible
                else "용량 제거 후에도 불가능 — 다른 제약이 원인입니다.",
            },
            ensure_ascii=False,
        )

    @tool
    def experiment_relax_supply() -> str:
        """공장 공급량을 매우 크게 설정한 후 재최적화하여 공급 부족이 원인인지 확인합니다."""
        feasible, status = build_and_solve(
            nd, solver_name, SolveOverrides(supply_multiplier=1e6)
        )
        return json.dumps(
            {
                "experiment": "supply_relaxation",
                "feasible_after_relaxation": feasible,
                "status": status,
                "interpretation": "공급량 부족이 불가능성의 원인입니다."
                if feasible
                else "공급 무제한 후에도 불가능 — 공급 이외의 원인이 있습니다.",
            },
            ensure_ascii=False,
        )

    @tool
    def experiment_remove_mapping() -> str:
        """모든 Mapping ID 제약을 제거한 후 재최적화하여 매핑 충돌이 원인인지 확인합니다."""
        mapped_count = len(get_customer_mapping_requirements(nd))
        feasible, status = build_and_solve(
            nd, solver_name, SolveOverrides(remove_mapping_constraints=True)
        )
        return json.dumps(
            {
                "experiment": "mapping_removal",
                "mapped_customers_before": mapped_count,
                "feasible_after_removal": feasible,
                "status": status,
                "interpretation": "Mapping ID 제약이 불가능성의 원인입니다."
                if feasible
                else "매핑 제거 후에도 불가능 — 매핑 이외의 원인이 있습니다.",
            },
            ensure_ascii=False,
        )

    @tool
    def experiment_warehouse_count_sweep() -> str:
        """warehouse_qty를 1부터 전체 창고 수까지 순차 변경하며 실행 가능한 최소 수를 탐색합니다."""
        max_n = len(nd.warehouses)
        mapped_min = len(set(get_customer_mapping_requirements(nd).values()))
        results = []
        min_feasible = None
        for qty in range(max(1, mapped_min), max_n + 1):
            feasible, status = build_and_solve(
                nd, solver_name, SolveOverrides(warehouse_qty_override=qty)
            )
            results.append({"warehouse_qty": qty, "feasible": feasible, "status": status})
            if feasible and min_feasible is None:
                min_feasible = qty
        return json.dumps(
            {
                "experiment": "warehouse_count_sweep",
                "original_warehouse_qty": nd.simulation.warehouse_qty,
                "minimum_feasible_qty": min_feasible,
                "sweep_results": results,
            },
            ensure_ascii=False,
        )

    @tool
    def experiment_per_warehouse_exclusion() -> str:
        """강제 개방 창고(Mapping ID 참조)를 하나씩 제외하며 재최적화하여 문제 창고를 특정합니다."""
        mapped_wh_ids = set(get_customer_mapping_requirements(nd).values())
        if not mapped_wh_ids:
            return json.dumps(
                {"note": "매핑 창고 없음 — 이 실험은 적용 불가", "results": []}, ensure_ascii=False
            )
        results = []
        for wid in sorted(mapped_wh_ids):
            feasible, status = build_and_solve(
                nd, solver_name, SolveOverrides(exclude_warehouse_ids={wid})
            )
            results.append(
                {
                    "excluded_warehouse_id": wid,
                    "feasible_after_exclusion": feasible,
                    "status": status,
                }
            )
        return json.dumps(
            {
                "experiment": "per_warehouse_exclusion",
                "tested_warehouses": sorted(mapped_wh_ids),
                "results": results,
            },
            ensure_ascii=False,
        )

    return [
        check_aggregate_balance,
        check_customer_arc_eligibility,
        check_mapping_constraints,
        check_mapped_warehouse_capacity,
        check_warehouse_count_feasibility,
        experiment_relax_capacity,
        experiment_relax_supply,
        experiment_remove_mapping,
        experiment_warehouse_count_sweep,
        experiment_per_warehouse_exclusion,
    ]
