import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getRuns } from "../api";
import { Card, DataTable, KpiCard, PageHeader, StatusBadge } from "../components";

export function HomePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["runs"],
    queryFn: getRuns,
  });
  const runs = data?.runs ?? [];
  const latest = runs[0];

  return (
    <div className="page">
      <PageHeader
        title="Run Overview"
        subtitle="최근 실행 이력과 최신 네트워크 최적화 결과를 확인합니다."
      />
      <div className="kpi-grid">
        <KpiCard label="Runs" value={runs.length} />
        <KpiCard label="Latest Best Cost" value={latest?.bestTotalCost ?? "-"} />
        <KpiCard label="Latest Status" value={latest?.status ?? "-"} />
      </div>
      <Card>
        <div className="section-title">Recent Runs</div>
        {isLoading ? <div>Loading...</div> : null}
        {error ? <div className="error-box">{String(error)}</div> : null}
        {!isLoading && !error ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>File</th>
                  <th>Status</th>
                  <th>Best Cost</th>
                  <th>Cases</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.runId}>
                    <td>
                      <Link to={`/runs/${run.runId}`}>{run.runId}</Link>
                    </td>
                    <td>{run.inputFileName}</td>
                    <td>
                      <StatusBadge status={run.status} />
                    </td>
                    <td>{run.bestTotalCost ?? "-"}</td>
                    <td>{run.caseCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
      <Card>
        <div className="section-title">Next Step</div>
        <p>
          새 workbook으로 실행을 시작하려면 <Link to="/runs/new">Upload &amp; Run</Link>으로 이동합니다.
        </p>
      </Card>
    </div>
  );
}
