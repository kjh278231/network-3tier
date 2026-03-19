from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..domain import CaseResult, NetworkData


def _normalize_scalar(value):
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def dataframe_to_records(frame: pd.DataFrame, rename: dict[str, str] | None = None) -> list[dict]:
    working = frame.copy()
    if rename:
        working = working.rename(columns=rename)
    records = []
    for row in working.to_dict(orient="records"):
        records.append({str(key): _normalize_scalar(value) for key, value in row.items()})
    return records


def simulation_to_dict(data: NetworkData) -> dict:
    return {
        "simulationName": data.simulation.simulation_name,
        "structure": data.simulation.structure,
        "warehouseQty": data.simulation.warehouse_qty,
        "speedKmh": data.simulation.speed_kmh,
        "coverageHours": data.simulation.coverage_hours,
    }


def case_summary_row(case: CaseResult) -> dict:
    row = case.summary.iloc[0].to_dict()
    selected = row.get("Selected Warehouses")
    warehouses = [item for item in str(selected).split(",") if item] if selected else []
    return {
        "caseName": row["Case Name"],
        "caseType": row["Case Type"],
        "totalRank": row["Total Rank"],
        "costRank": row["Cost Rank"],
        "optimalCost": row["Optimal Cost"],
        "optimalTotalInboundQty": row["Optimal Total Inbound Qty"],
        "optimalTotalOutboundQty": row["Optimal Total Outbound Qty"],
        "inboundCost": row["Inbound Cost"],
        "warehouseCost": row["Warehouse Cost"],
        "outboundCost": row["Outbound Cost"],
        "leadTimeRank": row["Lead Time Rank"],
        "optimalLeadTimeSec": row["Optimal Lead Time (Sec.)"],
        "inboundLeadTimeSec": row["Inbound Lead Time (Sec.)"],
        "outboundLeadTimeSec": row["Outbound Lead Time (Sec.)"],
        "coverageRankTime": row["Coverage Rank(Time)"],
        "coverageTimePct": row["Coverage Time (%)"],
        "coverageRankVol": row["Coverage Rank(Vol)"],
        "coverageVolPct": row["Coverage Vol (%)"],
        "costScore": row["Cost Score"],
        "leadTimeScore": row["Lead Time Score"],
        "coverageTimeScore": row["Coverage Time Score"],
        "coverageVolScore": row["Coverage Vol Score"],
        "coverageScore": row["Coverage Score"],
        "totalScore": row["Total Score"],
        "selectedWarehouseCount": row["Selected Warehouse Count"],
        "selectedWarehouses": warehouses,
        "carbonEmissionTco2eq": row["Carbon Emission(tCO2-eq)"],
    }


def build_warehouse_summary(case: CaseResult, coverage_detail: pd.DataFrame) -> list[dict]:
    covered_customers = (
        coverage_detail.groupby("Warehouse Id")["Coverage YN"].apply(lambda s: float((s == "Y").mean() * 100.0))
        if not coverage_detail.empty
        else pd.Series(dtype=float)
    )
    covered_doqty = (
        coverage_detail.assign(_covered=coverage_detail["Coverage YN"] == "Y")
        .groupby("Warehouse Id")[["Assigned Do Qty", "_covered"]]
        .apply(
            lambda df: float(
                df.loc[df["_covered"], "Assigned Do Qty"].sum() / df["Assigned Do Qty"].sum() * 100.0
            )
            if float(df["Assigned Do Qty"].sum()) > 0
            else 0.0
        )
        if not coverage_detail.empty
        else pd.Series(dtype=float)
    )
    customer_counts = (
        case.warehouse_customer_routes.groupby("Warehouse Id")["Customer Id"].nunique()
        if not case.warehouse_customer_routes.empty
        else pd.Series(dtype=int)
    )
    rows = []
    for row in case.warehouse_summary.to_dict(orient="records"):
        capacity = float(row["Throughput Capacity Qty"]) if row["Throughput Capacity Qty"] else 0.0
        outbound = float(row["Outbound Qty"])
        warehouse_id = str(row["Warehouse Id"])
        rows.append(
            {
                "warehouseId": warehouse_id,
                "warehouseLocationName": row["Warehouse Location Name"],
                "inboundQty": float(row["Inbound Qty"]),
                "outboundQty": outbound,
                "throughputCapacityQty": capacity,
                "capacityUtilizationPct": (outbound / capacity * 100.0) if capacity else 0.0,
                "fixedCost": float(row["Fixed Cost"]),
                "operationCost": float(row["Operation Cost"]),
                "assignedCustomerCount": int(customer_counts.get(warehouse_id, 0)),
                "coveredCustomerPct": float(covered_customers.get(warehouse_id, 0.0)),
                "coveredDoQtyPct": float(covered_doqty.get(warehouse_id, 0.0)),
            }
        )
    return rows


