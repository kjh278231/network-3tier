# Network 3-Tier Optimizer Web App 화면별 와이어프레임 명세서

## 1. 문서 목적

본 문서는 [web_app_planning.md](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/web_app_planning.md)를 바탕으로 실제 구현 가능한 수준의 화면 와이어프레임을 정의한다.

이 문서는 디자인 시안이 아니라 다음을 명확히 하기 위한 개발 명세서다.

- 화면별 레이아웃 구조
- 컴포넌트 구성
- 주요 상태
- 핵심 인터랙션
- 화면 간 이동 흐름
- 백엔드 API 연결 포인트

---

## 2. 공통 레이아웃 규칙

### 2.1 데스크톱 기본 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar: Project / Run / Case / Status / Global Actions                          |
+----------------------+----------------------------------------+------------------+
| Left Navigation      | Main Content                           | Right Context    |
| - Home               | - KPI / Chart / Map / Graph / Table   | - Filters        |
| - Upload & Run       | - Primary analysis area               | - Selected item  |
| - Input Analysis     | - Drill-down panel                    | - Summary cards  |
| - Validation         |                                        |                  |
| - Summary            |                                        |                  |
| - Map                |                                        |                  |
| - Graph              |                                        |                  |
| - Warehouse          |                                        |                  |
| - Customer           |                                        |                  |
| - Route              |                                        |                  |
| - Scenario Compare   |                                        |                  |
| - Explain            |                                        |                  |
+----------------------+----------------------------------------+------------------+
| Bottom Table / Detail Drawer / Logs                                                |
+----------------------------------------------------------------------------------+
```

### 2.2 공통 UI 규칙

- 상단바에는 항상 현재 `run`, `case`, `status`를 노출한다.
- 우측 패널은 화면별 필터와 선택 객체 상세를 담당한다.
- 하단 영역은 원본 테이블 또는 로그를 보여준다.
- KPI 카드에서 drill-down 가능한 모든 요소는 클릭 가능해야 한다.
- 화면 이동 시 run/case 컨텍스트는 유지된다.

### 2.3 상태 규칙

- `no_run`: 아직 업로드/실행 전
- `validating`: validation 실행 중
- `validation_failed`: 실행 차단 상태
- `running`: 최적화 실행 중
- `completed`: 결과 조회 가능
- `failed`: 실행 실패

---

## 3. 전역 컴포넌트 명세

## 3.1 Top Bar

### 표시 항목

- Project name
- Run ID
- Input file name
- Current case selector
- Run status chip
- Last updated time

### 액션

- Re-validate
- Re-run
- Export summary
- Share link

## 3.2 Left Navigation

### 메뉴

- Home
- Upload & Run
- Input Analysis
- Validation
- Summary
- Map
- Graph
- Warehouse
- Customer
- Route
- Scenario Compare
- Explain

### 규칙

- `completed` 전에는 결과 화면 비활성화 가능
- `validation_failed` 상태에서는 Explain과 Input Analysis는 열리지만 실행 관련 CTA는 비활성화

## 3.3 Right Context Panel

### 공통 영역

- Global filters
- Current selection summary
- KPI mini cards
- Reset selection

### 기본 필터

- Case
- Warehouse
- Customer
- Coverage YN
- Mapping ID only
- Top N

## 3.4 Bottom Data Panel

### 역할

- 원본 데이터 검증
- 선택 결과 drill-down
- 정렬/필터/검색
- CSV export

---

## 4. 화면별 와이어프레임

## 4.1 Home / Run 목록

### 목적

사용자가 최근 실행 이력과 현재 프로젝트 상태를 빠르게 파악한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+-----------------------------------------------------------+
| Left Nav             | [KPI] Latest Best Cost | Latest Coverage | Success Rate   |
|                      +-----------------------------------------------------------+
|                      | Recent Runs Table                                         |
|                      | Run ID | File | Status | Best Cost | Coverage | Time      |
|                      +-----------------------------------------------------------+
|                      | Failed Runs / Warnings                                    |
|                      +-----------------------------------------------------------+
|                      | Quick Actions: New Upload / Reopen Latest / Compare Runs   |
+----------------------+-----------------------------------------------------------+
```

### 핵심 컴포넌트

