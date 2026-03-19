from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .service import RunService
from .storage import RunStorage


APP_ROOT = Path(__file__).resolve().parents[3]
RUNS_ROOT = APP_ROOT / "web_runs"
storage = RunStorage(RUNS_ROOT)
service = RunService(storage)

app = FastAPI(title="Network 3-Tier Optimizer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_case(run_id: str, case_name: str) -> dict:
    path = storage.case_path(run_id, case_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Case '{case_name}' not found for run '{run_id}'.")
    return storage.load_json(path)


def _load_json_or_404(path: Path, message: str):
    if not path.exists():
        raise HTTPException(status_code=404, detail=message)
    return storage.load_json(path)


@app.get("/runs")
def list_runs():
    return {"runs": service.list_runs()}


@app.post("/runs/upload", status_code=201)
async def upload_run(
    file: UploadFile = File(...),
    solver: str = Form("SCIP"),
    maxSamples: int = Form(10),
    randomSeed: int = Form(42),
):
    suffix = Path(file.filename or "input.xls").suffix or ".xls"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp_path = Path(temp.name)
        shutil.copyfileobj(file.file, temp)
    try:
        meta = service.create_run(temp_path, file.filename or temp_path.name, solver, maxSamples, randomSeed)
        return {"run": meta}
    finally:
        temp_path.unlink(missing_ok=True)


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    try:
        return service.get_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.") from None


@app.post("/runs/{run_id}/validate")
def validate_run(run_id: str):
    try:
        return service.validate_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.") from None


@app.post("/runs/{run_id}/execute", status_code=202)
def execute_run(run_id: str, background_tasks: BackgroundTasks):
    try:
        run = service.get_run(run_id)["run"]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.") from None
    background_tasks.add_task(service.execute_run, run_id)
    return {"runId": run_id, "status": "running", "startedAt": run["updatedAt"]}


@app.get("/runs/{run_id}/input/simulation")
def get_simulation_input(run_id: str):
    payload = _load_json_or_404(storage.input_path(run_id), f"Input payload not found for run '{run_id}'.")
    return {"rows": payload["simulation"]}


@app.get("/runs/{run_id}/input/plants")
def get_plant_input(run_id: str):
    payload = _load_json_or_404(storage.input_path(run_id), f"Input payload not found for run '{run_id}'.")
    return {"rows": payload["plants"]}


@app.get("/runs/{run_id}/input/warehouses")
def get_warehouse_input(run_id: str):
    payload = _load_json_or_404(storage.input_path(run_id), f"Input payload not found for run '{run_id}'.")
    return {"rows": payload["warehouses"]}


@app.get("/runs/{run_id}/input/customers")
def get_customer_input(run_id: str):
    payload = _load_json_or_404(storage.input_path(run_id), f"Input payload not found for run '{run_id}'.")
    return {"rows": payload["customers"]}


@app.get("/runs/{run_id}/input/plant-warehouse-arcs")
def get_pw_input(run_id: str):
    payload = _load_json_or_404(storage.input_path(run_id), f"Input payload not found for run '{run_id}'.")
    return {"rows": payload["plantWarehouseArcs"]}


@app.get("/runs/{run_id}/input/warehouse-customer-arcs")
def get_wc_input(run_id: str):
    payload = _load_json_or_404(storage.input_path(run_id), f"Input payload not found for run '{run_id}'.")
    return {"rows": payload["warehouseCustomerArcs"]}


@app.get("/runs/{run_id}/validation-issues")
def get_validation_issues(run_id: str):
    return service.get_validation(run_id)


@app.get("/runs/{run_id}/summary")
def get_summary(run_id: str):
    return _load_json_or_404(storage.summary_path(run_id), f"Summary not found for run '{run_id}'.")


@app.get("/runs/{run_id}/cases")
def get_cases(run_id: str):
    return _load_json_or_404(storage.cases_path(run_id), f"Cases not found for run '{run_id}'.")


@app.get("/runs/{run_id}/cases/{case_name}/warehouse-summary")
def get_warehouse_summary(run_id: str, case_name: str):
    return {"rows": _load_case(run_id, case_name)["warehouseSummary"]}


@app.get("/runs/{run_id}/cases/{case_name}/plant-warehouse-routes")
def get_pw_routes(run_id: str, case_name: str):
    return {"rows": _load_case(run_id, case_name)["plantWarehouseRoutes"]}


@app.get("/runs/{run_id}/cases/{case_name}/warehouse-customer-routes")
def get_wc_routes(run_id: str, case_name: str):
    return {"rows": _load_case(run_id, case_name)["warehouseCustomerRoutes"]}


@app.get("/runs/{run_id}/cases/{case_name}/coverage-details")
def get_coverage(run_id: str, case_name: str):
    return {"rows": _load_case(run_id, case_name)["coverageDetails"]}


@app.get("/runs/{run_id}/events")
def get_events(run_id: str):
    return {"events": storage.load_events(run_id)}
