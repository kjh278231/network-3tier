from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd


@dataclass
class CaseData:
    case_name: str
    case_type: str
    summary: dict
    warehouse_summary: list[dict]
    plant_warehouse_routes: list[dict]
    warehouse_customer_routes: list[dict]
    coverage_details: list[dict]


@dataclass
class RunData:
    format: Literal["cli", "web_run"]
    run_dir: Path
    simulation: dict
    plants: list[dict]
    warehouses: list[dict]
    customers: list[dict]
    plant_warehouse_arcs: list[dict]
    warehouse_customer_arcs: list[dict]
    summary_rows: list[dict]
    cases: list[CaseData]
    run_meta: dict = field(default_factory=dict)

    def best_case(self) -> CaseData:
        best_name = self.run_meta.get("best_case") or self.run_meta.get("bestCaseName", "best_model")
        for c in self.cases:
            if c.case_name == best_name:
                return c
        return self.cases[0]


def _detect_format(run_dir: Path) -> Literal["cli", "web_run"]:
    if (run_dir / "meta.json").exists() and (run_dir / "input.json").exists():
        return "web_run"
    if (run_dir / "run_summary.json").exists():
        return "cli"
    raise ValueError(
        f"Cannot detect run format in {run_dir}. "
        "Expected 'run_summary.json' (CLI) or 'meta.json'+'input.json' (web_run)."
    )


