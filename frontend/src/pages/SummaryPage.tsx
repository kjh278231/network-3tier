import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { getRun, getSummary } from "../api";
import { Card, DataTable, KpiCard, PageHeader } from "../components";

export function SummaryPage() {
  const { runId = "" } = useParams();
  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.run.status;
      return status === "running" || status === "validating" || status === "uploaded" ? 3000 : false;
    },
  });
  const { data, isLoading, error } = useQuery({
    queryKey: ["run", runId, "summary"],
    queryFn: () => getSummary(runId),
    enabled: runQuery.data?.run.status === "completed",
    refetchInterval: runQuery.data?.run.status === "running" ? 3000 : false,
  });
  const rows = data?.rows ?? [];
  const best = rows[0];
  const runStatus = runQuery.data?.run.status;

  return (
    <div className="page-section">
      <PageHeader title="Summary Dashboard" subtitle="case별 총비용, lead time, coverage, selected warehouses를 요약합니다." />
      <div className="kpi-grid">
        <KpiCard label="Cases" value={rows.length} />
        <KpiCard label="Best Cost" value={best?.optimalCost ?? "-"} />
        <KpiCard label="Best Coverage Time" value={best?.coverageTimePct ?? "-"} />
      </div>
      <Card>
        {runStatus && runStatus !== "completed" ? (
          <div className="empty-state">
            {runStatus === "uploaded" ? "Upload completed. Run validation and then execute the model." : null}
            {runStatus === "ready" ? "Validation passed. Execute the model to generate case summary." : null}
            {runStatus === "validating" ? "Validation is running." : null}
            {runStatus === "running" ? "Optimization is running. Summary will appear when execution completes." : null}
            {runStatus === "validation_failed" || runStatus === "failed" ? runQuery.data?.run.errorSummary : null}
          </div>
        ) : null}
        {isLoading ? <div>Loading summary...</div> : null}
        {error ? <div className="error-box">{String(error)}</div> : null}
        {!isLoading && !error && runStatus === "completed" ? <DataTable rows={rows as unknown as Record<string, unknown>[]} /> : null}
      </Card>
    </div>
  );
}
