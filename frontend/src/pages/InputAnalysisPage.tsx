import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getInputSheet } from "../api";
import { Card, DataTable, KpiCard, PageHeader } from "../components";

const sheets = [
  ["simulation", "Simulation"],
  ["plants", "Plants"],
  ["warehouses", "Warehouses"],
  ["customers", "Customers"],
  ["plant-warehouse-arcs", "P->W Arcs"],
  ["warehouse-customer-arcs", "W->C Arcs"],
] as const;

export function InputAnalysisPage() {
  const { runId = "" } = useParams();
  const [sheet, setSheet] = useState<(typeof sheets)[number][0]>("simulation");
  const { data, isLoading, error } = useQuery({
    queryKey: ["run", runId, "input", sheet],
    queryFn: () => getInputSheet(runId, sheet),
  });
  const rows = data?.rows ?? [];
  const summary = useMemo(() => {
    return {
      rows: rows.length,
      columns: rows[0] ? Object.keys(rows[0]).length : 0,
    };
  }, [rows]);

  return (
    <div className="page-section">
      <PageHeader title="Input Analysis" subtitle="입력 workbook의 시트별 데이터와 모델 반영 대상 컬럼을 확인합니다." />
      <Card>
        <div className="tab-row">
          {sheets.map(([value, label]) => (
            <button
              key={value}
              className={value === sheet ? "tab-button active" : "tab-button"}
              onClick={() => setSheet(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </Card>
      <div className="kpi-grid">
        <KpiCard label="Rows" value={summary.rows} />
        <KpiCard label="Columns" value={summary.columns} />
        <KpiCard label="Current Sheet" value={sheet} />
      </div>
      <Card>
        {isLoading ? <div>Loading sheet...</div> : null}
        {error ? <div className="error-box">{String(error)}</div> : null}
        {!isLoading && !error ? <DataTable rows={rows} /> : null}
      </Card>
    </div>
  );
}
