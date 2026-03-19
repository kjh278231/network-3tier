const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type Run = {
  runId: string;
  status: string;
  inputFileName: string;
  createdAt: string;
  updatedAt: string;
  solver: string;
  maxSamples: number;
  randomSeed: number;
  caseCount: number;
  bestCaseName: string | null;
  bestTotalCost: number | null;
  bestTotalInboundQty: number | null;
  requiredWarehouseQty: number | null;
  errorSummary: string | null;
};

export type CaseSummary = {
  caseName: string;
  caseType: string;
  totalRank: number;
  costRank: number;
  optimalCost: number;
  optimalTotalInboundQty: number;
  optimalTotalOutboundQty: number;
  inboundCost: number;
  warehouseCost: number;
  outboundCost: number;
  leadTimeRank: number;
  optimalLeadTimeSec: number;
  coverageTimePct: number;
  coverageVolPct: number;
  totalScore: number;
  selectedWarehouses: string[];
};

export type PlantInputRow = {
  plantId: string;
  locationName: string;
  latitude: number;
  longitude: number;
  productQty: number;
  shipmentQty: number;
};

export type WarehouseInputRow = {
  warehouseId: string;
  locationName: string;
  latitude: number;
  longitude: number;
  capacityQty: number;
  fixedCost: number;
  operationCost: number;
  activeYn: string;
  includedInModel: boolean;
};

export type CustomerInputRow = {
  customerId: string;
  locationName: string;
  latitude: number;
  longitude: number;
  doQty: number;
  shipmentQty: number;
  mappingId?: string | null;
};

export type PlantWarehouseRouteRow = {
  plantId: string;
  plantLocationName: string;
  warehouseId: string;
  warehouseLocationName: string;
  doQty: number;
  cost: number;
  shipmentQtyRatio: number;
  leadTimeSec: number;
  distanceKm: number;
  carbonEmissionTco2eq: number;
};

export type WarehouseCustomerRouteRow = {
  warehouseId: string;
  warehouseLocationName: string;
  customerId: string;
  customerLocationName: string;
  doQty: number;
  cost: number;
  shipmentQty: number;
  leadTimeSec: number;
  distanceKm: number;
  oneWayTimeSec: number;
  coverageYn: "Y" | "N";
  operationCost: number;
  carbonEmissionTco2eq: number;
  mappingId?: string | null;
};

export type WarehouseSummaryRow = {
  warehouseId: string;
  warehouseLocationName: string;
  inboundQty: number;
  outboundQty: number;
  throughputCapacityQty: number;
  capacityUtilizationPct: number;
  fixedCost: number;
  operationCost: number;
  assignedCustomerCount: number;
  coveredCustomerPct: number;
  coveredDoQtyPct: number;
};

export type ValidationIssue = {
  issueId: string;
  severity: string;
  ruleName: string;
  message: string;
  recommendation: string | null;
  affectedCount: number;
  blocking: boolean;
};

export type RunEvent = {
  timestamp: string;
  level: string;
  message: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getRuns() {
  return request<{ runs: Run[] }>("/runs");
}

export function getRun(runId: string) {
  return request<{ run: Run; simulation: Record<string, unknown> | null }>(`/runs/${runId}`);
}

export function uploadRun(file: File, solver: string, maxSamples: number, randomSeed: number) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("solver", solver);
  formData.append("maxSamples", String(maxSamples));
  formData.append("randomSeed", String(randomSeed));
  return request<{ run: Run }>("/runs/upload", {
    method: "POST",
    body: formData,
  });
}

export function validateRun(runId: string) {
  return request<{
    runId: string;
    status: string;
    summary: { errorCount: number; warningCount: number; infoCount: number; blocking: boolean };
    issues: ValidationIssue[];
  }>(`/runs/${runId}/validate`, { method: "POST" });
}

export function executeRun(runId: string) {
  return request<{ runId: string; status: string; startedAt: string }>(`/runs/${runId}/execute`, {
    method: "POST",
  });
}

export function getInputSheet(runId: string, sheet: string) {
  return request<{ rows: Record<string, unknown>[] }>(`/runs/${runId}/input/${sheet}`);
}

export function getValidationIssues(runId: string) {
  return request<{
    summary: { errorCount: number; warningCount: number; infoCount: number; blocking: boolean };
    issues: ValidationIssue[];
  }>(`/runs/${runId}/validation-issues`);
}

export function getSummary(runId: string) {
  return request<{ rows: CaseSummary[] }>(`/runs/${runId}/summary`);
}

export function getPlantInput(runId: string) {
  return request<{ rows: PlantInputRow[] }>(`/runs/${runId}/input/plants`);
}

export function getWarehouseInput(runId: string) {
  return request<{ rows: WarehouseInputRow[] }>(`/runs/${runId}/input/warehouses`);
}

export function getCustomerInput(runId: string) {
  return request<{ rows: CustomerInputRow[] }>(`/runs/${runId}/input/customers`);
}

export function getPlantWarehouseRoutes(runId: string, caseName: string) {
  return request<{ rows: PlantWarehouseRouteRow[] }>(
    `/runs/${runId}/cases/${encodeURIComponent(caseName)}/plant-warehouse-routes`,
  );
}

export function getWarehouseCustomerRoutes(runId: string, caseName: string) {
  return request<{ rows: WarehouseCustomerRouteRow[] }>(
    `/runs/${runId}/cases/${encodeURIComponent(caseName)}/warehouse-customer-routes`,
  );
}

export function getWarehouseSummary(runId: string, caseName: string) {
  return request<{ rows: WarehouseSummaryRow[] }>(
    `/runs/${runId}/cases/${encodeURIComponent(caseName)}/warehouse-summary`,
  );
}

export function getRunEvents(runId: string) {
  return request<{ events: RunEvent[] }>(`/runs/${runId}/events`);
}
