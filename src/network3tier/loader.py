from __future__ import annotations

from pathlib import Path

import pandas as pd

from .domain import NetworkData, SimulationConfig
from .logging_utils import get_logger


HEADER_ROW_INDEX = 4
HEADER_START_COL = 1


class DataValidationError(Exception):
    pass


LOGGER = get_logger()


def load_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header = raw.iloc[HEADER_ROW_INDEX, HEADER_START_COL:].tolist()
    frame = raw.iloc[
        HEADER_ROW_INDEX + 1 :, HEADER_START_COL : HEADER_START_COL + len(header)
    ].copy()
    frame.columns = header
    return frame.dropna(how="all").reset_index(drop=True)


def normalize_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def normalize_mapping_id(series: pd.Series) -> pd.Series:
    normalized = series.fillna("").astype(str).str.strip()
    return normalized.where(normalized != "", pd.NA)


def is_integral_series(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce")
    return bool(((numeric.dropna() % 1) == 0).all())


def get_customer_mapping_requirements(data: NetworkData) -> dict[str, str]:
    if "Mapping ID" not in data.customers.columns:
        return {}

    mapped = data.customers[["Customer ID", "Mapping ID"]].dropna(subset=["Mapping ID"]).copy()
    if mapped.empty:
        return {}
    return {
        str(row["Customer ID"]): str(row["Mapping ID"]).strip()
        for _, row in mapped.iterrows()
        if str(row["Mapping ID"]).strip()
    }


def load_network_data(path: Path) -> NetworkData:
    LOGGER.info("Loading workbook: %s", path)
    simulation_df = load_sheet(path, "simulation")
    plants = load_sheet(path, "plant")
    warehouses = load_sheet(path, "warehouse")
    customers = load_sheet(path, "customer")
    plant_warehouse_cost = load_sheet(path, "plantWarehouseCost")
    warehouse_customer_cost = load_sheet(path, "warehouseCustomerCost")

    for frame, numeric_columns in [
        (simulation_df, ["Warehouse Qty", "Speed (km/h)", "Coverage (hour)"]),
        (plants, ["Product Qty", "Shipment Qty", "Latitude", "Longitude"]),
        (warehouses, ["Capacity Qty", "Fixed Cost", "Operation Cost", "Latitude", "Longitude"]),
        (customers, ["Do Qty", "Shipment Qty", "Latitude", "Longitude"]),
        (plant_warehouse_cost, ["Distance (km)", "Trns Cost"]),
        (warehouse_customer_cost, ["Distance (km)", "Trns Cost"]),
    ]:
        for column in numeric_columns:
            if column in frame.columns:
                frame[column] = normalize_numeric(frame[column])

    warehouses["Active Y/N"] = warehouses["Active Y/N"].astype(str).str.strip().str.upper()
    warehouses = warehouses[warehouses["Active Y/N"] == "Y"].reset_index(drop=True)
    if "Mapping ID" in customers.columns:
        customers["Mapping ID"] = normalize_mapping_id(customers["Mapping ID"])

    if simulation_df.empty:
        raise DataValidationError("No simulation rows found.")

    simulation = SimulationConfig(
        simulation_name=str(simulation_df.iloc[0]["Simulation Name"]),
        structure=str(simulation_df.iloc[0]["Structure"]),
        warehouse_qty=int(simulation_df.iloc[0]["Warehouse Qty"]),
        speed_kmh=float(simulation_df.iloc[0]["Speed (km/h)"]),
        coverage_hours=float(simulation_df.iloc[0]["Coverage (hour)"]),
    )

    LOGGER.info(
        "Loaded %d plant(s), %d active warehouse(s), %d customer(s)",
        len(plants),
        len(warehouses),
        len(customers),
    )

    return NetworkData(
        simulation=simulation,
        plants=plants,
        warehouses=warehouses,
        customers=customers,
        plant_warehouse_cost=plant_warehouse_cost,
        warehouse_customer_cost=warehouse_customer_cost,
    )


def validate_network_data(data: NetworkData) -> None:
    LOGGER.info("Validating input data")
    errors: list[str] = []

    total_demand = float(data.customers["Do Qty"].sum())
    total_capacity = float(data.warehouses["Capacity Qty"].sum())
    total_supply = float(data.plants["Product Qty"].sum())
    customer_mapping = get_customer_mapping_requirements(data)

    if data.plants.empty:
        errors.append("No plant rows found.")
    if data.warehouses.empty:
        errors.append("No active warehouse rows found.")
    if data.customers.empty:
        errors.append("No customer rows found.")
    if data.simulation.warehouse_qty > len(data.warehouses):
        errors.append(
            f"Simulation warehouse qty ({data.simulation.warehouse_qty}) exceeds active warehouse count ({len(data.warehouses)})."
        )
    if total_demand > total_capacity:
        errors.append(
            f"Total Do Qty ({total_demand}) exceeds total active warehouse capacity ({total_capacity})."
        )
    if total_demand > total_supply:
        errors.append(
            f"Total Do Qty ({total_demand}) exceeds plant Product Qty ({total_supply})."
        )
    if data.simulation.warehouse_qty < len(set(customer_mapping.values())):
        errors.append(
            "Simulation warehouse qty "
            f"({data.simulation.warehouse_qty}) is smaller than required mapped warehouse count "
            f"({len(set(customer_mapping.values()))})."
        )

    integral_checks = [
        ("plant.Product Qty", data.plants["Product Qty"]),
        ("plant.Shipment Qty", data.plants["Shipment Qty"]),
        ("warehouse.Capacity Qty", data.warehouses["Capacity Qty"]),
        ("customer.Do Qty", data.customers["Do Qty"]),
        ("customer.Shipment Qty", data.customers["Shipment Qty"]),
    ]
    for label, series in integral_checks:
        if not is_integral_series(series):
            errors.append(f"{label} must be integer-valued for the current IR/model semantics.")

    wh_ids = set(data.warehouses["Warehouse ID"])
    cust_ids = set(data.customers["Customer ID"])
    plant_ids = set(data.plants["Plant ID"])

    pw_wh_ids = set(data.plant_warehouse_cost["Warehouse ID"])
    pw_plant_ids = set(data.plant_warehouse_cost["Plant ID"])
    wc_wh_ids = set(data.warehouse_customer_cost["Warehouse ID"])
    wc_cust_ids = set(data.warehouse_customer_cost["Customer ID"])

    missing_pw_plant = sorted(plant_ids - pw_plant_ids)
    missing_pw_wh = sorted(wh_ids - pw_wh_ids)
    missing_wc_wh = sorted(wh_ids - wc_wh_ids)
    missing_wc_cust = sorted(cust_ids - wc_cust_ids)

    if missing_pw_plant:
        errors.append(f"Plants missing plant->warehouse cost rows: {missing_pw_plant}")
    if missing_pw_wh:
        errors.append(
            f"Warehouses missing plant->warehouse cost rows ({len(missing_pw_wh)}): {missing_pw_wh[:10]}"
        )
    if missing_wc_wh:
        errors.append(
            f"Warehouses missing warehouse->customer cost rows ({len(missing_wc_wh)}): {missing_wc_wh[:10]}"
        )
    if missing_wc_cust:
        errors.append(
            f"Customers missing warehouse->customer cost rows ({len(missing_wc_cust)}): {missing_wc_cust[:10]}"
        )

    coverage = data.warehouse_customer_cost.groupby("Customer ID")["Warehouse ID"].nunique()
    uncovered_customers = sorted(cust_ids - set(coverage.index))
    if uncovered_customers:
        errors.append(
            f"Customers without any eligible warehouse assignment ({len(uncovered_customers)}): {uncovered_customers[:10]}"
        )

    mapped_wh_ids = set(customer_mapping.values())
    missing_mapped_wh = sorted(mapped_wh_ids - wh_ids)
    if missing_mapped_wh:
        errors.append(
            f"Mapping ID references inactive or missing warehouses ({len(missing_mapped_wh)}): {missing_mapped_wh[:10]}"
        )

    missing_mapping_arcs: list[str] = []
    wc_pairs = set(
        zip(
            data.warehouse_customer_cost["Warehouse ID"].astype(str),
            data.warehouse_customer_cost["Customer ID"].astype(str),
        )
    )
    for customer_id, warehouse_id in customer_mapping.items():
        if (warehouse_id, customer_id) not in wc_pairs:
            missing_mapping_arcs.append(f"{customer_id}->{warehouse_id}")
    if missing_mapping_arcs:
        errors.append(
            "Mapped customers missing required warehouse->customer cost rows "
            f"({len(missing_mapping_arcs)}): {missing_mapping_arcs[:10]}"
        )

    if errors:
        raise DataValidationError("\n".join(errors))

    LOGGER.info("Validation passed")
