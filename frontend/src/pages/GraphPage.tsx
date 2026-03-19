import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import cytoscape from "cytoscape";
import { useParams, useSearchParams } from "react-router-dom";
import {
  getCustomerInput,
  getPlantInput,
  getPlantWarehouseRoutes,
  getSummary,
  getWarehouseCustomerRoutes,
  getWarehouseInput,
  getWarehouseSummary,
  type WarehouseSummaryRow,
} from "../api";
import { Card, PageHeader } from "../components";

type PopupState = {
  x: number;
  y: number;
  data: Record<string, unknown>;
};

function UtilizationPie({ utilizationPct }: { utilizationPct: number }) {
  const safePct = Number.isFinite(utilizationPct) ? Math.max(0, Math.min(100, utilizationPct)) : 0;
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  const dash = (safePct / 100) * circumference;

  return (
    <div className="utilization-pie">
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" r={radius} className="utilization-track" />
        <circle
          cx="32"
          cy="32"
          r={radius}
          className="utilization-fill"
          strokeDasharray={`${dash} ${circumference - dash}`}
          transform="rotate(-90 32 32)"
        />
      </svg>
      <div className="utilization-label">
        <strong>{safePct.toFixed(1)}%</strong>
        <span>Capacity</span>
      </div>
    </div>
  );
}

function PopupRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="graph-popup-row">
      <span>{label}</span>
      <strong>{String(value ?? "-")}</strong>
    </div>
  );
}

function GraphPopup({ popup }: { popup: PopupState }) {
  const type = String(popup.data.type ?? "");
  const utilizationPct =
    typeof popup.data.capacityUtilizationPct === "number"
      ? popup.data.capacityUtilizationPct
      : Number(popup.data.capacityUtilizationPct ?? 0);

  return (
    <div
      className="graph-popup"
      style={{
        left: `${popup.x}px`,
        top: `${popup.y}px`,
      }}
    >
      <div className="graph-popup-title">
        <strong>{String(popup.data.label ?? popup.data.id ?? "Selection")}</strong>
        <span>{type}</span>
      </div>
      {type === "warehouse" ? <UtilizationPie utilizationPct={utilizationPct} /> : null}
      {type === "plant" ? (
        <>
          <PopupRow label="Location" value={popup.data.locationName} />
          <PopupRow label="Product Qty" value={popup.data.productQty} />
          <PopupRow label="Shipment Qty" value={popup.data.shipmentQty} />
        </>
      ) : null}
      {type === "warehouse" ? (
        <>
          <PopupRow label="Location" value={popup.data.locationName} />
          <PopupRow label="Outbound" value={popup.data.outboundQty} />
          <PopupRow label="Capacity" value={popup.data.throughputCapacityQty ?? popup.data.capacityQty} />
          <PopupRow label="Assigned Customers" value={popup.data.assignedCustomerCount} />
        </>
      ) : null}
      {type === "customer" ? (
        <>
          <PopupRow label="Location" value={popup.data.locationName} />
          <PopupRow label="DO Qty" value={popup.data.doQty} />
          <PopupRow label="Shipment Qty" value={popup.data.shipmentQty} />
          <PopupRow label="Mapping ID" value={popup.data.mappingId} />
        </>
      ) : null}
      {type === "pw" ? (
        <>
          <PopupRow label="Plant" value={popup.data.plantId} />
          <PopupRow label="Warehouse" value={popup.data.warehouseId} />
          <PopupRow label="DO Qty" value={popup.data.doQty} />
          <PopupRow label="Cost" value={popup.data.cost} />
          <PopupRow label="Lead Time Sec" value={popup.data.leadTimeSec} />
        </>
      ) : null}
      {type === "wc" ? (
        <>
          <PopupRow label="Warehouse" value={popup.data.warehouseId} />
          <PopupRow label="Customer" value={popup.data.customerId} />
          <PopupRow label="DO Qty" value={popup.data.doQty} />
          <PopupRow label="Cost" value={popup.data.cost} />
          <PopupRow label="Coverage" value={popup.data.coverageYn} />
        </>
      ) : null}
    </div>
  );
}

