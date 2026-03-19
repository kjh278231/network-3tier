import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { uploadRun } from "../api";
import { Card, PageHeader } from "../components";

export function UploadRunPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [solver, setSolver] = useState("SCIP");
  const [maxSamples, setMaxSamples] = useState(10);
  const [randomSeed, setRandomSeed] = useState(42);
  const mutation = useMutation({
    mutationFn: () => {
      if (!file) {
        throw new Error("Please choose a file.");
      }
      return uploadRun(file, solver, maxSamples, randomSeed);
    },
    onSuccess: (data) => {
      navigate(`/runs/${data.run.runId}`);
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div className="page">
      <PageHeader title="Upload & Run" subtitle="입력 workbook을 업로드하고 validation 및 실행을 시작합니다." />
      <Card>
        <form className="form-grid" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Workbook</span>
            <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <label className="form-field">
            <span>Solver</span>
            <select value={solver} onChange={(event) => setSolver(event.target.value)}>
              <option value="SCIP">SCIP</option>
              <option value="CBC">CBC</option>
            </select>
          </label>
          <label className="form-field">
            <span>Max Samples</span>
            <input type="number" value={maxSamples} onChange={(event) => setMaxSamples(Number(event.target.value))} />
          </label>
          <label className="form-field">
            <span>Random Seed</span>
            <input type="number" value={randomSeed} onChange={(event) => setRandomSeed(Number(event.target.value))} />
          </label>
          <button className="primary-button" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Uploading..." : "Create Run"}
          </button>
        </form>
        {mutation.error ? <div className="error-box">{String(mutation.error)}</div> : null}
        {mutation.data ? (
          <div className="success-box">
            Run created: <Link to={`/runs/${mutation.data.run.runId}`}>{mutation.data.run.runId}</Link>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
