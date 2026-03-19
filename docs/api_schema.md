# Network 3-Tier Optimizer Web App 백엔드 API 응답 스키마 문서

## 1. 문서 목적

본 문서는 웹 앱 프론트엔드와 백엔드 간 JSON 계약을 정의한다.

이 문서는 다음을 목표로 한다.

- endpoint별 request/response 스키마 정의
- 타입 의미와 nullable 규칙 정의
- 프론트엔드 타입 생성 기준 제시
- 현재 Python 모델 출력 구조를 웹 친화적인 형태로 정규화

본 문서는 [frontend_architecture.md](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/frontend_architecture.md)의 API 연동 기준 문서다.

---

## 2. 기본 규칙

### 2.1 공통 포맷

- Content-Type: `application/json`
- 파일 업로드만 `multipart/form-data`

### 2.2 날짜/시간 규칙

- 모든 API 시간 값은 ISO 8601 문자열 사용
- 예: `2026-03-19T10:41:49+09:00`

### 2.3 숫자 규칙

- 비용, 비율, 시간은 JSON number 사용
- 프론트 formatting은 별도 처리

### 2.4 ID 규칙

- `runId`: string
- `caseName`: string
- `warehouseId`, `plantId`, `customerId`: string

### 2.5 null 규칙

- 데이터가 아예 없으면 `null`
- 빈 목록은 `[]`
- 숫자 계산 불가 시 `null`

### 2.6 에러 응답 규칙

