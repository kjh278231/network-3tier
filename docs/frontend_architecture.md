# Network 3-Tier Optimizer Web App 프론트엔드 구조 설계서

## 1. 문서 목적

본 문서는 아래 두 문서를 기반으로 실제 프론트엔드 구현 구조를 정의한다.

- [web_app_planning.md](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/web_app_planning.md)
- [web_app_wireframes.md](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/web_app_wireframes.md)

이 문서의 목적은 다음이다.

- 프론트엔드 폴더 구조 정의
- 라우팅 구조 정의
- 페이지별 컴포넌트 트리 정의
- 상태관리 경계 정의
- API 연동 구조 정의
- MVP 구현 순서에 맞는 모듈 분리 기준 제시

---

## 2. 권장 기술 스택

### 프레임워크

- React
- TypeScript
- Vite

### 라우팅

- React Router

### 서버 상태

- TanStack Query

### 전역 UI 상태

- Zustand 또는 React Context + reducer

### 테이블

- TanStack Table

### 차트

- ECharts 또는 Recharts

### 지도

- MapLibre GL 또는 Leaflet

### 그래프

- Cytoscape.js

### 스타일

- CSS Modules 또는 Tailwind 중 하나로 일관성 유지

### 권장 결론

가장 현실적인 조합은 아래다.

- `React + TypeScript + Vite`
- `React Router`
- `TanStack Query`
- `Zustand`
- `TanStack Table`
- `ECharts`
- `MapLibre GL`
- `Cytoscape.js`

---

## 3. 프론트엔드 설계 원칙

### 원칙 1. run 중심 구조

모든 화면은 `run`을 중심 컨텍스트로 동작해야 한다.

- 어떤 파일을 올렸는가
- 어떤 validation 결과인가
- 어떤 case를 보고 있는가

이 3가지는 모든 페이지에 일관되게 전달되어야 한다.

### 원칙 2. 페이지와 분석 위젯 분리

페이지는 화면 조립과 라우팅을 담당하고, 차트/테이블/필터는 재사용 위젯으로 분리한다.

### 원칙 3. 서버 상태와 UI 상태 분리

- 서버 상태: API 응답, loading, error, cache
- UI 상태: 선택된 case, 선택된 warehouse, 패널 열림 상태, layout 모드

### 원칙 4. drill-down 상태 공유

Map, Graph, Table, KPI 카드가 같은 selection state를 공유해야 한다.

예:

- warehouse 선택
- customer 선택
- route 선택
- coverage filter

### 원칙 5. 결과 화면 공통 패턴 유지

Summary, Map, Graph, Warehouse, Customer, Route는 모두 같은 shell 위에서 동작해야 한다.

---

## 4. 권장 폴더 구조