- KPI cards
- Recent runs table
- Failed runs list
- Quick action buttons

### 상태

- empty state: run 없음
- list state
- loading state

### 인터랙션

- run row 클릭 -> Summary 화면으로 이동
- failed row 클릭 -> Validation 또는 log drawer 열기

### 연결 API

- `GET /runs`
- `GET /runs/{runId}`

---

## 4.2 Upload & Run

### 목적

입력 workbook을 업로드하고 validation 및 실행을 제어한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+----------------------------------------+------------------+
| Left Nav             | Upload Zone                            | Run Settings     |
|                      | - drag & drop                          | - solver         |
|                      | - selected file meta                   | - max samples    |
|                      |                                        | - random seed    |
|                      +----------------------------------------+------------------+
|                      | Validation Summary / Blocking Issues                       |
|                      +-----------------------------------------------------------+
|                      | Execution Timeline / Log Stream                            |
|                      +-----------------------------------------------------------+
|                      | CTA: Validate | Execute | Cancel                           |
+----------------------+-----------------------------------------------------------+
```

### 핵심 컴포넌트

- File uploader
- File metadata card
- Run settings form
- Validation summary banner
- Log stream panel
- Primary CTA group

### 상태

- no file
- file uploaded
- validating
- ready to execute
- running
- failed
- completed

### 인터랙션

- 파일 업로드 시 자동 메타데이터 표시
- Validate 클릭 시 validation summary 갱신
- Execute 클릭 시 log streaming 시작
- Blocking error 존재 시 Execute 비활성화

### 연결 API

- `POST /runs/upload`
- `POST /runs/{runId}/validate`
- `POST /runs/{runId}/execute`
- `GET /runs/{runId}`

---

## 4.3 Input Analysis

### 목적

입력 데이터를 모델 친화적으로 탐색한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+----------------------------------------+------------------+
| Left Nav             | Tab Bar: Simulation | Plants | Warehouses | Customers ... |
|                      +----------------------------------------+------------------+
|                      | KPI Row: total demand / total supply / total capacity      |
|                      +----------------------------------------+------------------+
|                      | Main Grid or Distribution Chart                             |
|                      |                                                            |
|                      +-----------------------------------------------------------+
|                      | Data Table                                                 |
+----------------------+----------------------------------------+------------------+
| Right Panel: column filters / quick stats / selected row detail                    |
+----------------------------------------------------------------------------------+
```

### 탭별 포커스

- Simulation: config card 중심
- Plants: supply/shipment 분석
- Warehouses: capacity/cost/active 상태
- Customers: demand/mapping 분석
- P->W Arc: plant-warehouse 비용/거리
- W->C Arc: warehouse-customer 비용/거리

### 핵심 컴포넌트

- tab navigation
- KPI cards
- histogram or summary chart
- data grid
- column filter panel

### 인터랙션

- warehouse row 클릭 -> 해당 warehouse 관련 arc만 필터
- customer row 클릭 -> Mapping ID와 assignment arc 미리보기
- 탭 간 필터 유지 여부는 선택 옵션으로 제공

### 연결 API

- `GET /runs/{runId}/input/*`

---

## 4.4 Validation

### 목적

실행 가능성과 데이터 품질 문제를 rule 중심으로 보여준다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+----------------------------------------+------------------+
| Left Nav             | Validation KPI: Errors | Warnings | Passed Rules           |
|                      +-----------------------------------------------------------+
|                      | Rule Result List                                          |
|                      | [Severity] Rule Name | Affected Count | Status             |
|                      +-----------------------------------------------------------+
|                      | Selected Rule Detail                                      |
|                      | - meaning                                                 |
|                      | - failure reason                                          |
|                      | - recommendation                                          |
|                      +-----------------------------------------------------------+
|                      | Affected Rows Table                                       |
+----------------------+----------------------------------------+------------------+
```

### 핵심 컴포넌트

- severity summary cards
- rule result list
- rule detail panel
- affected rows table

### 상태

- no validation yet
- validating
- passed
- failed with blocking issues

### 인터랙션

- rule 클릭 -> 하단 affected rows 갱신
- affected row 클릭 -> Input Analysis 특정 탭/행으로 deep link

### 연결 API

- `GET /runs/{runId}/validation-issues`

---

## 4.5 Summary Dashboard

### 목적

한 run의 전체 성능과 case 구조를 요약한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar: Run / Case Selector                                                      |
+----------------------+-----------------------------------------------------------+
| Left Nav             | KPI Cards Row                                             |
|                      | Cost | Inbound Cost | Outbound Cost | Lead Time | Coverage |
|                      +-----------------------------------------------------------+
|                      | Chart Row                                                 |
|                      | [Cost Breakdown] [Case Comparison] [Score Radar]          |
|                      +-----------------------------------------------------------+
|                      | Selected Warehouses Card                                  |
|                      +-----------------------------------------------------------+
|                      | Case Summary Table                                        |
+----------------------+-----------------------------------------------------------+
| Right Panel: case filter / metric toggle / selected KPI explanation               |
+----------------------------------------------------------------------------------+
```

