import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { getValidationIssues, validateRun } from "../api";
import { Card, DataTable, KpiCard, PageHeader } from "../components";

export function ValidationPage() {
  const { runId = "" } = useParams();
  const queryClient = useQueryClient();
  const validationQuery = useQuery({
    queryKey: ["run", runId, "validation"],
    queryFn: () => getValidationIssues(runId),
  });
  const validateMutation = useMutation({
    mutationFn: () => validateRun(runId),
    onSuccess: () => {
      validationQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["run", runId] });
      queryClient.invalidateQueries({ queryKey: ["run", runId, "events"] });
    },
  });
  const summary = validationQuery.data?.summary;
  const issues = validationQuery.data?.issues ?? [];

  return (
    <div className="page-section">
      <PageHeader title="Validation" subtitle="실행 전 입력 데이터 품질과 feasibility gate를 확인합니다." />
      <div className="toolbar">
        <button className="primary-button" onClick={() => validateMutation.mutate()} disabled={validateMutation.isPending}>
          {validateMutation.isPending ? "Validating..." : "Run Validation"}
        </button>
      </div>
      <div className="kpi-grid">
        <KpiCard label="Errors" value={summary?.errorCount ?? 0} />
        <KpiCard label="Warnings" value={summary?.warningCount ?? 0} />
        <KpiCard label="Blocking" value={summary?.blocking ? "Yes" : "No"} />
      </div>
      <Card>
        {validationQuery.isLoading ? <div>Loading validation...</div> : null}
        {validationQuery.error ? <div className="error-box">{String(validationQuery.error)}</div> : null}
        {!validationQuery.isLoading && !validationQuery.error ? <DataTable rows={issues} /> : null}
      </Card>
    </div>
  );
}