```text
frontend/
|-- index.html
|-- package.json
|-- tsconfig.json
|-- vite.config.ts
|-- src/
|   |-- main.tsx
|   |-- app/
|   |   |-- App.tsx
|   |   |-- providers/
|   |   |   |-- router-provider.tsx
|   |   |   |-- query-provider.tsx
|   |   |   `-- theme-provider.tsx
|   |   |-- router/
|   |   |   |-- routes.tsx
|   |   |   `-- route-guards.tsx
|   |   |-- layout/
|   |   |   |-- app-shell.tsx
|   |   |   |-- top-bar.tsx
|   |   |   |-- side-nav.tsx
|   |   |   |-- right-panel.tsx
|   |   |   `-- bottom-panel.tsx
|   |   `-- store/
|   |       |-- ui-store.ts
|   |       |-- run-context-store.ts
|   |       `-- selection-store.ts
|   |-- pages/
|   |   |-- home/
|   |   |   `-- home-page.tsx
|   |   |-- runs/
|   |   |   |-- upload-run-page.tsx
|   |   |   |-- input-analysis-page.tsx
|   |   |   |-- validation-page.tsx
|   |   |   |-- summary-page.tsx
|   |   |   |-- map-page.tsx
|   |   |   |-- graph-page.tsx
|   |   |   |-- warehouse-page.tsx
|   |   |   |-- customer-page.tsx
|   |   |   |-- route-page.tsx
|   |   |   |-- scenario-compare-page.tsx
|   |   |   `-- explain-page.tsx
|   |-- features/
|   |   |-- runs/
|   |   |   |-- api/
|   |   |   |   |-- get-runs.ts
|   |   |   |   |-- get-run.ts
|   |   |   |   |-- upload-run.ts
|   |   |   |   |-- validate-run.ts
|   |   |   |   `-- execute-run.ts
|   |   |   |-- hooks/
|   |   |   |   |-- use-runs.ts
|   |   |   |   `-- use-run.ts
|   |   |   `-- components/
|   |   |       |-- run-status-chip.tsx
|   |   |       |-- run-list-table.tsx
|   |   |       `-- run-meta-card.tsx
|   |   |-- input-analysis/
|   |   |   |-- api/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- simulation-panel.tsx
|   |   |       |-- plants-table.tsx
|   |   |       |-- warehouses-table.tsx
|   |   |       |-- customers-table.tsx
|   |   |       |-- pw-arcs-table.tsx
|   |   |       `-- wc-arcs-table.tsx
|   |   |-- validation/
|   |   |   |-- api/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- validation-summary.tsx
|   |   |       |-- validation-rule-list.tsx
|   |   |       |-- validation-rule-detail.tsx
|   |   |       `-- affected-rows-table.tsx
|   |   |-- summary/
|   |   |   |-- api/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- kpi-cards.tsx
|   |   |       |-- cost-breakdown-chart.tsx
|   |   |       |-- case-comparison-chart.tsx
|   |   |       |-- score-radar-chart.tsx
|   |   |       `-- selected-warehouses.tsx
|   |   |-- map/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- network-map.tsx
|   |   |       |-- map-legend.tsx
|   |   |       |-- layer-toggle.tsx
|   |   |       `-- map-selection-detail.tsx
|   |   |-- graph/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- network-graph.tsx
|   |   |       |-- graph-layout-switcher.tsx
|   |   |       |-- graph-legend.tsx
|   |   |       `-- graph-selection-detail.tsx
|   |   |-- warehouse/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- warehouse-kpis.tsx
|   |   |       |-- warehouse-utilization-chart.tsx
|   |   |       |-- warehouse-table.tsx
|   |   |       `-- warehouse-detail-card.tsx
|   |   |-- customer/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- customer-kpis.tsx
|   |   |       |-- customer-scatter-chart.tsx
|   |   |       |-- customer-table.tsx
|   |   |       `-- customer-detail-card.tsx
|   |   |-- route/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- route-subtabs.tsx
|   |   |       |-- pw-route-table.tsx
|   |   |       |-- wc-route-table.tsx
|   |   |       `-- route-detail-card.tsx
|   |   |-- scenario-compare/
|   |   |   |-- hooks/
|   |   |   `-- components/
|   |   |       |-- case-selector.tsx
|   |   |       |-- delta-kpi-cards.tsx
|   |   |       |-- compare-scatter.tsx
|   |   |       |-- warehouse-diff-panel.tsx
|   |   |       `-- compare-table.tsx
|   |   `-- explain/
|   |       `-- components/
|   |           |-- explain-nav.tsx
|   |           |-- formula-card.tsx
|   |           `-- glossary.tsx
|   |-- shared/
|   |   |-- api/
|   |   |   |-- client.ts
|   |   |   |-- types.ts
|   |   |   `-- query-keys.ts
|   |   |-- components/
|   |   |   |-- ui/
|   |   |   |   |-- button.tsx
|   |   |   |   |-- card.tsx
|   |   |   |   |-- chip.tsx
|   |   |   |   |-- tabs.tsx
|   |   |   |   |-- select.tsx
|   |   |   |   `-- drawer.tsx
|   |   |   |-- data-grid/
|   |   |   |   |-- data-grid.tsx
|   |   |   |   |-- data-grid-toolbar.tsx
|   |   |   |   `-- column-visibility.tsx
|   |   |   |-- filters/
|   |   |   |   |-- case-filter.tsx
|   |   |   |   |-- warehouse-filter.tsx
|   |   |   |   |-- customer-filter.tsx
|   |   |   |   `-- coverage-filter.tsx
|   |   |   |-- kpi/
|   |   |   |   |-- kpi-card.tsx
|   |   |   |   `-- kpi-row.tsx
|   |   |   `-- empty-state.tsx
|   |   |-- hooks/
|   |   |   |-- use-debounced-value.ts
|   |   |   |-- use-url-state.ts
|   |   |   `-- use-selection-sync.ts
|   |   |-- utils/
|   |   |   |-- format-number.ts
|   |   |   |-- format-seconds.ts
|   |   |   |-- format-percent.ts
|   |   |   `-- export-csv.ts
|   |   `-- constants/
|   |       |-- routes.ts
|   |       `-- colors.ts
|   `-- styles/
|       |-- globals.css
|       `-- theme.css
```