def build_case_payload(case: CaseResult, data: NetworkData) -> dict:
    customer_mapping = (
        data.customers.set_index("Customer ID")["Mapping ID"].to_dict()
        if "Mapping ID" in data.customers.columns
        else {}
    )
    wc_rows = []
    for row in case.warehouse_customer_routes.to_dict(orient="records"):
        customer_id = str(row["Customer Id"])
        wc_rows.append(
            {
                "warehouseId": row["Warehouse Id"],
                "warehouseLocationName": row["Warehouse Location Name"],
                "customerId": customer_id,
                "customerLocationName": row["Customer Location Name"],
                "doQty": float(row["Do Qty"]),
                "cost": float(row["Cost"]),
                "shipmentQty": float(row["Shipment Qty"]),
                "leadTimeSec": float(row["Lead Time (Sec.)"]),
                "distanceKm": float(row["Distance (km)"]),
                "oneWayTimeSec": float(row["One-way Time (Sec.)"]),
                "coverageYn": row["Coverage YN"],
                "operationCost": float(row["Operation Cost"]),
                "carbonEmissionTco2eq": float(row["Carbon Emission(tCO2-eq)"]),
                "mappingId": customer_mapping.get(customer_id),
            }
        )

    return {
        "summary": case_summary_row(case),
        "warehouseSummary": build_warehouse_summary(case, case.coverage_detail),
        "plantWarehouseRoutes": dataframe_to_records(
            case.plant_warehouse_routes,
            {
                "Plant Id": "plantId",
                "Plant Location Name": "plantLocationName",
                "Warehouse Id": "warehouseId",
                "Warehouse Location Name": "warehouseLocationName",
                "Do Qty": "doQty",
                "Cost": "cost",
                "Shipment Qty Ratio": "shipmentQtyRatio",
                "Lead Time (Sec.)": "leadTimeSec",
                "Distance (km)": "distanceKm",
                "Carbon Emission(tCO2-eq)": "carbonEmissionTco2eq",
            },
        ),
        "warehouseCustomerRoutes": wc_rows,
        "coverageDetails": dataframe_to_records(
            case.coverage_detail,
            {
                "Warehouse Id": "warehouseId",
                "Customer Id": "customerId",
                "Assigned Do Qty": "assignedDoQty",
                "Customer Shipment Qty": "customerShipmentQty",
                "Plant-Warehouse Lead Time (Sec.)": "plantWarehouseLeadTimeSec",
                "Warehouse-Customer Lead Time (Sec.)": "warehouseCustomerLeadTimeSec",
                "Total Lead Time (Sec.)": "totalLeadTimeSec",
                "Coverage Hour": "coverageHour",
                "One-way Time (Sec.)": "oneWayTimeSec",
                "Coverage YN": "coverageYn",
            },
        ),
    }


def build_input_payload(data: NetworkData) -> dict:
    return {
        "simulation": [
            {
                "simulationName": data.simulation.simulation_name,
                "status": None,
                "structure": data.simulation.structure,
                "warehouseQty": data.simulation.warehouse_qty,
                "speedKmh": data.simulation.speed_kmh,
                "coverageHours": data.simulation.coverage_hours,
            }
        ],
        "plants": dataframe_to_records(
            data.plants,
            {
                "Plant ID": "plantId",
                "Location Name": "locationName",
                "Latitude": "latitude",
                "Longitude": "longitude",
                "Product Qty": "productQty",
                "Shipment Qty": "shipmentQty",
            },
        ),
        "warehouses": dataframe_to_records(
            data.warehouses.assign(Included=True),
            {
                "Warehouse ID": "warehouseId",
                "Location Name": "locationName",
                "Latitude": "latitude",
                "Longitude": "longitude",
                "Capacity Qty": "capacityQty",
                "Fixed Cost": "fixedCost",
                "Operation Cost": "operationCost",
                "Active Y/N": "activeYn",
                "Included": "includedInModel",
            },
        ),
        "customers": dataframe_to_records(
            data.customers,
            {
                "Customer ID": "customerId",
                "Location Name": "locationName",
                "Latitude": "latitude",
                "Longitude": "longitude",
                "Do Qty": "doQty",
                "Shipment Qty": "shipmentQty",
                "Mapping ID": "mappingId",
            },
        ),
        "plantWarehouseArcs": dataframe_to_records(
            data.plant_warehouse_cost,
            {
                "Plant ID": "plantId",
                "Warehouse ID": "warehouseId",
                "Distance (km)": "distanceKm",
                "Distance Type": "distanceType",
                "Trns Cost": "trnsCost",
            },
        ),
        "warehouseCustomerArcs": dataframe_to_records(
            data.warehouse_customer_cost,
            {
                "Warehouse ID": "warehouseId",
                "Customer ID": "customerId",
                "Distance (km)": "distanceKm",
                "Distance Type": "distanceType",
                "Trns Cost": "trnsCost",
            },
        ),
    }


def load_json(path: Path):
    import json

    return json.loads(path.read_text(encoding="utf-8"))
