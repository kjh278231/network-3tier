from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from .domain import CaseResult, NetworkData, PrecheckIssue, PrecheckResult
from .loader import get_customer_mapping_requirements


FAIL_SUMMARY_COLUMNS = [
    "Case Name",
    "Case Type",
    "Run Status",
    "Fail Stage",
    "Fail Reason Count",
    "Fail Reason Summary",
    "Total Rank",
    "Cost Rank",
    "Optimal Cost",
    "Inbound Cost",
    "Warehouse Cost",
    "Outbound Cost",
    "Lead Time Rank",
    "Optimal Lead Time (Sec.)",
    "Inbound Lead Time (Sec.)",
    "Outbound Lead Time (Sec.)",
    "Coverage Rank(Time)",
    "Coverage Time (%)",
    "Coverage Rank(Vol)",
    "Coverage Vol (%)",
    "Cost Score",
    "Lead Time Score",
    "Coverage Time Score",
    "Coverage Vol Score",
    "Coverage Score",
    "Total Score",
    "Selected Warehouse Count",
    "Selected Warehouses",
    "Carbon Emission(tCO2-eq)",
]

EMPTY_ROUTE_COLUMNS = {
    "plant_warehouse_routes": [
        "Plant Id",
        "Plant Location Name",
        "Warehouse Id",
        "Warehouse Location Name",
        "Do Qty",
        "Cost",
        "Shipment Qty Ratio",
        "Lead Time (Sec.)",
        "Distance (km)",
        "Carbon Emission(tCO2-eq)",
    ],
    "warehouse_summary": [
        "Warehouse Id",
        "Warehouse Location Name",
        "Do Qty",
        "Fixed Cost",
        "Operation Cost",
    ],
    "warehouse_customer_routes": [
        "Warehouse Id",
        "Warehouse Location Name",
        "Customer Id",
        "Customer Location Name",
        "Do Qty",
        "Cost",
        "Shipment Qty",
        "Lead Time (Sec.)",
        "Distance (km)",
        "One-way Time (Sec.)",
        "Coverage YN",
        "Operation Cost",
        "Carbon Emission(tCO2-eq)",
    ],
    "coverage_detail": [
        "Warehouse Id",
        "Customer Id",
        "Assigned Do Qty",
        "Customer Shipment Qty",
        "Plant-Warehouse Lead Time (Sec.)",
        "Warehouse-Customer Lead Time (Sec.)",
        "Total Lead Time (Sec.)",
        "Coverage Hour",
        "One-way Time (Sec.)",
        "Coverage YN",
    ],
}