---

## 5. 라우팅 구조

### 5.1 최상위 라우트

```text
/
/runs/new
/runs/:runId
/runs/:runId/input
/runs/:runId/validation
/runs/:runId/summary
/runs/:runId/map
/runs/:runId/graph
/runs/:runId/warehouse
/runs/:runId/customer
/runs/:runId/route
/runs/:runId/compare
/runs/:runId/explain
```

### 5.2 권장 상세 구조

```text
/
└── home-page

/runs/new
└── upload-run-page

/runs/:runId
└── redirect to /runs/:runId/summary

/runs/:runId/input
└── input-analysis-page
    ├── ?tab=simulation
    ├── ?tab=plants
    ├── ?tab=warehouses
    ├── ?tab=customers
    ├── ?tab=pw-arcs
    └── ?tab=wc-arcs

/runs/:runId/validation
└── validation-page

/runs/:runId/summary
└── summary-page
    └── ?case=best_model

/runs/:runId/map
└── map-page
    └── ?case=best_model

/runs/:runId/graph
└── graph-page
    └── ?case=best_model&layout=layered

/runs/:runId/warehouse
└── warehouse-page
    └── ?case=best_model&warehouse=Hub_1

/runs/:runId/customer
└── customer-page
    └── ?case=best_model&customer=96220_Chae

/runs/:runId/route
└── route-page
    └── ?case=best_model&tab=wc

/runs/:runId/compare
└── scenario-compare-page
    └── ?base=best_model&target=sampled_case_1

/runs/:runId/explain
└── explain-page
```

### 5.3 URL 상태로 유지할 항목

- `case`
- `warehouse`
- `customer`
- `layout`
- `tab`
- `coverageOnly`
- `mappingOnly`
- `topN`
- `compare target`

이 값들은 URL query로 유지해야 공유 링크와 복구가 가능하다.

---

## 6. 페이지별 컴포넌트 트리

## 6.1 App Shell

```text
App
└── AppProviders
    └── RouterProvider
        └── AppShell
            ├── TopBar
            ├── SideNav
            ├── MainOutlet
            ├── RightContextPanel
            └── BottomDataPanel
```

### 책임

- run/case 컨텍스트 표시
- 공통 네비게이션 제공
- 공통 패널 영역 제공
- 페이지별 slot 구성

## 6.2 Home Page

```text
HomePage
├── KPIRow
│   ├── KpiCard
│   ├── KpiCard
│   └── KpiCard
├── RunListTable
├── FailedRunList
└── QuickActions
```

## 6.3 Upload Run Page

```text
UploadRunPage
├── UploadZone
├── RunMetaCard
├── RunSettingsForm
├── ValidationSummaryBanner
├── ExecutionTimeline
├── LogStreamPanel
└── ActionBar
```

## 6.4 Input Analysis Page