export function GraphPage() {
  const { runId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [popup, setPopup] = useState<PopupState | null>(null);
  const [warehouseQuery, setWarehouseQuery] = useState(searchParams.get("warehouseQuery") ?? "");
  const [isRendering, setIsRendering] = useState(false);

  const summaryQuery = useQuery({
    queryKey: ["run", runId, "summary"],
    queryFn: () => getSummary(runId),
  });
  const caseName = searchParams.get("case") ?? summaryQuery.data?.rows[0]?.caseName ?? "";
  const layout = searchParams.get("layout") ?? "cose";
  const selectedWarehouseIds = useMemo(
    () =>
      (searchParams.get("warehouse") ?? "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    [searchParams],
  );

  const [plantsQuery, warehousesQuery, customersQuery, pwRoutesQuery, wcRoutesQuery, warehouseSummaryQuery] = useQueries({
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
      {
        queryKey: ["run", runId, "case", caseName, "warehouse-summary"],
        queryFn: () => getWarehouseSummary(runId, caseName),
        enabled: Boolean(runId && caseName),
      },
    ],
  });

  const warehouseOptions = useMemo(() => {
    const warehouses = warehousesQuery.data?.rows ?? [];
    const normalizedQuery = warehouseQuery.trim().toLowerCase();
    return warehouses
      .filter((row) => {
        if (!normalizedQuery) return true;
        return [row.warehouseId, row.locationName].some((value) => String(value ?? "").toLowerCase().includes(normalizedQuery));
      });
  }, [warehouseQuery, warehousesQuery.data?.rows]);

  const elements = useMemo(() => {
    const plants = plantsQuery.data?.rows ?? [];
    const warehouses = warehousesQuery.data?.rows ?? [];
    const customers = customersQuery.data?.rows ?? [];
    const pwRoutes = pwRoutesQuery.data?.rows ?? [];
    const wcRoutes = wcRoutesQuery.data?.rows ?? [];
    const warehouseSummaries = warehouseSummaryQuery.data?.rows ?? [];

    const warehouseSummaryById = new Map<string, WarehouseSummaryRow>(
      warehouseSummaries.map((row) => [row.warehouseId, row]),
    );

    const warehouseFilterActive = selectedWarehouseIds.length > 0;
    const filteredPwRoutes = warehouseFilterActive
      ? pwRoutes.filter((row) => selectedWarehouseIds.includes(row.warehouseId))
      : pwRoutes;
    const filteredWcRoutes = warehouseFilterActive
      ? wcRoutes.filter((row) => selectedWarehouseIds.includes(row.warehouseId))
      : wcRoutes;
    const visibleWarehouseIds = new Set<string>(
      warehouseFilterActive
        ? selectedWarehouseIds
        : [...filteredPwRoutes.map((row) => row.warehouseId), ...filteredWcRoutes.map((row) => row.warehouseId)],
    );
    const visiblePlantIds = new Set(filteredPwRoutes.map((row) => row.plantId));
    const visibleCustomerIds = new Set(filteredWcRoutes.map((row) => row.customerId));

    const plantNodes = plants
      .filter((row) => visiblePlantIds.has(row.plantId))
      .map((row) => ({
        data: { id: `plant:${row.plantId}`, label: row.plantId, type: "plant", ...row },
      }));

    const warehouseNodes = warehouses
      .filter((row) => visibleWarehouseIds.has(row.warehouseId))
      .map((row) => ({
        data: {
          id: `warehouse:${row.warehouseId}`,
          label: row.warehouseId,
          type: "warehouse",
          ...row,
          ...(warehouseSummaryById.get(row.warehouseId) ?? {}),
        },
      }));

    const customerNodes = customers
      .filter((row) => visibleCustomerIds.has(row.customerId))
      .map((row) => ({
        data: { id: `customer:${row.customerId}`, label: row.customerId, type: "customer", ...row },
      }));

    const pwEdges = filteredPwRoutes.map((row) => ({
      data: {
        id: `pw:${row.plantId}:${row.warehouseId}`,
        source: `plant:${row.plantId}`,
        target: `warehouse:${row.warehouseId}`,
        label: String(row.doQty),
        type: "pw",
        ...row,
      },
    }));

    const wcEdges = filteredWcRoutes.map((row) => ({
      data: {
        id: `wc:${row.warehouseId}:${row.customerId}`,
        source: `warehouse:${row.warehouseId}`,
        target: `customer:${row.customerId}`,
        label: String(row.doQty),
        type: "wc",
        ...row,
      },
    }));

    return [...plantNodes, ...warehouseNodes, ...customerNodes, ...pwEdges, ...wcEdges];
  }, [
    customersQuery.data?.rows,
    plantsQuery.data?.rows,
    pwRoutesQuery.data?.rows,
    selectedWarehouseIds,
    warehouseSummaryQuery.data?.rows,
    warehousesQuery.data?.rows,
    wcRoutesQuery.data?.rows,
  ]);

  useEffect(() => {
    if (!containerRef.current || elements.length === 0) {
      setIsRendering(false);
      return;
    }
    setIsRendering(true);
    setPopup(null);
    cyRef.current?.destroy();
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-size": 10,
            color: "#1f1a15",
            "text-valign": "center",
            "text-halign": "center",
          },
        },
        {
          selector: 'node[type = "plant"]',
          style: { shape: "round-rectangle", width: 56, height: 30, "background-color": "#173b44", color: "#ffffff" },
        },
        {
          selector: 'node[type = "warehouse"]',
          style: { shape: "ellipse", width: 38, height: 38, "background-color": "#f0a93e" },
        },
        {
          selector: 'node[type = "customer"]',
          style: { shape: "ellipse", width: 18, height: 18, "background-color": "#8f98a7", "font-size": 8 },
        },
        {
          selector: 'edge[type = "pw"]',
          style: {
            width: 2,
            "line-color": "#1b697a",
            "target-arrow-color": "#1b697a",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: 'edge[type = "wc"]',
          style: {
            width: 1.4,
            "line-color": "#b45b42",
            "target-arrow-color": "#b45b42",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: ":selected",
          style: {
            "border-width": 3,
            "border-color": "#1a6a7a",
          },
        },
      ],
    });
    const cyLayout = cy.layout({
      name: layout === "circle" ? "circle" : layout === "breadthfirst" ? "breadthfirst" : "cose",
      directed: true,
      padding: 24,
      animate: false,
      fit: true,
    });
    cyLayout.on("layoutstop", () => {
      setIsRendering(false);
    });
    cyLayout.run();

    cy.on("tap", "node, edge", (event) => {
      const position = event.renderedPosition ?? { x: 0, y: 0 };
      setPopup({
        x: position.x + 16,
        y: position.y + 16,
        data: event.target.data(),
      });
    });
    cy.on("tap", (event) => {
      if (event.target === cy) {
        setPopup(null);
      }
    });
    cyRef.current = cy;
    return () => {
      cy.destroy();
    };
  }, [elements, layout]);

  useEffect(() => {
    setPopup(null);
  }, [caseName, layout, selectedWarehouseIds]);

  const loading =
    summaryQuery.isLoading ||
    plantsQuery.isLoading ||
    warehousesQuery.isLoading ||
    customersQuery.isLoading ||
    pwRoutesQuery.isLoading ||
    wcRoutesQuery.isLoading ||
    warehouseSummaryQuery.isLoading;
  const error =
    summaryQuery.error ||
    plantsQuery.error ||
    warehousesQuery.error ||
    customersQuery.error ||
    pwRoutesQuery.error ||
    wcRoutesQuery.error ||
    warehouseSummaryQuery.error;

  function updateSearchParams(nextWarehouseIds: string[], nextLayout = layout, nextCaseName = caseName, nextWarehouseQuery = warehouseQuery) {
    const next = new URLSearchParams(searchParams);
    if (nextCaseName) next.set("case", nextCaseName);
    if (nextLayout) next.set("layout", nextLayout);
    if (nextWarehouseIds.length) next.set("warehouse", nextWarehouseIds.join(","));
    else next.delete("warehouse");
    if (nextWarehouseQuery) next.set("warehouseQuery", nextWarehouseQuery);
    else next.delete("warehouseQuery");
    setSearchParams(next);
  }

  function toggleWarehouse(warehouseId: string) {
    const nextSelected = selectedWarehouseIds.includes(warehouseId)
      ? selectedWarehouseIds.filter((value) => value !== warehouseId)
      : [...selectedWarehouseIds, warehouseId];
    updateSearchParams(nextSelected, layout, caseName, warehouseQuery);
  }

  return (
    <div className="page-section">
      <PageHeader title="Network Graph" subtitle="Cytoscape 기반 node-link 그래프로 Plant → Warehouse → Customer 구조를 분석합니다." />
      <Card>
        <div className="map-toolbar">
          <label className="inline-field">
            <span>Case</span>
            <select
              value={caseName}
              onChange={(event) => {
                updateSearchParams(selectedWarehouseIds, layout, event.target.value, warehouseQuery);
              }}
            >
              {(summaryQuery.data?.rows ?? []).map((row) => (
                <option key={row.caseName} value={row.caseName}>
                  {row.caseName}
                </option>
              ))}
            </select>
          </label>
          <label className="inline-field">
            <span>Layout</span>
            <select
              value={layout}
              onChange={(event) => {
                updateSearchParams(selectedWarehouseIds, event.target.value, caseName, warehouseQuery);
              }}
            >
              <option value="cose">Force</option>
              <option value="breadthfirst">Layered</option>
              <option value="circle">Circle</option>
            </select>
          </label>
          <label className="inline-field graph-filter-field">
            <span>Warehouse Search</span>
            <input
              type="text"
              value={warehouseQuery}
              placeholder="WH ID or location"
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                const value = event.target.value;
                setWarehouseQuery(value);
                updateSearchParams(selectedWarehouseIds, layout, caseName, value);
              }}
            />
          </label>
        </div>
        <div className="graph-checkbox-toolbar">
          <div className="graph-filter-actions">
            <span>Warehouse Filter</span>
            <button className="ghost-button" type="button" onClick={() => updateSearchParams([], layout, caseName, warehouseQuery)}>
              Clear
            </button>
            <button
              className="ghost-button"
              type="button"
              onClick={() => updateSearchParams(warehouseOptions.map((row) => row.warehouseId), layout, caseName, warehouseQuery)}
            >
              Select Visible
            </button>
          </div>
          <div className="graph-checkbox-list">
            {warehouseOptions.map((row) => (
              <label key={row.warehouseId} className="graph-checkbox-item">
                <input
                  type="checkbox"
                  checked={selectedWarehouseIds.includes(row.warehouseId)}
                  onChange={() => toggleWarehouse(row.warehouseId)}
                />
                <span>{row.warehouseId}</span>
                <small>{row.locationName}</small>
              </label>
            ))}
          </div>
        </div>
      </Card>
      <Card className="graph-card graph-card-wide">
        {error ? <div className="error-box">{String(error)}</div> : null}
        {!error ? (
          <div className="graph-stage">
            <div ref={containerRef} className="graph-canvas" />
            {loading || isRendering ? (
              <div className="graph-loading-overlay">
                <div className="graph-loading-bar" />
                <div className="graph-loading-text">{loading ? "Loading graph data..." : "Rendering graph..."}</div>
              </div>
            ) : null}
            {popup ? <GraphPopup popup={popup} /> : null}
          </div>
        ) : null}
      </Card>
    </div>
  );
}
