import { useEffect, useMemo, useRef, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { CircleMarker, MapContainer, Pane, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { useParams, useSearchParams } from "react-router-dom";
import type {
  CustomerInputRow,
  PlantInputRow,
  PlantWarehouseRouteRow,
  WarehouseCustomerRouteRow,
  WarehouseInputRow,
} from "../api";
import {
  getCustomerInput,
  getPlantInput,
  getPlantWarehouseRoutes,
  getSummary,
  getWarehouseCustomerRoutes,
  getWarehouseInput,
} from "../api";
import { Card, DataTable, PageHeader } from "../components";

type SelectedItem =
  | { type: "plant"; payload: PlantInputRow }
  | { type: "warehouse"; payload: WarehouseInputRow }
  | { type: "customer"; payload: CustomerInputRow }
  | { type: "pwRoute"; payload: PlantWarehouseRouteRow }
  | { type: "wcRoute"; payload: WarehouseCustomerRouteRow }
  | null;

function FitToMarkers({ points, fitKey }: { points: Array<[number, number]>; fitKey: string }) {
  const map = useMap();
  const lastFitKeyRef = useRef<string | null>(null);
  useEffect(() => {
    if (!points.length) return;
    if (lastFitKeyRef.current === fitKey) return;
    lastFitKeyRef.current = fitKey;
    map.fitBounds(points, { padding: [40, 40] });
  }, [fitKey, map, points]);
  return null;
}

export function MapPage() {
  const { runId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [showPlants, setShowPlants] = useState(true);
  const [showWarehouses, setShowWarehouses] = useState(true);
  const [showCustomers, setShowCustomers] = useState(false);
  const [showPwRoutes, setShowPwRoutes] = useState(true);
  const [showWcRoutes, setShowWcRoutes] = useState(false);
  const [coverageOnly, setCoverageOnly] = useState(false);
  const [selected, setSelected] = useState<SelectedItem>(null);

  const summaryQuery = useQuery({
    queryKey: ["run", runId, "summary"],
    queryFn: () => getSummary(runId),
  });
  const caseName = searchParams.get("case") ?? summaryQuery.data?.rows[0]?.caseName ?? "";

  const [plantsQuery, warehousesQuery, customersQuery, pwRoutesQuery, wcRoutesQuery] = useQueries({
    queries: [
      { queryKey: ["run", runId, "plants"], queryFn: () => getPlantInput(runId), enabled: Boolean(runId) },
      { queryKey: ["run", runId, "warehouses"], queryFn: () => getWarehouseInput(runId), enabled: Boolean(runId) },
      { queryKey: ["run", runId, "customers"], queryFn: () => getCustomerInput(runId), enabled: Boolean(runId) },
      {
        queryKey: ["run", runId, "case", caseName, "pw-routes"],
        queryFn: () => getPlantWarehouseRoutes(runId, caseName),
        enabled: Boolean(runId && caseName),
      },
      {
        queryKey: ["run", runId, "case", caseName, "wc-routes"],
        queryFn: () => getWarehouseCustomerRoutes(runId, caseName),
        enabled: Boolean(runId && caseName),
      },
    ],
  });

  const plants = plantsQuery.data?.rows ?? [];
  const warehouses = warehousesQuery.data?.rows ?? [];
  const customers = customersQuery.data?.rows ?? [];
  const pwRoutes = pwRoutesQuery.data?.rows ?? [];
  const wcRoutes = useMemo(() => {
    const rows = wcRoutesQuery.data?.rows ?? [];
    return coverageOnly ? rows.filter((row) => row.coverageYn === "N") : rows;
  }, [coverageOnly, wcRoutesQuery.data?.rows]);

  const plantsById = useMemo(() => new Map(plants.map((row) => [row.plantId, row])), [plants]);
  const warehousesById = useMemo(() => new Map(warehouses.map((row) => [row.warehouseId, row])), [warehouses]);
  const customersById = useMemo(() => new Map(customers.map((row) => [row.customerId, row])), [customers]);

  const markerPoints = useMemo(() => {
    const points: Array<[number, number]> = [];
    for (const row of plants) points.push([row.latitude, row.longitude]);
    for (const row of warehouses) points.push([row.latitude, row.longitude]);
    if (showCustomers) {
      for (const row of customers) points.push([row.latitude, row.longitude]);
    }
    return points;
  }, [customers, plants, showCustomers, warehouses]);

  const detailRows = useMemo(() => {
    if (!selected) return [];
    return [selected.payload as unknown as Record<string, unknown>];
  }, [selected]);

  const loading =
    summaryQuery.isLoading ||
    plantsQuery.isLoading ||
    warehousesQuery.isLoading ||
    customersQuery.isLoading ||
    pwRoutesQuery.isLoading ||
    wcRoutesQuery.isLoading;
  const error =
    summaryQuery.error ||
    plantsQuery.error ||
    warehousesQuery.error ||
    customersQuery.error ||
    pwRoutesQuery.error ||
    wcRoutesQuery.error;

  return (
    <div className="page-section">
      <PageHeader title="Network Map" subtitle="OSM 기반 지도에서 plant, warehouse, customer, route를 공간적으로 분석합니다." />
      <Card>
        <div className="map-toolbar">
          <label className="inline-field">
            <span>Case</span>
            <select
              value={caseName}
              onChange={(event) => {
                const next = new URLSearchParams(searchParams);
                next.set("case", event.target.value);
                setSearchParams(next);
              }}
            >
              {(summaryQuery.data?.rows ?? []).map((row) => (
                <option key={row.caseName} value={row.caseName}>
                  {row.caseName}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox-field">
            <input type="checkbox" checked={showPlants} onChange={() => setShowPlants((value) => !value)} />
            Plants
          </label>
          <label className="checkbox-field">
            <input type="checkbox" checked={showWarehouses} onChange={() => setShowWarehouses((value) => !value)} />
            Warehouses
          </label>
          <label className="checkbox-field">
            <input type="checkbox" checked={showCustomers} onChange={() => setShowCustomers((value) => !value)} />
            Customers
          </label>
          <label className="checkbox-field">
            <input type="checkbox" checked={showPwRoutes} onChange={() => setShowPwRoutes((value) => !value)} />
            P→W Routes
          </label>
          <label className="checkbox-field">
            <input type="checkbox" checked={showWcRoutes} onChange={() => setShowWcRoutes((value) => !value)} />
            W→C Routes
          </label>
          <label className="checkbox-field">
            <input type="checkbox" checked={coverageOnly} onChange={() => setCoverageOnly((value) => !value)} />
            Low Coverage Only
          </label>
        </div>
      </Card>
      <div className="map-layout">
        <Card className="map-card">
          {loading ? <div>Loading map...</div> : null}
          {error ? <div className="error-box">{String(error)}</div> : null}
          {!loading && !error ? (
            <MapContainer center={[13.7563, 100.5018]} zoom={6} className="leaflet-map">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <FitToMarkers points={markerPoints} fitKey={`${runId}:${caseName || "default"}`} />
              <Pane name="pwRoutes" style={{ zIndex: 350 }} />
              <Pane name="wcRoutes" style={{ zIndex: 360 }} />
              {showPwRoutes
                ? pwRoutes.map((route) => {
                    const plant = plantsById.get(route.plantId);
                    const warehouse = warehousesById.get(route.warehouseId);
                    if (!plant || !warehouse) return null;
                    return (
                      <Polyline
                        key={`pw-${route.plantId}-${route.warehouseId}`}
                        positions={[
                          [plant.latitude, plant.longitude],
                          [warehouse.latitude, warehouse.longitude],
                        ]}
                        pathOptions={{ color: "#175e6d", weight: 1 + route.doQty / 2500, opacity: 0.75 }}
                        eventHandlers={{ click: () => setSelected({ type: "pwRoute", payload: route }) }}
                      >
                        <Popup>
                          <strong>
                            {route.plantId} → {route.warehouseId}
                          </strong>
                          <div>Do Qty: {route.doQty}</div>
                          <div>Cost: {route.cost}</div>
                          <div>Lead Time (Sec.): {route.leadTimeSec}</div>
                        </Popup>
                      </Polyline>
                    );
                  })
                : null}
              {showWcRoutes
                ? wcRoutes.map((route) => {
                    const warehouse = warehousesById.get(route.warehouseId);
                    const customer = customersById.get(route.customerId);
                    if (!warehouse || !customer) return null;
                    return (
                      <Polyline
                        key={`wc-${route.warehouseId}-${route.customerId}`}
                        positions={[
                          [warehouse.latitude, warehouse.longitude],
                          [customer.latitude, customer.longitude],
                        ]}
                        pathOptions={{
                          color: route.coverageYn === "Y" ? "#4a8a52" : "#ba563f",
                          weight: 1 + route.doQty / 250,
                          opacity: 0.5,
                        }}
                        eventHandlers={{ click: () => setSelected({ type: "wcRoute", payload: route }) }}
                      >
                        <Popup>
                          <strong>
                            {route.warehouseId} → {route.customerId}
                          </strong>
                          <div>Do Qty: {route.doQty}</div>
                          <div>Cost: {route.cost}</div>
                          <div>Coverage: {route.coverageYn}</div>
                        </Popup>
                      </Polyline>
                    );
                  })
                : null}
              {showPlants
                ? plants.map((plant) => (
                    <CircleMarker
                      key={plant.plantId}
                      center={[plant.latitude, plant.longitude]}
                      radius={10}
                      pathOptions={{ color: "#11343c", fillColor: "#11343c", fillOpacity: 0.85 }}
                      eventHandlers={{ click: () => setSelected({ type: "plant", payload: plant }) }}
                    >
                      <Popup>
                        <strong>{plant.plantId}</strong>
                        <div>{plant.locationName}</div>
                        <div>Product Qty: {plant.productQty}</div>
                      </Popup>
                    </CircleMarker>
                  ))
                : null}
              {showWarehouses
                ? warehouses.map((warehouse) => (
                    <CircleMarker
                      key={warehouse.warehouseId}
                      center={[warehouse.latitude, warehouse.longitude]}
                      radius={7}
                      pathOptions={{ color: "#d08700", fillColor: "#f3b341", fillOpacity: 0.8 }}
                      eventHandlers={{ click: () => setSelected({ type: "warehouse", payload: warehouse }) }}
                    >
                      <Popup>
                        <strong>{warehouse.warehouseId}</strong>
                        <div>{warehouse.locationName}</div>
                        <div>Capacity Qty: {warehouse.capacityQty}</div>
                      </Popup>
                    </CircleMarker>
                  ))
                : null}
              {showCustomers
                ? customers.map((customer) => (
                    <CircleMarker
                      key={customer.customerId}
                      center={[customer.latitude, customer.longitude]}
                      radius={Math.max(3, Math.min(9, customer.doQty / 20))}
                      pathOptions={{ color: "#59616b", fillColor: "#8894a3", fillOpacity: 0.65 }}
                      eventHandlers={{ click: () => setSelected({ type: "customer", payload: customer }) }}
                    >
                      <Popup>
                        <strong>{customer.customerId}</strong>
                        <div>{customer.locationName}</div>
                        <div>Do Qty: {customer.doQty}</div>
                        <div>Mapping ID: {customer.mappingId ?? "-"}</div>
                      </Popup>
                    </CircleMarker>
                  ))
                : null}
            </MapContainer>
          ) : null}
        </Card>
        <Card className="map-side-card">
          <div className="section-title">Selection Detail</div>
          {selected ? (
            <>
              <div className="selection-type">{selected.type}</div>
              <DataTable rows={detailRows} />
            </>
          ) : (
            <div className="empty-state">Click a marker or route to inspect it.</div>
          )}
        </Card>
      </div>
    </div>
  );
}