### 핵심 컴포넌트

- KPI cards
- cost breakdown chart
- case comparison bar chart
- score radar chart
- selected warehouses chip list
- summary table

### 인터랙션

- KPI 클릭 -> 관련 상세 화면 이동
- case row 클릭 -> 해당 case 컨텍스트로 전환
- warehouse chip 클릭 -> Warehouse 화면으로 drill-down

### 연결 API

- `GET /runs/{runId}/summary`
- `GET /runs/{runId}/cases`

---

## 4.6 Network Map

### 목적

지리 기반으로 network footprint를 분석한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+----------------------------------------+------------------+
| Left Nav             | Map Canvas                                              |
|                      | - plants                                                |
|                      | - warehouses                                            |
|                      | - customers                                             |
|                      | - P->W routes                                           |
|                      | - W->C routes                                           |
|                      |                                                         |
|                      +---------------------------------------------------------+
|                      | Selected Object Detail / Linked Route Table             |
+----------------------+----------------------------------------+------------------+
| Right Panel: layer toggles / geo filters / coverage filter / legend              |
+----------------------------------------------------------------------------------+
```

### 핵심 컴포넌트

- map canvas
- layer toggle group
- legend
- selected object detail card
- linked route table

### 상태

- no coordinates
- full network
- warehouse focused
- customer focused

### 인터랙션

- warehouse marker 클릭 -> 연결 customer와 upstream flow 강조
- customer marker 클릭 -> assigned warehouse 및 route detail 표시
- coverage filter 적용 시 low coverage customer만 노출

### 지도 툴팁

- Plant: id, supply, shipment qty
- Warehouse: id, inbound, outbound, capacity
- Customer: id, do qty, assigned warehouse, coverage 여부

### 연결 API

- `GET /runs/{runId}/cases/{caseName}/warehouse-summary`
- `GET /runs/{runId}/cases/{caseName}/plant-warehouse-routes`
- `GET /runs/{runId}/cases/{caseName}/warehouse-customer-routes`

---

## 4.7 Network Graph

### 목적

지리가 아니라 연결 구조 자체를 분석한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+----------------------------------------+------------------+
| Left Nav             | Graph Canvas                                              |
|                      | Plant ----> Warehouse ----> Customer                     |
|                      |                                                         |
|                      |                                                         |
|                      +---------------------------------------------------------+
|                      | Linked Routes / Selected Node Detail                     |
+----------------------+----------------------------------------+------------------+
| Right Panel: graph filters / layout switch / legend / node metrics               |
+----------------------------------------------------------------------------------+
```

### 핵심 컴포넌트

- graph canvas
- layout switcher
- node type legend
- node metric summary
- selected node detail panel
- linked edges table

### 상태

- default layered layout
- warehouse focus mode
- high-demand customer filtered mode
- low-coverage filtered mode

### 인터랙션

- node 클릭 -> neighborhood 강조
- edge hover -> qty/cost/lead time tooltip
- layout 변경 -> layered / force / radial
- selected warehouse only 토글

### 노드 상세 패널 항목

- Plant: total outbound, connected warehouses
- Warehouse: inbound, outbound, capacity utilization, customer count
- Customer: do qty, coverage, lead time, assigned warehouse, mapping 여부

### 연결 API

