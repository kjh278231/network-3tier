import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useParams } from "react-router-dom";
import { executeRun, getRun, getRunEvents, validateRun } from "../api";
import { Card, DataTable, PageHeader, StatusBadge } from "../components";

export function RunLayout() {
  const { runId = "" } = useParams();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.run.status;
      return status === "running" || status === "validating" || status === "uploaded" ? 3000 : false;
    },
  });
  const eventsQuery = useQuery({
    queryKey: ["run", runId, "events"],
    queryFn: () => getRunEvents(runId),
    enabled: Boolean(runId),
    refetchInterval: 3000,
  });
  const validateMutation = useMutation({
    mutationFn: () => validateRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["run", runId] });
      queryClient.invalidateQueries({ queryKey: ["run", runId, "validation"] });
      queryClient.invalidateQueries({ queryKey: ["run", runId, "events"] });
      queryClient.invalidateQueries({ queryKey: ["run", runId, "summary"] });
    },
  });
  const executeMutation = useMutation({
    mutationFn: () => executeRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["run", runId] });
      queryClient.invalidateQueries({ queryKey: ["run", runId, "events"] });
      queryClient.invalidateQueries({ queryKey: ["run", runId, "summary"] });
    },
  });
  const run = data?.run;
  const status = run?.status ?? "unknown";
  const canValidate = Boolean(runId) && !validateMutation.isPending && status !== "validating" && status !== "running";
  const canExecute = Boolean(runId) && (status === "ready" || status === "completed") && !executeMutation.isPending;
  const latestEvents = (eventsQuery.data?.events ?? []).slice(-5).reverse();

  return (
    <div className="page">
      <PageHeader title={runId} subtitle="Run context and analysis pages" />
      <Card className="run-meta-banner">
        {isLoading ? <div>Loading run...</div> : null}
        {error ? <div className="error-box">{String(error)}</div> : null}
        {data ? (
          <div className="meta-grid">
            <div>
              <strong>Input File</strong>
              <div>{data.run.inputFileName}</div>
            </div>
            <div>
              <strong>Status</strong>
              <div>
                <StatusBadge status={data.run.status} />
              </div>
            </div>
            <div>
              <strong>Best Case</strong>
              <div>{data.run.bestCaseName ?? "-"}</div>
            </div>
            <div className="meta-actions">
              <button className="primary-button" onClick={() => validateMutation.mutate()} disabled={!canValidate}>
                {validateMutation.isPending ? "Validating..." : "Run Validation"}
              </button>
              <button className="primary-button" onClick={() => executeMutation.mutate()} disabled={!canExecute}>
                {executeMutation.isPending || status === "running" ? "Executing..." : "Execute Model"}
              </button>
              <Link to={`/runs/${runId}/input`}>Input</Link>
              <Link to={`/runs/${runId}/validation`}>Validation</Link>
              <Link to={`/runs/${runId}`}>Summary</Link>
            </div>
          </div>
        ) : null}
        {run ? (
          <div className="run-status-note">
            {status === "uploaded" ? "Upload completed. Run validation first." : null}
            {status === "ready" ? "Validation passed. You can now execute the optimization model." : null}
            {status === "running" ? "Optimization is running in the background. This can take several minutes." : null}
            {status === "validation_failed" || status === "failed" ? run?.errorSummary : null}
          </div>
        ) : null}
        {eventsQuery.data ? (
          <div className="event-log">
            <div className="event-log-title">Recent Events</div>
            <DataTable rows={latestEvents as unknown as Record<string, unknown>[]} />
          </div>
        ) : null}
      </Card>
      <Outlet />
    </div>
  );
}