```text
InputAnalysisPage
├── InputTabBar
├── InputKpiRow
├── InputVisualizationPanel
│   ├── Histogram or SummaryCardGroup
│   └── ContextStats
├── InputDataGrid
└── RowDetailDrawer
```

## 6.5 Validation Page

```text
ValidationPage
├── ValidationSummary
├── ValidationRuleList
├── ValidationRuleDetail
└── AffectedRowsTable
```

## 6.6 Summary Page

```text
SummaryPage
├── CaseSelector
├── KpiRow
├── CostBreakdownChart
├── CaseComparisonChart
├── ScoreRadarChart
├── SelectedWarehouses
└── SummaryTable
```

## 6.7 Map Page

```text
MapPage
├── CaseSelector
├── LayerToggle
├── NetworkMap
├── MapLegend
├── MapSelectionDetail
└── LinkedRouteTable
```

## 6.8 Graph Page

```text
GraphPage
├── CaseSelector
├── GraphLayoutSwitcher
├── GraphFilterPanel
├── NetworkGraph
├── GraphLegend
├── GraphSelectionDetail
└── LinkedEdgesTable
```

## 6.9 Warehouse Page

```text
WarehousePage
├── CaseSelector
├── WarehouseKpis
├── WarehouseUtilizationChart
├── WarehouseCostChart
├── WarehouseTable
└── WarehouseDetailCard
```

## 6.10 Customer Page

```text
CustomerPage
├── CaseSelector
├── CustomerKpis
├── CustomerScatterChart
├── CustomerTable
└── CustomerDetailCard
```

## 6.11 Route Page

```text
RoutePage
├── CaseSelector
├── RouteSubtabs
├── RouteKpiRow
├── RouteChartPanel
├── PwRouteTable or WcRouteTable
└── RouteDetailCard
```

## 6.12 Scenario Compare Page

```text
ScenarioComparePage
├── BaseCaseSelector
├── TargetCaseSelector
├── DeltaKpiCards
├── CompareScatter
├── WarehouseDiffPanel
├── CompareTable
└── CompareInsightPanel
```

## 6.13 Explain Page

```text
ExplainPage
├── ExplainNav
├── ProblemDefinitionSection
├── ConstraintSection
├── ObjectiveSection
├── LeadtimeCoverageSection
├── RankingSection
└── Glossary
```

---

## 7. 상태관리 구조

## 7.1 서버 상태

TanStack Query로 관리할 대상:

- run 목록
- run 메타
- input tables
- validation issues
- summary data
- case details
- route data
- coverage data

### query key 예시

```text
['runs']
['run', runId]
['run', runId, 'input', 'warehouses']
['run', runId, 'validation']
['run', runId, 'summary']
['run', runId, 'case', caseName, 'warehouse-summary']
['run', runId, 'case', caseName, 'pw-routes']
['run', runId, 'case', caseName, 'wc-routes']
['run', runId, 'case', caseName, 'coverage']
```

## 7.2 UI 상태

Zustand 등으로 관리할 대상:

- selectedCase
- selectedWarehouse
- selectedCustomer
- selectedRoute
- selectedValidationRule
- graphLayout
- mapLayers
- rightPanelOpen
- bottomPanelMode

## 7.3 URL 상태

URL query로 반영할 대상:

- case
- tab
- warehouse
- customer
- coverageOnly
- mappingOnly
- layout
- compare target

### 경계 기준

- 새로고침 후 복원 필요: URL 상태
- 여러 위젯이 공유해야 함: 전역 UI 상태
- 서버에서 받아오는 원본: 서버 상태

---

## 8. API Client 구조

## 8.1 공통 API client

`shared/api/client.ts`

책임:

- base URL 설정
- 공통 error 처리
- JSON 파싱
- 업로드 요청 지원

## 8.2 feature별 API 모듈

예시:

- `features/runs/api/upload-run.ts`
- `features/validation/api/get-validation-issues.ts`
- `features/summary/api/get-summary.ts`

원칙:

- page에서 직접 `fetch`하지 않는다
- API 응답 shape는 feature 내부에서 normalize 한다