- `GET /runs/{runId}/cases/{caseName}/plant-warehouse-routes`
- `GET /runs/{runId}/cases/{caseName}/warehouse-customer-routes`
- `GET /runs/{runId}/cases/{caseName}/coverage-details`

---

## 4.8 Warehouse Analysis

### 목적

warehouse 운영 관점에서 부담과 효율을 해석한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+-----------------------------------------------------------+
| Left Nav             | KPI: Avg Utilization | Total Fixed Cost | Avg Cust Count  |
|                      +-----------------------------------------------------------+
|                      | Warehouse Utilization Chart                               |
|                      +-----------------------------------------------------------+
|                      | Warehouse Cost / Customer Count Chart                     |
|                      +-----------------------------------------------------------+
|                      | Warehouse Table                                           |
+----------------------+-----------------------------------------------------------+
| Right Panel: warehouse selector / selected warehouse detail / route shortcuts     |
+----------------------------------------------------------------------------------+
```

### 핵심 컴포넌트

- utilization chart
- cost chart
- warehouse table
- selected warehouse detail card

### 인터랙션

- warehouse bar 클릭 -> 상세 panel 및 linked customer table 갱신
- utilization 정렬, fixed cost 정렬, operation cost 정렬

### 연결 API

- `GET /runs/{runId}/cases/{caseName}/warehouse-summary`
- `GET /runs/{runId}/cases/{caseName}/warehouse-customer-routes`

---

## 4.9 Customer Analysis

### 목적

서비스 품질 문제를 customer 단위로 추적한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+-----------------------------------------------------------+
| Left Nav             | KPI: Low Coverage Customers | Worst Lead Time | Mapped Cust|
|                      +-----------------------------------------------------------+
|                      | Customer Scatter / Distribution                            |
|                      | x: Do Qty / y: Lead Time / color: Coverage YN            |
|                      +-----------------------------------------------------------+
|                      | Customer Table                                             |
+----------------------+-----------------------------------------------------------+
| Right Panel: filters / selected customer detail / upstream route preview          |
+----------------------------------------------------------------------------------+
```

### 핵심 컴포넌트

- KPI cards
- customer scatter plot
- customer table
- selected customer detail panel

### 인터랙션

- low coverage filter
- mapped only filter
- selected customer -> route preview
- customer row -> Map/Graph 동기화

### 연결 API

- `GET /runs/{runId}/cases/{caseName}/warehouse-customer-routes`
- `GET /runs/{runId}/cases/{caseName}/coverage-details`

---

## 4.10 Route Analysis

### 목적

운송 경로를 비용과 lead time 기준으로 해석한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+-----------------------------------------------------------+
| Left Nav             | Subtabs: Plant->Warehouse | Warehouse->Customer           |
|                      +-----------------------------------------------------------+
|                      | Route KPI Row                                             |
|                      +-----------------------------------------------------------+
|                      | Route Chart / Top Routes                                  |
|                      +-----------------------------------------------------------+
|                      | Route Table                                               |
+----------------------+-----------------------------------------------------------+
| Right Panel: route filters / selected route detail / export                       |
+----------------------------------------------------------------------------------+
```

### Plant -> Warehouse 탭

- KPI: total inbound cost, avg lead time, top warehouse by inbound
- chart: warehouse별 inbound qty
- table: route별 qty/cost/lead time

### Warehouse -> Customer 탭

- KPI: total outbound cost, low coverage route count, avg one-way time
- chart: high cost route / long lead time route
- table: route별 qty/cost/coverage

### 인터랙션

- route 클릭 -> map/graph highlight
- warehouse filter 적용 시 양 탭 동시 반영

### 연결 API

- `GET /runs/{runId}/cases/{caseName}/plant-warehouse-routes`
- `GET /runs/{runId}/cases/{caseName}/warehouse-customer-routes`

---

## 4.11 Scenario Compare

### 목적

best model과 designated case 간 trade-off를 빠르게 판단한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar: Case A selector | Case B selector                                        |
+----------------------+-----------------------------------------------------------+
| Left Nav             | Delta KPI Cards                                           |
|                      | Cost Δ | Lead Time Δ | Coverage Δ | Warehouse Swap Count  |
|                      +-----------------------------------------------------------+
|                      | Scatter / Frontier View                                   |
|                      +-----------------------------------------------------------+
|                      | Warehouse Diff Panel                                      |
|                      +-----------------------------------------------------------+
|                      | Case Comparison Table                                     |
+----------------------+-----------------------------------------------------------+
| Right Panel: compare mode / metric selector / significance notes                  |
+----------------------------------------------------------------------------------+
```

