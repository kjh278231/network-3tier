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
    customer_mapping = get_customer_mapping_requirements(data)

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

    if data.simulation.warehouse_qty <= 0:
        errors.append("Simulation warehouse qty must be positive.")
    if customer_mapping and "Mapping ID" not in data.customers.columns:
        errors.append("Customer Mapping ID normalization failed.")

    if errors:
        raise DataValidationError("\n".join(errors))

    LOGGER.info("Validation passed")