def _format_num(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{float(value):.3f}"


def _issue(
    issue_id: str,
    category: str,
    description: str,
    evidence: str,
    severity: str = "error",
    certainty: str = "certain",
) -> PrecheckIssue:
    return PrecheckIssue(
        issue_id=issue_id,
        category=category,
        severity=severity,
        certainty=certainty,
        description=description,
        evidence=evidence,
    )


def run_precheck(data: NetworkData) -> PrecheckResult:
    issues: list[PrecheckIssue] = []
    customer_mapping = get_customer_mapping_requirements(data)

    total_demand = float(data.customers["Do Qty"].sum()) if "Do Qty" in data.customers else 0.0
    total_supply = float(data.plants["Product Qty"].sum()) if "Product Qty" in data.plants else 0.0
    total_capacity = float(data.warehouses["Capacity Qty"].sum()) if "Capacity Qty" in data.warehouses else 0.0
    required_k = int(data.simulation.warehouse_qty)
    active_warehouse_count = int(len(data.warehouses))

    capacity_series = (
        pd.to_numeric(data.warehouses["Capacity Qty"], errors="coerce").fillna(0.0)
        if "Capacity Qty" in data.warehouses
        else pd.Series(dtype=float)
    )
    top_k_capacity = float(capacity_series.nlargest(min(required_k, len(capacity_series))).sum()) if required_k > 0 else 0.0

    mapped_customer_ids = set(customer_mapping)
    mapped_warehouse_ids = set(customer_mapping.values())
    mapped_customer_demand = (
        float(
            data.customers[data.customers["Customer ID"].astype(str).isin(mapped_customer_ids)]["Do Qty"].sum()
        )
        if mapped_customer_ids and "Do Qty" in data.customers
        else 0.0
    )
    mapped_warehouse_capacity = (
        float(
            data.warehouses[data.warehouses["Warehouse ID"].astype(str).isin(mapped_warehouse_ids)]["Capacity Qty"].sum()
        )
        if mapped_warehouse_ids and "Capacity Qty" in data.warehouses
        else 0.0
    )

    metrics: dict[str, float | int | str] = {
        "total_demand": total_demand,
        "total_supply": total_supply,
        "total_capacity": total_capacity,
        "top_k_capacity": top_k_capacity,
        "required_warehouse_qty": required_k,
        "active_warehouse_count": active_warehouse_count,
        "mapped_warehouse_count": len(mapped_warehouse_ids),
        "mapped_customer_demand": mapped_customer_demand,
        "mapped_warehouse_capacity": mapped_warehouse_capacity,
    }

    if data.plants.empty:
        issues.append(_issue("no_plants", "entity_presence", "No plant rows are available.", "plant row count = 0"))
    if data.warehouses.empty:
        issues.append(
            _issue("no_active_warehouses", "entity_presence", "No active warehouse rows are available.", "active warehouse row count = 0")
        )
    if data.customers.empty:
        issues.append(_issue("no_customers", "entity_presence", "No customer rows are available.", "customer row count = 0"))
    if required_k <= 0:
        issues.append(
            _issue("invalid_required_warehouse_qty", "configuration", "Required warehouse count must be positive.", f"simulation.Warehouse Qty = {required_k}")
        )
    if required_k > active_warehouse_count:
        issues.append(
            _issue(
                "warehouse_qty_exceeds_active_count",
                "configuration",
                "Required warehouse count exceeds active warehouse count.",
                f"K={required_k}, active_warehouses={active_warehouse_count}",
            )
        )
    if total_supply < total_demand:
        issues.append(
            _issue(
                "total_supply_shortage",
                "supply",
                "Total plant supply is smaller than total customer demand.",
                f"supply={_format_num(total_supply)}, demand={_format_num(total_demand)}",
            )
        )
    if total_capacity < total_demand:
        issues.append(
            _issue(
                "total_capacity_shortage_all_active",
                "capacity",
                "Total active warehouse capacity is smaller than total customer demand.",
                f"capacity={_format_num(total_capacity)}, demand={_format_num(total_demand)}",
            )
        )
    if active_warehouse_count > 0 and required_k > 0 and top_k_capacity < total_demand:
        issues.append(
            _issue(
                "top_k_capacity_shortage",
                "capacity",
                "Even the largest possible set of K warehouses cannot cover total demand.",
                f"top_k_capacity={_format_num(top_k_capacity)}, demand={_format_num(total_demand)}, K={required_k}",
            )
        )
    if len(mapped_warehouse_ids) > required_k:
        issues.append(
            _issue(
                "mapped_warehouse_count_exceeds_k",
                "mapping",
                "Distinct mapped warehouses exceed the allowed warehouse count.",
                f"mapped_warehouses={len(mapped_warehouse_ids)}, K={required_k}",
            )
        )
    if mapped_warehouse_capacity < mapped_customer_demand:
        issues.append(
            _issue(
                "mapped_warehouse_capacity_shortage",
                "mapping",
                "Mapped warehouses do not have enough combined capacity for mapped customers.",
                f"mapped_capacity={_format_num(mapped_warehouse_capacity)}, mapped_demand={_format_num(mapped_customer_demand)}",
            )
        )

    wh_ids = set(data.warehouses["Warehouse ID"].astype(str)) if "Warehouse ID" in data.warehouses else set()
    customer_ids = set(data.customers["Customer ID"].astype(str)) if "Customer ID" in data.customers else set()
    plant_ids = set(data.plants["Plant ID"].astype(str)) if "Plant ID" in data.plants else set()
    pw_wh_ids = set(data.plant_warehouse_cost["Warehouse ID"].astype(str)) if "Warehouse ID" in data.plant_warehouse_cost else set()
    pw_plant_ids = set(data.plant_warehouse_cost["Plant ID"].astype(str)) if "Plant ID" in data.plant_warehouse_cost else set()
    wc_wh_ids = set(data.warehouse_customer_cost["Warehouse ID"].astype(str)) if "Warehouse ID" in data.warehouse_customer_cost else set()
    wc_cust_ids = set(data.warehouse_customer_cost["Customer ID"].astype(str)) if "Customer ID" in data.warehouse_customer_cost else set()

    if plant_ids - pw_plant_ids:
        missing = sorted(plant_ids - pw_plant_ids)
        issues.append(
            _issue(
                "plant_missing_outbound_arc",
                "arc_coverage",
                "Some plants have no plant-to-warehouse arcs.",
                f"missing_plants={missing[:10]}",
            )
        )
    if wh_ids - pw_wh_ids:
        missing = sorted(wh_ids - pw_wh_ids)
        issues.append(
            _issue(
                "warehouse_missing_inbound_arc",
                "arc_coverage",
                "Some active warehouses have no plant-to-warehouse arcs.",
                f"missing_warehouses={missing[:10]}",
            )
        )
    if wh_ids - wc_wh_ids:
        missing = sorted(wh_ids - wc_wh_ids)
        issues.append(
            _issue(
                "warehouse_missing_customer_arc",
                "arc_coverage",
                "Some active warehouses have no warehouse-to-customer arcs.",
                f"missing_warehouses={missing[:10]}",
            )
        )
    if customer_ids - wc_cust_ids:
        missing = sorted(customer_ids - wc_cust_ids)
        issues.append(
            _issue(
                "customer_without_arc",
                "arc_coverage",
                "Some customers have no eligible warehouse-customer arcs.",
                f"missing_customers={missing[:10]}",
            )
        )

    missing_mapped_wh = sorted(mapped_warehouse_ids - wh_ids)
    if missing_mapped_wh:
        issues.append(
            _issue(
                "required_warehouse_missing_in_active_set",
                "mapping",
                "Some Mapping ID values reference inactive or missing warehouses.",
                f"missing_mapped_warehouses={missing_mapped_wh[:10]}",
            )
        )

    wc_pairs = set(
        zip(
            data.warehouse_customer_cost["Warehouse ID"].astype(str),
            data.warehouse_customer_cost["Customer ID"].astype(str),
        )
    )
    missing_mapping_arcs = [
        f"{customer_id}->{warehouse_id}"
        for customer_id, warehouse_id in sorted(customer_mapping.items())
        if (warehouse_id, customer_id) not in wc_pairs
    ]
    if missing_mapping_arcs:
        issues.append(
            _issue(
                "mapped_customer_missing_required_arc",
                "mapping",
                "Some mapped customers do not have the required warehouse-customer arc.",
                f"missing_pairs={missing_mapping_arcs[:10]}",
            )
        )

    fail_fast = any(issue.certainty == "certain" for issue in issues)
    return PrecheckResult(
        precheck_passed=not fail_fast,
        fail_fast=fail_fast,
        issues=issues,
        metrics=metrics,
    )


def precheck_issues_to_frame(result: PrecheckResult) -> pd.DataFrame:
    rows = [asdict(issue) for issue in result.issues]
    if not rows:
        return pd.DataFrame(
            columns=["issue_id", "category", "severity", "certainty", "description", "evidence"]
        )
    return pd.DataFrame(rows)


def build_fail_case(case_name: str, case_type: str, result: PrecheckResult) -> CaseResult:
    issues_df = precheck_issues_to_frame(result)
    summary = pd.DataFrame(
        [
            {
                "Case Name": case_name,
                "Case Type": case_type,
                "Run Status": "FAIL",
                "Fail Stage": "precheck",
                "Fail Reason Count": len(result.issues),
                "Fail Reason Summary": " | ".join(issue.issue_id for issue in result.issues),
                "Total Rank": None,
                "Cost Rank": None,
                "Optimal Cost": None,
                "Inbound Cost": None,
                "Warehouse Cost": None,
                "Outbound Cost": None,
                "Lead Time Rank": None,
                "Optimal Lead Time (Sec.)": None,
                "Inbound Lead Time (Sec.)": None,
                "Outbound Lead Time (Sec.)": None,
                "Coverage Rank(Time)": None,
                "Coverage Time (%)": None,
                "Coverage Rank(Vol)": None,
                "Coverage Vol (%)": None,
                "Cost Score": None,
                "Lead Time Score": None,
                "Coverage Time Score": None,
                "Coverage Vol Score": None,
                "Coverage Score": None,
                "Total Score": None,
                "Selected Warehouse Count": None,
                "Selected Warehouses": "",
                "Carbon Emission(tCO2-eq)": None,
            }
        ],
        columns=FAIL_SUMMARY_COLUMNS,
    )

    empty_frames = {
        name: pd.DataFrame(columns=columns) for name, columns in EMPTY_ROUTE_COLUMNS.items()
    }
    return CaseResult(
        case_name=case_name,
        case_type=case_type,
        run_status="FAIL",
        total_cost=0.0,
        selected_warehouses=[],
        plant_warehouse_routes=empty_frames["plant_warehouse_routes"],
        warehouse_summary=empty_frames["warehouse_summary"],
        warehouse_customer_routes=empty_frames["warehouse_customer_routes"],
        coverage_detail=empty_frames["coverage_detail"],
        precheck_issues=issues_df,
        summary=summary,
    )
