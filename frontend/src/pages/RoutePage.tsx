import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";
import { getPlantWarehouseRoutes, getSummary, getWarehouseCustomerRoutes } from "../api";
import { Card, DataTable, KpiCard, PageHeader } from "../components";

export function RoutePage() {
  const { runId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const summaryQuery = useQuery({
    queryKey: ["run", runId, "summary"],
    queryFn: () => getSummary(runId),
  });
  const caseName = searchParams.get("case") ?? summaryQuery.data?.rows[0]?.caseName ?? "";
  const tab = searchParams.get("tab") ?? "wc";
  const pwQuery = useQuery({
    queryKey: ["run", runId, "case", caseName, "pw-routes"],
    queryFn: () => getPlantWarehouseRoutes(runId, caseName),
    enabled: Boolean(runId && caseName),
  });
  const wcQuery = useQuery({
    queryKey: ["run", runId, "case", caseName, "wc-routes"],
    queryFn: () => getWarehouseCustomerRoutes(runId, caseName),
    enabled: Boolean(runId && caseName),
  });

  const pwRows = pwQuery.data?.rows ?? [];
  const wcRows = wcQuery.data?.rows ?? [];
  const visibleRows = tab === "pw" ? pwRows : wcRows;
  const stats = useMemo(() => {
    if (tab === "pw") {
      return {
        count: pwRows.length,
        totalCost: pwRows.reduce((sum, row) => sum + row.cost, 0),
        maxLeadTime: pwRows.reduce((max, row) => Math.max(max, row.leadTimeSec), 0),
      };
    }
    return {
      count: wcRows.length,
      totalCost: wcRows.reduce((sum, row) => sum + row.cost, 0),
      maxLeadTime: wcRows.reduce((max, row) => Math.max(max, row.leadTimeSec), 0),
    };
  }, [pwRows, tab, wcRows]);

  const loading = pwQuery.isLoading || wcQuery.isLoading;
  const error = pwQuery.error || wcQuery.error;

  return (
    <div className="page-section">
      <PageHeader title="Route Analysis" subtitle="Plant→Warehouse와 Warehouse→Customer route를 비용과 lead time 기준으로 분석합니다." />
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
          <div className="tab-row">
            <button
              className={tab === "pw" ? "tab-button active" : "tab-button"}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.set("case", caseName);
                next.set("tab", "pw");
                setSearchParams(next);
              }}
            >
              Plant → Warehouse
            </button>
            <button
              className={tab === "wc" ? "tab-button active" : "tab-button"}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.set("case", caseName);
                next.set("tab", "wc");
                setSearchParams(next);
              }}
            >
              Warehouse → Customer
            </button>
          </div>
        </div>
      </Card>
      <div className="kpi-grid">
        <KpiCard label="Routes" value={stats.count} />
        <KpiCard label="Total Cost" value={stats.totalCost.toFixed(0)} />
        <KpiCard label="Max Lead Time Sec" value={stats.maxLeadTime.toFixed(0)} />
      </div>
      <Card>
        {loading ? <div>Loading routes...</div> : null}
        {error ? <div className="error-box">{String(error)}</div> : null}
        {!loading && !error ? <DataTable rows={visibleRows as unknown as Record<string, unknown>[]} /> : null}
      </Card>
    </div>
  );
}
