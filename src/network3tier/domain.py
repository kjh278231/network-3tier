from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SimulationConfig:
    simulation_name: str
    structure: str
    warehouse_qty: int
    speed_kmh: float
    coverage_hours: float


@dataclass
class NetworkData:
    simulation: SimulationConfig
    plants: pd.DataFrame
    warehouses: pd.DataFrame
    customers: pd.DataFrame
    plant_warehouse_cost: pd.DataFrame
    warehouse_customer_cost: pd.DataFrame


@dataclass(frozen=True)
class PrecheckIssue:
    issue_id: str
    category: str
    severity: str
    certainty: str
    description: str
    evidence: str


@dataclass
class PrecheckResult:
    precheck_passed: bool
    fail_fast: bool
    issues: list[PrecheckIssue]
    metrics: dict[str, float | int | str]


@dataclass
class CaseResult:
    case_name: str
    case_type: str
    run_status: str
    total_cost: float
    selected_warehouses: list[str]
    plant_warehouse_routes: pd.DataFrame
    warehouse_summary: pd.DataFrame
    warehouse_customer_routes: pd.DataFrame
    coverage_detail: pd.DataFrame
    precheck_issues: pd.DataFrame
    summary: pd.DataFrame