모든 실패 응답은 아래 구조를 사용한다.

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Human readable summary",
    "details": {
      "runId": "run_20260319104148"
    }
  }
}
```

---

## 3. 공통 타입

## 3.1 RunStatus

```text
uploaded
validating
validation_failed
ready
running
completed
failed
```

## 3.2 CaseType

```text
best
designated
```

## 3.3 Severity

```text
error
warning
info
```

---

## 4. 핵심 도메인 스키마

## 4.1 Run

```json
{
  "runId": "run_20260319104148",
  "status": "completed",
  "inputFileName": "TRNS_DOWNLOAD_20260319.xls",
  "createdAt": "2026-03-19T10:41:48+09:00",
  "updatedAt": "2026-03-19T10:41:49+09:00",
  "solver": "SCIP",
  "maxSamples": 10,
  "randomSeed": 42,
  "caseCount": 1,
  "bestCaseName": "best_model",
  "bestTotalCost": 105015282.0,
  "bestTotalInboundQty": 63789.0,
  "requiredWarehouseQty": 10,
  "errorSummary": null
}
```

### 필드 설명

- `caseCount`: 실행된 case 수
- `bestCaseName`: 최우수 case 이름
- `errorSummary`: 실패 시 요약 메시지

## 4.2 SimulationConfig

```json
{
  "simulationName": "Makro_Hub_10",
  "structure": "TRNS3",
  "warehouseQty": 10,
  "speedKmh": 60.0,
  "coverageHours": 2.0
}
```

## 4.3 ValidationIssue

```json
{
  "issueId": "validation_001",
  "severity": "error",
  "ruleCode": "CUSTOMER_ASSIGNMENT_ARC_MISSING",
  "ruleName": "Customer without eligible warehouse assignment",
  "message": "Customers without any eligible warehouse assignment detected.",
  "recommendation": "Add at least one warehouse->customer cost row for the affected customers.",
  "affectedEntityType": "customer",
  "affectedCount": 3,
  "affectedRefs": [
    {
      "sheet": "warehouseCustomerCost",
      "rowKey": "96220_Chae"
    }
  ],
  "blocking": true
}
```

## 4.4 CaseSummary

```json
{
  "caseName": "best_model",
  "caseType": "best",
  "totalRank": 1,
  "costRank": 1,
  "optimalCost": 105015282.0,
  "optimalTotalInboundQty": 63789.0,
  "optimalTotalOutboundQty": 63345.0,
  "inboundCost": 41509889.0,
  "warehouseCost": 11080350.0,
  "outboundCost": 52425043.0,
  "leadTimeRank": 1,
  "optimalLeadTimeSec": 65964908.0958,
  "inboundLeadTimeSec": 325359.8958,
  "outboundLeadTimeSec": 65639548.2,
  "coverageRankTime": 1,
  "coverageTimePct": 40.1075,
  "coverageRankVol": 1,
  "coverageVolPct": 50.4397,
  "costScore": 1.0,
  "leadTimeScore": 1.0,
  "coverageTimeScore": 1.0,
  "coverageVolScore": 1.0,
  "coverageScore": 1.0,
  "totalScore": 1.0,
  "selectedWarehouseCount": 10,
  "selectedWarehouses": [
    "Hub_1",
    "Hub_10",
    "Hub_2"
  ],
  "carbonEmissionTco2eq": 0.0
}
```

### 정규화 규칙

기존 출력은 `Selected Warehouses`를 comma-separated string으로 저장하지만 API에서는 `string[]`로 반환한다.

## 4.5 WarehouseSummaryRow

```json
{
  "warehouseId": "Hub_1",
  "warehouseLocationName": "Hub_1",
  "inboundQty": 2574.0,
  "outboundQty": 2574.0,
  "throughputCapacityQty": 2574.0,
  "capacityUtilizationPct": 100.0,
  "fixedCost": 918000.0,
  "operationCost": 77220.0,
  "assignedCustomerCount": 66,
  "coveredCustomerPct": 21.2,
  "coveredDoQtyPct": 31.8
}
```

### 주의

- `capacityUtilizationPct`, `assignedCustomerCount`, `coveredCustomerPct`, `coveredDoQtyPct`는 API 레이어에서 후처리로 계산 가능

## 4.6 PlantWarehouseRouteRow

```json
{
  "plantId": "CDC",
  "plantLocationName": "Wang Noi CDC",
  "warehouseId": "Hub_1",
  "warehouseLocationName": "Hub_1",
  "doQty": 2574.0,
  "cost": 4509648.0,
  "shipmentQtyRatio": 0.6052,
  "leadTimeSec": 35338.1815,
  "distanceKm": 973.15,
  "carbonEmissionTco2eq": 0.0
}
```

## 4.7 WarehouseCustomerRouteRow

```json
{
  "warehouseId": "Hub_1",
  "warehouseLocationName": "Hub_1",
  "customerId": "80170_Huai",
  "customerLocationName": "Hua Sai",
  "doQty": 39.0,
  "cost": 49491.0,
  "shipmentQty": 5.0,
  "leadTimeSec": 59721.0,
  "distanceKm": 199.07,
  "oneWayTimeSec": 11944.2,
  "coverageYn": "N",
  "operationCost": 1170.0,
  "carbonEmissionTco2eq": 0.0,
  "mappingId": "Hub_1"
}
```

### 정규화 추가 필드

- `mappingId`는 현재 결과 파일에는 직접 없지만 customer 원본과 join해서 API에서 추가하는 편이 좋다

## 4.8 CoverageDetailRow

```json
{
  "warehouseId": "Hub_1",
  "customerId": "80170_Huai",
  "assignedDoQty": 39.0,
  "customerShipmentQty": 5.0,
  "plantWarehouseLeadTimeSec": 35338.1815,
  "warehouseCustomerLeadTimeSec": 59721.0,
  "totalLeadTimeSec": 95059.1815,
  "coverageHour": 2.0,
  "oneWayTimeSec": 11944.2,
  "coverageYn": "N"
}
```

---

## 5. 입력 데이터 스키마

웹 화면에서 input explorer를 위해 시트별 정규화 응답이 필요하다.

## 5.1 SimulationInputRow

```json
{
  "simulationName": "Makro_Hub_10",
  "status": "COMPLETED",
  "structure": "TRNS3",
  "warehouseQty": 10,
  "speedKmh": 60.0,
  "coverageHours": 2.0
}
```

## 5.2 PlantInputRow

```json
{
  "plantId": "CDC",
  "locationName": "Wang Noi CDC",
  "latitude": 14.183173,
  "longitude": 100.646494,
  "productQty": 63789.0,
  "shipmentQty": 4253.0
}
```

## 5.3 WarehouseInputRow

```json
{
  "warehouseId": "Hub_9",
  "locationName": "Hub_9",
  "latitude": 19.016131,
  "longitude": 99.517041,
  "capacityQty": 6708.0,
  "fixedCost": 918000.0,
  "operationCost": 30.0,
  "activeYn": "F",
  "includedInModel": true
}
```

## 5.4 CustomerInputRow

```json
{
  "customerId": "96220_Chae",
  "locationName": "Chanae",
  "latitude": 6.057088,
  "longitude": 101.695444,
  "doQty": 12.0,
  "shipmentQty": 2.0,
  "mappingId": "Hub_1"
}
```

## 5.5 PlantWarehouseArcRow

```json
{
  "plantId": "CDC",
  "warehouseId": "Hub_1",
  "distanceKm": 973.15,
  "distanceType": null,
  "trnsCost": 1752.0
}
```

## 5.6 WarehouseCustomerArcRow

```json
{
  "warehouseId": "Hub_1",
  "customerId": "10100_Poai",
  "distanceKm": 920.86,
  "distanceType": null,
  "trnsCost": 5870.0
}
```

---

## 6. Endpoint 정의

## 6.1 `POST /runs/upload`

### 목적

입력 workbook 업로드 및 run 생성

### Request

`multipart/form-data`

필드:

- `file`: workbook 파일
- `solver`: optional, default `SCIP`
- `maxSamples`: optional, default `10`
- `randomSeed`: optional, default `42`

### Response `201`

```json
{
  "run": {
    "runId": "run_20260319110000",
    "status": "uploaded",
    "inputFileName": "TRNS_DOWNLOAD_20260319.xls",
    "createdAt": "2026-03-19T11:00:00+09:00",
    "updatedAt": "2026-03-19T11:00:00+09:00",
    "solver": "SCIP",
    "maxSamples": 10,
    "randomSeed": 42,
    "caseCount": 0,
    "bestCaseName": null,
    "bestTotalCost": null,
    "bestTotalInboundQty": null,
    "requiredWarehouseQty": null,
    "errorSummary": null
  }
}
```

## 6.2 `POST /runs/{runId}/validate`

### 목적

입력 workbook validation 수행

### Response `200`

```json
{
  "runId": "run_20260319110000",
  "status": "ready",
  "summary": {
    "errorCount": 0,
    "warningCount": 1,
    "infoCount": 4,
    "blocking": false
  },
  "issues": [
    {
      "issueId": "validation_001",
      "severity": "warning",
      "ruleCode": "ACTIVE_WAREHOUSE_ALL_F_OR_Y",
      "ruleName": "Warehouse active filter applied",
      "message": "Only warehouses with Active Y/N in {Y, F} are included.",
      "recommendation": null,
      "affectedEntityType": "warehouse",
      "affectedCount": 10,
      "affectedRefs": [],
      "blocking": false
    }
  ]
}
```

## 6.3 `POST /runs/{runId}/execute`

### 목적

최적화 실행 시작

### Response `202`

```json
{
  "runId": "run_20260319110000",
  "status": "running",
  "startedAt": "2026-03-19T11:00:10+09:00"
}
```

## 6.4 `GET /runs`

### Response `200`

```json
{
  "runs": [
    {
      "runId": "run_20260319104148",
      "status": "completed",
      "inputFileName": "TRNS_DOWNLOAD_20260319.xls",
      "createdAt": "2026-03-19T10:41:48+09:00",
      "updatedAt": "2026-03-19T10:41:49+09:00",
      "solver": "SCIP",
      "maxSamples": 10,
      "randomSeed": 42,
      "caseCount": 1,
      "bestCaseName": "best_model",
      "bestTotalCost": 105015282.0,
      "bestTotalInboundQty": 63789.0,
      "requiredWarehouseQty": 10,
      "errorSummary": null
    }
  ]
}
```

## 6.5 `GET /runs/{runId}`

### Response `200`

```json
{
  "run": {
    "runId": "run_20260319104148",
    "status": "completed",
    "inputFileName": "TRNS_DOWNLOAD_20260319.xls",
    "createdAt": "2026-03-19T10:41:48+09:00",
    "updatedAt": "2026-03-19T10:41:49+09:00",
    "solver": "SCIP",
    "maxSamples": 10,
    "randomSeed": 42,
    "caseCount": 1,
    "bestCaseName": "best_model",
    "bestTotalCost": 105015282.0,
    "bestTotalInboundQty": 63789.0,
    "requiredWarehouseQty": 10,
    "errorSummary": null
  },
  "simulation": {
    "simulationName": "Makro_Hub_10",
    "structure": "TRNS3",
    "warehouseQty": 10,
    "speedKmh": 60.0,
    "coverageHours": 2.0
  }
}
```

## 6.6 `GET /runs/{runId}/input/simulation`

### Response `200`

```json
{
  "rows": [
    {
      "simulationName": "Makro_Hub_10",
      "status": "COMPLETED",
      "structure": "TRNS3",
      "warehouseQty": 10,
      "speedKmh": 60.0,
      "coverageHours": 2.0
    }
  ]
}
```

## 6.7 `GET /runs/{runId}/input/plants`

### Response `200`

```json
{
  "rows": [
    {
      "plantId": "CDC",
      "locationName": "Wang Noi CDC",
      "latitude": 14.183173,
      "longitude": 100.646494,
      "productQty": 63789.0,
      "shipmentQty": 4253.0
    }
  ]
}
```

## 6.8 `GET /runs/{runId}/input/warehouses`

### Response `200`

```json
{
  "rows": [
    {
      "warehouseId": "Hub_9",
      "locationName": "Hub_9",
      "latitude": 19.016131,
      "longitude": 99.517041,
      "capacityQty": 6708.0,
      "fixedCost": 918000.0,
      "operationCost": 30.0,
      "activeYn": "F",
      "includedInModel": true
    }
  ]
}
```

## 6.9 `GET /runs/{runId}/input/customers`

### Response `200`

```json
{
  "rows": [
    {
      "customerId": "96220_Chae",
      "locationName": "Chanae",
      "latitude": 6.057088,
      "longitude": 101.695444,
      "doQty": 12.0,
      "shipmentQty": 2.0,
      "mappingId": "Hub_1"
    }
  ]
}
```

## 6.10 `GET /runs/{runId}/input/plant-warehouse-arcs`

### Response `200`

```json
{
  "rows": [
    {
      "plantId": "CDC",
      "warehouseId": "Hub_1",
      "distanceKm": 973.15,
      "distanceType": null,
      "trnsCost": 1752.0
    }
  ]
}
```

## 6.11 `GET /runs/{runId}/input/warehouse-customer-arcs`

### Response `200`

```json
{
  "rows": [
    {
      "warehouseId": "Hub_1",
      "customerId": "10100_Poai",
      "distanceKm": 920.86,
      "distanceType": null,
      "trnsCost": 5870.0
    }
  ]
}
```

## 6.12 `GET /runs/{runId}/validation-issues`

### Response `200`

```json
{
  "summary": {
    "errorCount": 0,
    "warningCount": 1,
    "infoCount": 4,
    "blocking": false
  },
  "issues": [
    {
      "issueId": "validation_001",
      "severity": "warning",
      "ruleCode": "WAREHOUSE_FILTER_APPLIED",
      "ruleName": "Warehouse active filter applied",
      "message": "Only warehouses with Active Y/N in {Y, F} are included.",
      "recommendation": null,
      "affectedEntityType": "warehouse",
      "affectedCount": 10,
      "affectedRefs": [],
      "blocking": false
    }
  ]
}
```

## 6.13 `GET /runs/{runId}/summary`

### Response `200`

```json
{
  "rows": [
    {
      "caseName": "best_model",
      "caseType": "best",
      "totalRank": 1,
      "costRank": 1,
      "optimalCost": 105015282.0,
      "optimalTotalInboundQty": 63789.0,
      "optimalTotalOutboundQty": 63345.0,
      "inboundCost": 41509889.0,
      "warehouseCost": 11080350.0,
      "outboundCost": 52425043.0,
      "leadTimeRank": 1,
      "optimalLeadTimeSec": 65964908.0958,
      "inboundLeadTimeSec": 325359.8958,
      "outboundLeadTimeSec": 65639548.2,
      "coverageRankTime": 1,
      "coverageTimePct": 40.1075,
      "coverageRankVol": 1,
      "coverageVolPct": 50.4397,
      "costScore": 1.0,
      "leadTimeScore": 1.0,
      "coverageTimeScore": 1.0,
      "coverageVolScore": 1.0,
      "coverageScore": 1.0,
      "totalScore": 1.0,
      "selectedWarehouseCount": 10,
      "selectedWarehouses": ["Hub_1", "Hub_10"],
      "carbonEmissionTco2eq": 0.0
    }
  ]
}
```

## 6.14 `GET /runs/{runId}/cases`

### Response `200`

```json
{
  "cases": [
    {
      "caseName": "best_model",
      "caseType": "best",
      "totalRank": 1,
      "optimalCost": 105015282.0
    }
  ]
}
```

## 6.15 `GET /runs/{runId}/cases/{caseName}/warehouse-summary`

### Response `200`

```json
{
  "rows": [
    {
      "warehouseId": "Hub_1",
      "warehouseLocationName": "Hub_1",
      "inboundQty": 2574.0,
      "outboundQty": 2574.0,
      "throughputCapacityQty": 2574.0,
      "capacityUtilizationPct": 100.0,
      "fixedCost": 918000.0,
      "operationCost": 77220.0,
      "assignedCustomerCount": 66,
      "coveredCustomerPct": 21.2,
      "coveredDoQtyPct": 31.8
    }
  ]
}
```

## 6.16 `GET /runs/{runId}/cases/{caseName}/plant-warehouse-routes`

### Response `200`

```json
{
  "rows": [
    {
      "plantId": "CDC",
      "plantLocationName": "Wang Noi CDC",
      "warehouseId": "Hub_1",
      "warehouseLocationName": "Hub_1",
      "doQty": 2574.0,
      "cost": 4509648.0,
      "shipmentQtyRatio": 0.6052,
      "leadTimeSec": 35338.1815,
      "distanceKm": 973.15,
      "carbonEmissionTco2eq": 0.0
    }
  ]
}
```

## 6.17 `GET /runs/{runId}/cases/{caseName}/warehouse-customer-routes`

### Response `200`

```json
{
  "rows": [
    {
      "warehouseId": "Hub_1",
      "warehouseLocationName": "Hub_1",
      "customerId": "80170_Huai",
      "customerLocationName": "Hua Sai",
      "doQty": 39.0,
      "cost": 49491.0,
      "shipmentQty": 5.0,
      "leadTimeSec": 59721.0,
      "distanceKm": 199.07,
      "oneWayTimeSec": 11944.2,
      "coverageYn": "N",
      "operationCost": 1170.0,
      "carbonEmissionTco2eq": 0.0,
      "mappingId": "Hub_1"
    }
  ]
}
```

## 6.18 `GET /runs/{runId}/cases/{caseName}/coverage-details`

### Response `200`

```json
{
  "rows": [
    {
      "warehouseId": "Hub_1",
      "customerId": "80170_Huai",
      "assignedDoQty": 39.0,
      "customerShipmentQty": 5.0,
      "plantWarehouseLeadTimeSec": 35338.1815,
      "warehouseCustomerLeadTimeSec": 59721.0,
      "totalLeadTimeSec": 95059.1815,
      "coverageHour": 2.0,
      "oneWayTimeSec": 11944.2,
      "coverageYn": "N"
    }
  ]
}
```

---

## 7. 실행 로그/상태 확장 응답

실행 중 상태 표시를 위해 선택적으로 아래 endpoint를 둘 수 있다.

## 7.1 `GET /runs/{runId}/events`

### 목적

실행 timeline 또는 polling 기반 상태 갱신

### Response `200`

```json
{
  "events": [
    {
      "timestamp": "2026-03-19T10:41:48+09:00",
      "level": "INFO",
      "message": "Loading workbook"
    },
    {
      "timestamp": "2026-03-19T10:41:49+09:00",
      "level": "INFO",
      "message": "Workflow completed successfully"
    }
  ]
}
```

---

## 8. 프론트엔드 타입 생성 권장안

프론트엔드에서는 아래 타입 파일로 분리하면 좋다.

- `run.ts`
- `input.ts`
- `validation.ts`
- `summary.ts`
- `route.ts`
- `coverage.ts`

### 예시

```ts
export type RunStatus =
  | 'uploaded'
  | 'validating'
  | 'validation_failed'
  | 'ready'
  | 'running'
  | 'completed'
  | 'failed';
```

---

## 9. 백엔드 구현 메모

### 현재 코드와 직접 매핑되는 값

- `summary_df`
- `warehouse_summary`
- `plant_warehouse_routes`
- `warehouse_customer_routes`
- `coverage_detail`
- `simulation`

### API 레이어에서 추가 정규화가 필요한 값

- `selectedWarehouses`: string -> string[]
- `mappingId`를 결과 route row에 join
- `capacityUtilizationPct`
- `assignedCustomerCount`
- `coveredCustomerPct`
- `coveredDoQtyPct`

즉, API는 단순 파일 전달이 아니라 웹 분석용 view model을 만들어 주는 계층이어야 한다.

---

## 10. 최종 권고

백엔드 API는 "CLI 결과 파일을 그대로 노출하는 구조"보다, 현재 Python 모델 출력을 기반으로 웹 화면에 맞는 정규화 JSON을 제공하는 구조가 맞다.

이 문서를 기준으로 프론트엔드 타입 선언과 백엔드 response schema를 동시에 고정하는 것이 가장 효율적이다.