def _load_input_json(run_dir: Path) -> dict:
    path = run_dir / "input.json"
    if not path.exists():
        raise FileNotFoundError(f"input.json not found in {run_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_xls_sheet(path: Path, sheet_name: str) -> list[dict]:
    df = pd.read_excel(path, sheet_name=sheet_name, header=0, engine="xlrd")
    df = df.dropna(how="all").reset_index(drop=True)
    return df.to_dict(orient="records")


def _load_cli(run_dir: Path) -> RunData:
    meta = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    input_payload = _load_input_json(run_dir)

    summary_path = run_dir / "output_summary.xls"
    summary_rows = _read_xls_sheet(summary_path, "summary") if summary_path.exists() else []

    case_count = int(meta.get("case_count", 1))
    cases: list[CaseData] = []
    for idx in range(1, case_count + 1):
        case_path = run_dir / f"output_case{idx}.xls"
        if not case_path.exists():
            continue
        summary_sheet = _read_xls_sheet(case_path, "summary")
        case_summary = summary_sheet[0] if summary_sheet else {}
        cases.append(
            CaseData(
                case_name=str(case_summary.get("Case Name", f"case_{idx}")),
                case_type=str(case_summary.get("Case Type", "unknown")),
                summary=case_summary,
                warehouse_summary=_read_xls_sheet(case_path, "warehouse"),
                plant_warehouse_routes=_read_xls_sheet(case_path, "plantWarehouseRoute"),
                warehouse_customer_routes=_read_xls_sheet(case_path, "warehouseCustomerRoute"),
                coverage_details=_read_xls_sheet(case_path, "coverageDetail"),
            )
        )

    sim_row = input_payload.get("simulation", [{}])[0]
    simulation = {
        "simulationName": sim_row.get("simulationName", ""),
        "warehouseQty": sim_row.get("warehouseQty", 0),
        "speedKmh": sim_row.get("speedKmh", 0),
        "coverageHours": sim_row.get("coverageHours", 0),
    }

    return RunData(
        format="cli",
        run_dir=run_dir,
        simulation=simulation,
        plants=input_payload.get("plants", []),
        warehouses=input_payload.get("warehouses", []),
        customers=input_payload.get("customers", []),
        plant_warehouse_arcs=input_payload.get("plantWarehouseArcs", []),
        warehouse_customer_arcs=input_payload.get("warehouseCustomerArcs", []),
        summary_rows=summary_rows,
        cases=cases,
        run_meta=meta,
    )


def _normalize_case_summary(row: dict) -> dict:
    """Normalize web_run camelCase summary fields to match CLI column names."""
    return {
        "Case Name": row.get("caseName", ""),
        "Case Type": row.get("caseType", ""),
        "Total Rank": row.get("totalRank"),
        "Cost Rank": row.get("costRank"),
        "Optimal Cost": row.get("optimalCost"),
        "Optimal Total Inbound Qty": row.get("optimalTotalInboundQty"),
        "Optimal Total Outbound Qty": row.get("optimalTotalOutboundQty"),
        "Inbound Cost": row.get("inboundCost"),
        "Warehouse Cost": row.get("warehouseCost"),
        "Outbound Cost": row.get("outboundCost"),
        "Lead Time Rank": row.get("leadTimeRank"),
        "Optimal Lead Time (Sec.)": row.get("optimalLeadTimeSec"),
        "Inbound Lead Time (Sec.)": row.get("inboundLeadTimeSec"),
        "Outbound Lead Time (Sec.)": row.get("outboundLeadTimeSec"),
        "Coverage Rank(Time)": row.get("coverageRankTime"),
        "Coverage Time (%)": row.get("coverageTimePct"),
        "Coverage Rank(Vol)": row.get("coverageRankVol"),
        "Coverage Vol (%)": row.get("coverageVolPct"),
        "Cost Score": row.get("costScore"),
        "Lead Time Score": row.get("leadTimeScore"),
        "Coverage Time Score": row.get("coverageTimeScore"),
        "Coverage Vol Score": row.get("coverageVolScore"),
        "Coverage Score": row.get("coverageScore"),
        "Total Score": row.get("totalScore"),
        "Selected Warehouse Count": row.get("selectedWarehouseCount"),
        "Selected Warehouses": ",".join(row.get("selectedWarehouses", [])),
    }


def _normalize_warehouse_summary(rows: list[dict]) -> list[dict]:
    normalized = []
    for r in rows:
        normalized.append({
            "Warehouse Id": r.get("warehouseId", ""),
            "Warehouse Location Name": r.get("warehouseLocationName", ""),
            "Inbound Qty": r.get("inboundQty"),
            "Outbound Qty": r.get("outboundQty"),
            "Throughput Capacity Qty": r.get("throughputCapacityQty"),
            "Fixed Cost": r.get("fixedCost"),
            "Operation Cost": r.get("operationCost"),
            "Assigned Customer Count": r.get("assignedCustomerCount"),
            "Covered Customer Pct": r.get("coveredCustomerPct"),
            "Covered DoQty Pct": r.get("coveredDoQtyPct"),
        })
    return normalized


def _normalize_pw_routes(rows: list[dict]) -> list[dict]:
    normalized = []
    for r in rows:
        normalized.append({
            "Plant Id": r.get("plantId", ""),
            "Plant Location Name": r.get("plantLocationName", ""),
            "Warehouse Id": r.get("warehouseId", ""),
            "Warehouse Location Name": r.get("warehouseLocationName", ""),
            "Do Qty": r.get("doQty"),
            "Cost": r.get("cost"),
            "Shipment Qty Ratio": r.get("shipmentQtyRatio"),
            "Lead Time (Sec.)": r.get("leadTimeSec"),
            "Distance (km)": r.get("distanceKm"),
        })
    return normalized


def _normalize_wc_routes(rows: list[dict]) -> list[dict]:
    normalized = []
    for r in rows:
        normalized.append({
            "Warehouse Id": r.get("warehouseId", ""),
            "Warehouse Location Name": r.get("warehouseLocationName", ""),
            "Customer Id": r.get("customerId", ""),
            "Customer Location Name": r.get("customerLocationName", ""),
            "Do Qty": r.get("doQty"),
            "Cost": r.get("cost"),
            "Shipment Qty": r.get("shipmentQty"),
            "Lead Time (Sec.)": r.get("leadTimeSec"),
            "Distance (km)": r.get("distanceKm"),
            "One-way Time (Sec.)": r.get("oneWayTimeSec"),
            "Coverage YN": r.get("coverageYn", ""),
            "Operation Cost": r.get("operationCost"),
        })
    return normalized


def _normalize_coverage(rows: list[dict]) -> list[dict]:
    normalized = []
    for r in rows:
        normalized.append({
            "Warehouse Id": r.get("warehouseId", ""),
            "Customer Id": r.get("customerId", ""),
            "Assigned Do Qty": r.get("assignedDoQty"),
            "Customer Shipment Qty": r.get("customerShipmentQty"),
            "Plant-Warehouse Lead Time (Sec.)": r.get("plantWarehouseLeadTimeSec"),
            "Warehouse-Customer Lead Time (Sec.)": r.get("warehouseCustomerLeadTimeSec"),
            "Total Lead Time (Sec.)": r.get("totalLeadTimeSec"),
            "Coverage Hour": r.get("coverageHour"),
            "One-way Time (Sec.)": r.get("oneWayTimeSec"),
            "Coverage YN": r.get("coverageYn", ""),
        })
    return normalized


def _load_web_run(run_dir: Path) -> RunData:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    input_payload = _load_input_json(run_dir)

    summary_path = run_dir / "summary.json"
    raw_summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    summary_rows = [_normalize_case_summary(r) for r in raw_summary.get("rows", [])]

    cases_index_path = run_dir / "cases.json"
    cases_index = json.loads(cases_index_path.read_text(encoding="utf-8")) if cases_index_path.exists() else {"cases": []}
    cases_dir = run_dir / "cases"

    cases: list[CaseData] = []
    for entry in cases_index.get("cases", []):
        case_path = cases_dir / f"{entry['caseName']}.json"
        if not case_path.exists():
            continue
        data = json.loads(case_path.read_text(encoding="utf-8"))
        case_summary = _normalize_case_summary(data.get("summary", data))
        cases.append(
            CaseData(
                case_name=entry["caseName"],
                case_type=entry.get("caseType", ""),
                summary=case_summary,
                warehouse_summary=_normalize_warehouse_summary(data.get("warehouseSummary", [])),
                plant_warehouse_routes=_normalize_pw_routes(data.get("plantWarehouseRoutes", [])),
                warehouse_customer_routes=_normalize_wc_routes(data.get("warehouseCustomerRoutes", [])),
                coverage_details=_normalize_coverage(data.get("coverageDetails", [])),
            )
        )

    sim_row = input_payload.get("simulation", [{}])[0]
    simulation = {
        "simulationName": sim_row.get("simulationName", ""),
        "warehouseQty": sim_row.get("warehouseQty", 0),
        "speedKmh": sim_row.get("speedKmh", 0),
        "coverageHours": sim_row.get("coverageHours", 0),
    }

    return RunData(
        format="web_run",
        run_dir=run_dir,
        simulation=simulation,
        plants=input_payload.get("plants", []),
        warehouses=input_payload.get("warehouses", []),
        customers=input_payload.get("customers", []),
        plant_warehouse_arcs=input_payload.get("plantWarehouseArcs", []),
        warehouse_customer_arcs=input_payload.get("warehouseCustomerArcs", []),
        summary_rows=summary_rows,
        cases=cases,
        run_meta=meta,
    )


def load_run(run_dir: Path) -> RunData:
    fmt = _detect_format(run_dir)
    if fmt == "cli":
        return _load_cli(run_dir)
    return _load_web_run(run_dir)