## 8.3 타입 구조

`shared/api/types.ts`에는 최소 아래 타입이 필요하다.

- `Run`
- `RunStatus`
- `ValidationIssue`
- `CaseSummary`
- `WarehouseSummaryRow`
- `PlantWarehouseRouteRow`
- `WarehouseCustomerRouteRow`
- `CoverageDetailRow`

---

## 9. selection state 공유 설계

Map, Graph, Warehouse Table, Customer Table가 서로 선택 상태를 공유해야 한다.

### 예시

#### warehouse 선택 시

- Warehouse page에서 warehouse 선택
- Map page에서 해당 warehouse marker 강조
- Graph page에서 해당 warehouse ego-network 강조
- Customer page에서 해당 warehouse 담당 고객만 필터
- Route page에서 해당 warehouse 관련 route만 표시

#### customer 선택 시

- Customer page에서 customer 선택
- Map page에서 customer location 표시
- Graph page에서 assigned edge 강조
- Route page에서 해당 route 상세 표시

### 권장 구현

- `selection-store.ts`에 공통 selection 저장
- 각 page는 `useSelectionSync` 훅으로 URL과 store를 동기화

---

## 10. 공통 재사용 컴포넌트 우선순위

초기에 꼭 먼저 만들어야 하는 공통 컴포넌트는 아래다.

1. `AppShell`
2. `KpiCard`
3. `DataGrid`
4. `CaseSelector`
5. `WarehouseFilter`
6. `CoverageFilter`
7. `RightPanel`
8. `EmptyState`
9. `RunStatusChip`
10. `DetailCard`

이 컴포넌트들이 먼저 안정화되면 나머지 페이지 조립 속도가 빨라진다.

---

## 11. MVP 구현 순서

### Step 1. 앱 골격

- Vite 초기화
- Router 구성
- AppShell 구성
- 공통 UI 컴포넌트 구성

### Step 2. 데이터 접근

- API client
- Query provider
- run 목록 / run 메타 조회

### Step 3. 실행 전 화면

- Home
- Upload & Run
- Input Analysis
- Validation

### Step 4. 결과 분석 기본 화면

- Summary
- Warehouse
- Customer
- Route

### Step 5. 시각화 확장

- Map
- Scenario Compare
- Graph

### Step 6. 설명/완성도 보강

- Explain
- export
- deep link
- loading / error polish

---

## 12. 권장 코드 경계

### pages

- 라우트 단위 화면 조립
- 데이터를 직접 가공하지 않음

### features

- 기능 단위 도메인 로직
- API, 훅, feature 전용 컴포넌트 포함

### shared

- 전역 재사용 컴포넌트/유틸/상수

### app

- 앱 초기화, provider, shell, router

---

## 13. 백엔드 연동 전 임시 모드

프론트엔드 초기 개발 시에는 mock 데이터를 사용할 수 있다.

### 권장 방식

- `shared/api/mock/`에 샘플 JSON 저장
- 실제 `output_summary.xls`, `output_case*.xls`를 JSON으로 변환한 fixture 생성
- 환경변수로 `mock mode` 전환

### 장점

- 백엔드 완료 전 UI 작업 가능
- Summary/Warehouse/Customer/Route 화면 병렬 개발 가능

---

## 14. 개발 산출물 체크리스트

프론트엔드 착수 전 아래 항목이 준비되면 좋다.

- API 응답 스키마 초안
- run 상태 enum 정의
- validation issue 구조 정의
- case summary 구조 정의
- warehouse/customer/route row 타입 정의
- mock JSON 1세트

---

## 15. 최종 권고

프론트엔드는 `run 기반 라우팅 + feature 기반 폴더 구조 + 공통 shell + shared selection state`로 설계하는 것이 가장 적절하다.

이 구조를 쓰면 현재 요구사항인 입력 검증, 실행, 지도 분석, 그래프 분석, 시나리오 비교를 무리 없이 확장할 수 있다.