### 핵심 컴포넌트

- case selectors
- delta KPI cards
- cost vs coverage scatter
- warehouse diff panel
- comparison table

### 인터랙션

- case 선택 시 전체 delta 재계산
- warehouse diff 클릭 시 영향 customer 추적
- best 기준 toggle

### 연결 API

- `GET /runs/{runId}/summary`
- `GET /runs/{runId}/cases/{caseName}/*`

---

## 4.12 Explain

### 목적

모델과 지표 정의를 설명한다.

### 레이아웃

```text
+----------------------------------------------------------------------------------+
| Top Bar                                                                           |
+----------------------+-----------------------------------------------------------+
| Left Nav             | Section Nav: Problem / Constraints / Objective / Ranking  |
|                      +-----------------------------------------------------------+
|                      | Rich Content Area                                         |
|                      | - text                                                    |
|                      | - formulas                                                |
|                      | - examples                                                |
|                      +-----------------------------------------------------------+
|                      | Glossary / FAQ                                            |
+----------------------+-----------------------------------------------------------+
```

### 핵심 컴포넌트

- section navigation
- formula cards
- glossary
- FAQ accordion

### 연결 데이터

- README 기반 설명
- IR 문서 기반 설명

---

## 5. 핵심 화면 연결 흐름

### 흐름 A. 실행 전

`Home -> Upload & Run -> Input Analysis -> Validation`

### 흐름 B. 실행 후 요약 확인

`Validation -> Upload & Run -> Summary Dashboard`

### 흐름 C. 문제 원인 분석

`Summary -> Warehouse Analysis -> Customer Analysis -> Route Analysis`

### 흐름 D. 공간/구조 분석

`Summary -> Network Map`

`Summary -> Network Graph`

### 흐름 E. 대안 비교

`Summary -> Scenario Compare -> Warehouse Diff -> Customer Impact`

---

## 6. 반응형 규칙

### Desktop

- 전체 3단 레이아웃 유지
- 지도/그래프와 테이블 동시 노출

### Tablet

- 우측 패널은 drawer 형태로 축소
- 하단 테이블은 탭 또는 접이식 영역으로 전환

### Mobile

- 조회 전용
- 맵/그래프는 단순 보기
- 테이블 편집성 기능 최소화

---

## 7. MVP 우선 화면

개발 1차 범위는 아래 순서가 적절하다.

1. Home
2. Upload & Run
3. Input Analysis
4. Validation
5. Summary Dashboard
6. Warehouse Analysis
7. Customer Analysis
8. Route Analysis
9. Network Map
10. Scenario Compare
11. Network Graph
12. Explain

그래프 화면은 중요하지만, 초기에는 결과 해석을 위한 기본 표/차트/지도 흐름이 먼저 안정화된 뒤 붙이는 편이 구현 리스크가 낮다.

---

## 8. 개발 전달 메모

### 디자이너에게

- KPI 카드와 데이터 테이블의 정보밀도를 높게 유지해야 한다
- 과도한 장식보다 분석 효율을 우선한다
- 상태 색상은 `success / warning / error / selected`가 명확해야 한다

### 프론트엔드 개발자에게

- 전역 상태는 `run`, `case`, `selection`, `filters`를 기준으로 설계한다
- Map과 Graph, Table이 selection state를 공유해야 한다
- 화면 간 deep link와 URL query state를 고려한다

### 백엔드 개발자에게

- run 중심 API 설계를 유지한다
- validation 결과는 rule 단위 + row reference 단위로 구조화한다
- 결과 테이블은 프론트가 직접 가공하지 않도록 분석 친화적 shape로 제공한다

---

## 9. 최종 요약

이 와이어프레임 명세는 단순 대시보드가 아니라, `입력 검증 -> 실행 -> 결과 해석 -> 공간 분석 -> 구조 분석 -> 시나리오 비교`까지 이어지는 분석 워크벤치 구현을 위한 기준 문서다.
