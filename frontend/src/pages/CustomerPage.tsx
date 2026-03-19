import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";
import { getSummary, getWarehouseCustomerRoutes } from "../api";
import { Card, DataTable, KpiCard, PageHeader } from "../components";

export function CustomerPage() {
  const { runId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const summaryQuery = useQuery({
    queryKey: ["run", runId, "summary"],
    queryFn: () => getSummary(runId),
  });
  const caseName = searchParams.get("case") ?? summaryQuery.data?.rows[0]?.caseName ?? "";
  const coverageOnly = searchParams.get("coverageOnly") === "true";
  const routesQuery = useQuery({
    queryKey: ["run", runId, "case", caseName, "wc-routes"],
    queryFn: () => getWarehouseCustomerRoutes(runId, caseName),
    enabled: Boolean(runId && caseName),
  });
  const allRows = routesQuery.data?.rows ?? [];
  const rows = useMemo(
    () => (coverageOnly ? allRows.filter((row) => row.coverageYn === "N") : allRows),
    [allRows, coverageOnly],
  );
  const selectedCustomerId = searchParams.get("customer") ?? rows[0]?.customerId ?? null;
  const selected = rows.find((row) => row.customerId === selectedCustomerId) ?? null;

  const stats = useMemo(() => {
    const lowCoverageCount = allRows.filter((row) => row.coverageYn === "N").length;
    const mappedCount = allRows.filter((row) => row.mappingId).length;
    const worstLeadTime = allRows.reduce((max, row) => Math.max(max, row.leadTimeSec), 0);
    return { lowCoverageCount, mappedCount, worstLeadTime };
  }, [allRows]);

  return (
    <div className="page-section">
      <PageHeader title="Customer Analysis" subtitle="고객 배정, lead time, coverage 문제를 customer 단위로 추적합니다." />
      <Card>
        <div className="map-toolbar">
          <label className="inline-field">
            <span>Case</span>
            <select
              value={caseName}
              onChange={(event) => {
                const next = new URLSearchParams(searchParams);
                next.set("case", event.target.value);
                next.delete("customer");
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
            <input
              type="checkbox"
              checked={coverageOnly}
              onChange={() => {
                const next = new URLSearchParams(searchParams);
                next.set("case", caseName);
                if (coverageOnly) next.delete("coverageOnly");
                else next.set("coverageOnly", "true");
                setSearchParams(next);
              }}
            />
            Low Coverage Only
          </label>
        </div>
      </Card>
      <div className="kpi-grid">
        <KpiCard label="Visible Customers" value={rows.length} />
        <KpiCard label="Low Coverage" value={stats.lowCoverageCount} />
        <KpiCard label="Worst Lead Time Sec" value={stats.worstLeadTime.toFixed(0)} />
      </div>
      <div className="split-layout">
        <Card>
          {routesQuery.isLoading ? <div>Loading customer routes...</div> : null}
          {routesQuery.error ? <div className="error-box">{String(routesQuery.error)}</div> : null}
          {!routesQuery.isLoading && !routesQuery.error ? (
            <DataTable rows={rows as unknown as Record<string, unknown>[]} />
          ) : null}
        </Card>
        <Card>
          <div className="section-title">Selected Customer</div>
          {selected ? (
            <DataTable rows={[selected as unknown as Record<string, unknown>]} />
          ) : (
            <div className="empty-state">Select a customer.</div>
          )}
          <div className="subsection">
            <div className="subsection-title">Quick Interpretation</div>
            <p>
              {selected
                ? `${selected.customerId} is served by ${selected.warehouseId} with coverage ${selected.coverageYn} and lead time ${selected.leadTimeSec.toFixed(
                    0,
                  )} sec.`
                : "No customer selected."}
            </p>
            <p>Mapped customers in this case: {stats.mappedCount}</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
