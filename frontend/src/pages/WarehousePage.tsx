import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";
import { getSummary, getWarehouseSummary } from "../api";
import { Card, DataTable, KpiCard, PageHeader } from "../components";

export function WarehousePage() {
  const { runId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const summaryQuery = useQuery({
    queryKey: ["run", runId, "summary"],
    queryFn: () => getSummary(runId),
  });
  const caseName = searchParams.get("case") ?? summaryQuery.data?.rows[0]?.caseName ?? "";
  const warehousesQuery = useQuery({
    queryKey: ["run", runId, "case", caseName, "warehouse-summary"],
    queryFn: () => getWarehouseSummary(runId, caseName),
    enabled: Boolean(runId && caseName),
  });
  const rows = warehousesQuery.data?.rows ?? [];
  const selectedWarehouseId = searchParams.get("warehouse") ?? rows[0]?.warehouseId ?? null;
  const selected = rows.find((row) => row.warehouseId === selectedWarehouseId) ?? null;

  const totals = useMemo(() => {
    const warehouseCount = rows.length;
    const avgUtilization =
      warehouseCount > 0
        ? rows.reduce((sum, row) => sum + row.capacityUtilizationPct, 0) / warehouseCount
        : 0;
    const totalFixedCost = rows.reduce((sum, row) => sum + row.fixedCost, 0);
    const totalCustomers = rows.reduce((sum, row) => sum + row.assignedCustomerCount, 0);
    return { warehouseCount, avgUtilization, totalFixedCost, totalCustomers };
  }, [rows]);

  return (
    <div className="page-section">
      <PageHeader title="Warehouse Analysis" subtitle="warehouse별 처리량, capacity 활용도, 비용 부담을 분석합니다." />
      <Card>
        <div className="map-toolbar">
          <label className="inline-field">
            <span>Case</span>
            <select
              value={caseName}
              onChange={(event) => {
                const next = new URLSearchParams(searchParams);
                next.set("case", event.target.value);
                next.delete("warehouse");
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
          <label className="inline-field">
            <span>Warehouse</span>
            <select
              value={selectedWarehouseId ?? ""}
              onChange={(event) => {
                const next = new URLSearchParams(searchParams);
                next.set("case", caseName);
                next.set("warehouse", event.target.value);
                setSearchParams(next);
              }}
            >
              {rows.map((row) => (
                <option key={row.warehouseId} value={row.warehouseId}>
                  {row.warehouseId}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>
      <div className="kpi-grid">
        <KpiCard label="Warehouses" value={totals.warehouseCount} />
        <KpiCard label="Avg Utilization %" value={totals.avgUtilization.toFixed(1)} />
        <KpiCard label="Total Fixed Cost" value={totals.totalFixedCost.toFixed(0)} />
      </div>
      <div className="split-layout">
        <Card>
          {warehousesQuery.isLoading ? <div>Loading warehouse summary...</div> : null}
          {warehousesQuery.error ? <div className="error-box">{String(warehousesQuery.error)}</div> : null}
          {!warehousesQuery.isLoading && !warehousesQuery.error ? (
            <DataTable rows={rows as unknown as Record<string, unknown>[]} />
          ) : null}
        </Card>
        <Card>
          <div className="section-title">Selected Warehouse</div>
          {selected ? (
            <DataTable rows={[selected as unknown as Record<string, unknown>]} />
          ) : (
            <div className="empty-state">Select a warehouse.</div>
          )}
          <div className="subsection">
            <div className="subsection-title">Quick Interpretation</div>
            <p>
              {selected
                ? `${selected.warehouseId} handles ${selected.assignedCustomerCount} customers with ${selected.capacityUtilizationPct.toFixed(
                    1,
                  )}% capacity utilization.`
                : "No warehouse selected."}
            </p>
            <p>Total assigned customers across warehouses: {totals.totalCustomers}</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
