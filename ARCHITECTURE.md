# Network 3-Tier Optimizer — Architecture

## 개요

Plant-Warehouse-Customer 3단계 공급망 네트워크에서 물류 비용을 최소화하는 Mixed-Integer Linear Programming(MILP) 최적화 시스템. OR-Tools(Google)를 MILP 엔진으로 사용하며, CLI 솔버 · FastAPI 웹 API · AI 분석 에이전트 세 가지 실행 모드를 제공한다.

```
network_optimizer.py          ← CLI 진입점
src/network3tier/             ← 솔버 코어
  ├── domain.py               ← 도메인 데이터 구조
  ├── loader.py               ← 입력 로딩 & 검증
  ├── optimizer.py            ← OR-Tools MILP 모델
  ├── ranking.py              ← 다기준 점수화 & 순위
  ├── sampling.py             ← 1-swap 이웃 탐색
  ├── output.py               ← Excel 결과 출력
  ├── cli.py                  ← CLI 오케스트레이션
  └── webapi/
      ├── app.py              ← FastAPI 라우터
      ├── service.py          ← 비즈니스 로직
      ├── serializers.py      ← DataFrame ↔ JSON 변환
      └── storage.py          ← 파일 시스템 추상화
analysis_agent/               ← AI 분석 에이전트 (솔버 성공 시)
  ├── main.py                 ← 에이전트 CLI 진입점
  ├── data_loader.py          ← 솔버 결과 로딩 & 정규화
  ├── tools.py                ← LangChain 분석 툴 10종
  ├── agent.py                ← LangGraph ReAct 에이전트
  └── prompt.py               ← LLM 시스템 프롬프트
infeasibility_agent/          ← AI 불가능성 진단 에이전트 (솔버 실패 시)
  ├── main.py                 ← 진단 에이전트 CLI 진입점
  ├── data_loader.py          ← 실패 런 input.json 로딩
  ├── tools.py                ← LangChain 진단·실험 툴 10종
  ├── agent.py                ← LangGraph ReAct 에이전트
  └── prompt.py               ← LLM 시스템 프롬프트
```

---

## 솔버 (`src/network3tier/`)

### domain.py — 도메인 데이터 구조

최적화 입력·출력을 표현하는 dataclass 정의.

| 클래스 | 역할 |
|--------|------|
| `SimulationConfig` (frozen) | 시뮬레이션 파라미터: `simulation_name`, `structure`, `warehouse_qty`, `speed_kmh`, `coverage_hours` |
| `NetworkData` | 전체 입력 문제: `simulation`, `plants`/`warehouses`/`customers` (DataFrame), 비용 아크 DataFrame |
| `CaseResult` | 단일 케이스 솔루션: 선택된 창고 목록, 경로별 흐름 DataFrame, 커버리지·비용 요약 |

모든 하위 모듈(loader, optimizer, output, cli)이 공유하는 단일 진실 소스(SSoT).

---

### loader.py — 입력 로딩 & 검증

Excel 워크북 또는 JSON 페이로드에서 네트워크 데이터를 로드하고 유효성을 검증한다.

**주요 함수**

| 함수 | 설명 |
|------|------|
| `load_network_data(path)` | Excel 8-시트 워크북 로드 (simulation, plant, warehouse, customer, 비용 아크) |
| `load_network_data_from_payload(payload)` | camelCase dict → NetworkData |
| `load_network_data_from_json(path)` | JSON 파일 경로 → NetworkData (payload 로드 후 위임) |
| `validate_network_data(data)` | 공급·수요 균형, 정수 수량, 아크 완결성, 고객 매핑 유효성, 커버리지 가능성 검사 |
| `get_customer_mapping_requirements(data)` | 고정 매핑(Mapping ID) 고객 → 창고 반환 |
| `ensure_default_inventory_column(df)` | `Default Inventory Qty` 열 없을 시 0으로 초기화 |

**예외**: `DataValidationError` — 검증 실패 시 상세 메시지와 함께 발생.

**Excel 시트 규칙**: 원본 입력은 row 4부터, 출력 XLS(`output_case*.xls`)는 row 0부터 데이터 시작 (`header=0`, xlrd 엔진).

---

### optimizer.py — MILP 모델 & 솔버

OR-Tools CP-SAT/SCIP로 시설 입지·할당·흐름을 동시에 최적화한다.

**결정 변수**

| 변수 | 타입 | 의미 |
|------|------|------|
| `y[w]` | Binary | 창고 w 개방 여부 |
| `x[(w,c)]` | Binary | 고객 c를 창고 w에 배정 |
| `f[(p,w)]` | Integer | 공장 p → 창고 w 출하량 |

**제약 조건**

- 각 고객은 정확히 하나의 창고에 배정
- 창고 처리량 ≤ 입고량 + 기본 재고 (용량 상한)
- 공장별 공급 상한
- 총 흐름 = 총 공급량
- 개방 창고 수 = `simulation.warehouse_qty` (고정)
- 고정 매핑(Mapping ID) 창고는 강제 개방
- 지정 케이스(designated)는 특정 창고 세트 강제 개방

**목적 함수**: 총 비용 = Inbound(공장→창고 운임) + Warehouse(고정비 + 운영비×출고량) + Outbound(창고→고객 운임) 최소화

**주요 함수**

| 함수 | 설명 |
|------|------|
| `solve_case(data, solver_name, case_name, case_type, forced_open_warehouses)` | MILP 풀고 CaseResult 반환 |
| `build_and_solve(data, solver_name, overrides)` | `SolveOverrides` 적용 후 MILP 실행, `(is_feasible: bool, status: str)` 반환 — 불가능성 진단용 |
| `configure_solver_threads()` | 가용 CPU 코어 수만큼 스레드 자동 설정 |

**`SolveOverrides` 데이터클래스** — `build_and_solve`에 전달해 NetworkData 복사본을 수정:

| 필드 | 효과 |
|------|------|
| `remove_capacity_upper_bound` | 모든 창고 용량을 총 수요 이상으로 설정 (용량 제약 무력화) |
| `supply_multiplier` | 공장 공급량에 배수 적용 (예: 1e6으로 공급 무제한 모사) |
| `remove_mapping_constraints` | `Mapping ID` 컬럼을 NA로 대체해 강제 배정 제거 |
| `warehouse_qty_override` | `simulation.warehouse_qty` 덮어쓰기 |
| `exclude_warehouse_ids` | 지정 창고를 데이터에서 제거 + `warehouse_qty` 자동 감소 |

지원 솔버: **SCIP** (기본, 성능 우수), **CBC** (대안).

---

### ranking.py — 다기준 점수화 & 순위

모든 케이스를 비용·리드타임·커버리지 기준으로 정규화 점수로 평가한다.

**점수 공식**

```
Cost Score       = best_cost / case_cost
Lead Time Score  = best_lead_time / case_lead_time
Coverage Score   = (Coverage_Time_Score + Coverage_Vol_Score) / 2
Total Score      = (0.9 × Cost + 0.1 × LeadTime + 0.1 × Coverage) / 1.1
```

최적값이 1.0, 낮을수록 열등. 동점 시 비용 → 리드타임 → 커버리지 순으로 타이브레이크.

**주요 함수**: `build_summary_workbook(cases)` — 전체 케이스 요약 DataFrame 반환.

---

### sampling.py — 1-Swap 이웃 탐색

최적 케이스의 창고 집합에서 창고 하나를 교체하는 인접 해를 생성한다.

**동작**: 비잠금 창고(non-locked) 중 하나를 제거하고 미선택 창고 중 하나를 추가 → 셔플 후 `max_samples`개 반환.

잠금 창고(Mapping ID 제약)는 절대 교체 대상에서 제외.

---

### output.py — Excel 결과 출력

xlwt로 케이스 결과를 `output_case{N}.xls` (5개 시트)와 `output_summary.xls`로 내보낸다.

시트 구성: `summary`, `plantWarehouseRoute`, `warehouse`, `warehouseCustomerRoute`, `coverageDetail`.

---

### cli.py — CLI 오케스트레이션

**실행 인수**

| 인수 | 기본값 | 설명 |
|------|--------|------|
| `--input` | `TRNS_DOWNLOAD_*.xls` | 입력 파일 (XLS 또는 JSON) |
| `--solver` | `SCIP` | SCIP 또는 CBC |
| `--max-samples` | `10` | 지정 케이스 최대 수 |
| `--random-seed` | `42` | 샘플링 시드 |

**워크플로**

```
입력 로드 & 검증 → best_model 솔브 → 이웃 창고 세트 생성
→ designated 케이스 솔브(×max_samples) → 순위 산정
→ Excel 출력 → run_summary.json 저장
```

**CLI 출력 구조**

```
output/<YYYYMMDDHHMMSS>/
├── input.json            # 정규화된 입력 페이로드
├── output_summary.xls    # 전체 케이스 순위
├── output_case1.xls      # best_model 상세
├── output_case2.xls      # sampled_case_1 상세
├── ...
├── run_summary.json      # 실행 메타데이터
└── run.log               # 실행 로그
```

---

## 웹 API (`src/network3tier/webapi/`)

### app.py — FastAPI 라우터

**주요 엔드포인트**

| Method | Path | 설명 |
|--------|------|------|
| POST | `/runs/upload` | 파일 업로드 & 런 생성 |
| POST | `/runs/{run_id}/validate` | 입력 데이터 검증 |
| POST | `/runs/{run_id}/execute` | 최적화 실행 (비동기) |
| GET | `/runs/{run_id}/summary` | 전체 케이스 순위 JSON |
| GET | `/runs/{run_id}/cases` | 케이스 목록 |
| GET | `/runs/{run_id}/cases/{case_name}/*` | 케이스 상세 (warehouse-summary, routes, coverage) |
| GET | `/runs/{run_id}/events` | 실행 로그 스트림 (JSONL) |

CORS: 전체 오리진 허용.

---

### service.py — 비즈니스 로직

런 생명주기와 솔버 실행을 조율한다.

**런 상태 머신**

```
uploaded → validating → ready → running → completed
                            ↓
                     validation_failed / failed
```

**웹 런 출력 구조**

```
web_runs/<run_id>/
├── meta.json             # 런 메타데이터, 솔버 파라미터, 상태
├── <업로드 파일명>        # 원본 Excel
├── input.json            # 정규화된 입력 페이로드
├── validation.json       # 검증 결과
├── summary.json          # 전체 케이스 순위 (camelCase)
├── cases.json            # 케이스 인덱스
├── cases/
│   ├── best_model.json
│   └── sampled_case_N.json
└── events.jsonl          # 실행 이벤트 로그
```

---

### serializers.py — DataFrame ↔ JSON 변환

내부 DataFrame 컬럼명(snake_case / 공백 포함)과 API JSON 키(camelCase) 간 변환을 담당한다.

| 방향 | 예시 |
|------|------|
| DataFrame → JSON | `Warehouse ID` → `warehouseId` |
| DataFrame → JSON | `Do Qty` → `doQty` |
| DataFrame → JSON | `Optimal Cost` → `optimalCost` |

**주요 함수**: `build_input_payload()`, `build_case_payload()`, `case_summary_row()`.

---

### storage.py — 파일 시스템 추상화

`web_runs/` 디렉터리 내 파일 I/O를 캡슐화한다. 런 ID 생성 (`run_<YYYYMMDDHHMMSS>`, 충돌 시 `_N` suffix), JSON 저장·로드, JSONL 이벤트 로그 추가·조회를 제공한다.

---

## AI 분석 에이전트 (`analysis_agent/`)

### data_loader.py — 솔버 결과 로딩

CLI 출력(`output/<timestamp>/`)과 웹 런 출력(`web_runs/<run_id>/`) 양쪽을 동일한 인터페이스로 로드한다.

**포맷 감지**

| 조건 | 포맷 |
|------|------|
| `run_summary.json` 존재 | cli |
| `meta.json` + `input.json` 존재 | web_run |

**데이터 구조**

- `CaseData`: 단일 케이스 — `case_name`, `summary`(dict), `warehouse_summary`, 경로·커버리지 데이터(list of dict)
- `RunData`: 전체 런 컨텍스트 — `format`, `simulation`, `plants`/`warehouses`/`customers`(list of dict), `summary_rows`, `cases`, `run_meta`

---

### tools.py — LangChain 분석 툴 10종

`make_tools(run_data)` 클로저로 생성. 모든 툴은 JSON 문자열을 반환한다.

| 번호 | 툴 이름 | 반환 내용 |
|------|---------|----------|
| 1 | `get_network_overview` | 시뮬레이션 설정, 창고 후보 전체, 공장, 공급·수요 균형 |
| 2 | `get_cross_case_ranking` | 전체 케이스 순위 테이블 |
| 3 | `get_cost_breakdown` | 케이스별 비용 구성 (inbound/warehouse/outbound, %) |
| 4 | `get_warehouse_utilization` | 창고별 입출고량, 가동률, 비용 |
| 5 | `get_coverage_stats` | 창고별 고객·물량 커버리지 % (위치 포함) |
| 6 | `get_lead_time_distribution` | 리드타임 분포 통계 (mean, p50, p90, p95) |
| 7 | `get_route_efficiency` | 창고별 단위당 비용, 평균 거리, 경로 수 |
| 8 | `get_customer_demand_concentration` | 수요 집중도: 상위 N개 고객, 80% 임계 고객 수 |
| 9 | `get_plant_warehouse_flow` | 공장→창고 인바운드 흐름 상세 |
| 10 | `get_warehouse_selection_diff` | 1-swap 민감도: 창고 교체 시 비용 변동 |

---

### agent.py — LangGraph ReAct 에이전트

```python
def run_analysis(run_data: RunData) -> str:
    tools = make_tools(run_data)
    model = ChatLiteLLM(model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"))
    app = create_react_agent(model=model, tools=tools, prompt=SYSTEM_PROMPT)
    result = app.invoke({"messages": [HumanMessage(content=user_prompt)]},
                        {"recursion_limit": 50})
    # → 마지막 AIMessage에서 마크다운 보고서 추출
```

LangGraph `create_react_agent`(ReAct 패턴)를 사용. 최대 50회 반복으로 툴 호출 → 결과 처리 → 보고서 작성.

LiteLLM을 통해 모델·API 키를 `.env`에서 주입하므로 Claude / OpenAI / 기타 모델 교체 가능.

---

### prompt.py — LLM 시스템 프롬프트

에이전트의 분석 행동을 정의한다.

- **데이터 스키마**: 비용 구성 요소, 점수 공식, 커버리지 정의, 케이스 타입
- **툴 호출 순서**: 10단계 순서 지정 (overview → ranking → cost → utilization → coverage → lead time → efficiency → concentration → flow → diff)
- **보고서 요구사항**:
  - **전체 한국어** 작성 (ID, 고유명사, 숫자만 영어 유지)
  - 10개 섹션 구조 지정
  - **테이블 완전성**: "..." 축약 절대 금지, 모든 행 표시

---

### main.py — 에이전트 CLI 진입점

```bash
cd analysis_agent
python main.py ../output/<YYYYMMDDHHMMSS>
# → analysis_agent/report_<timestamp>.md 생성
```

옵션 `--output <path>`으로 출력 파일 경로 지정 가능.

---

## AI 불가능성 진단 에이전트 (`infeasibility_agent/`)

솔버가 INFEASIBLE을 반환한 런의 `input.json`을 읽어 원인을 체계적으로 진단한다. `analysis_agent/`와 동일한 LangGraph ReAct 구조를 사용하며, 솔버 결과 대신 원시 입력 데이터를 분석 대상으로 삼는다.

### data_loader.py — 실패 런 로딩

`load_failed_run(run_dir) → FailedRunData`

| 필드 | 내용 |
|------|------|
| `network_data` | `load_network_data_from_payload()`로 로드한 `NetworkData` |
| `error_message` | `meta.json["errorSummary"]` 또는 `error.txt` |
| `solver` | 실패한 런에서 사용한 솔버 이름 (기본: SCIP) |

### tools.py — 진단·실험 툴 10종

`make_tools(run_data)` 클로저로 생성. 1–5번은 재최적화 없이 입력 데이터만 분석하고, 6–10번은 `build_and_solve()`를 호출해 제약을 하나씩 완화하며 실험한다.

| 번호 | 툴 이름 | 설명 |
|------|---------|------|
| 1 | `check_aggregate_balance` | 총 공급·수요·용량 집계 및 부족분 |
| 2 | `check_customer_arc_eligibility` | 배정 가능한 창고 아크가 없는 고객 탐지 |
| 3 | `check_mapping_constraints` | Mapping ID 고객의 창고 존재·아크 유효성 |
| 4 | `check_mapped_warehouse_capacity` | 강제 배정 창고별 매핑 수요 합산 vs 용량 |
| 5 | `check_warehouse_count_feasibility` | `warehouse_qty` vs 활성 창고 수 vs 매핑 최소 수 |
| 6 | `experiment_relax_capacity` | 용량 제약 제거 후 재최적화 |
| 7 | `experiment_relax_supply` | 공급량 1e6배 후 재최적화 |
| 8 | `experiment_remove_mapping` | Mapping ID 제약 전체 제거 후 재최적화 |
| 9 | `experiment_warehouse_count_sweep` | `warehouse_qty` 1..N 순차 스윕, 최소 가능 수 탐색 |
| 10 | `experiment_per_warehouse_exclusion` | 강제 창고 하나씩 제외하며 재최적화 |

### agent.py / prompt.py

`run_diagnosis(run_data: FailedRunData) -> str` — `recursion_limit=60`. 프롬프트는 10단계 순서 호출과 9개 섹션 한국어 보고서를 지정한다.

### main.py — 진단 에이전트 CLI 진입점

```bash
cd infeasibility_agent
python main.py ../web_runs/<run_id> [--output report.md]
# → infeasibility_agent/diagnosis_<timestamp>.md 생성
```

---

## 전체 데이터 플로우

### CLI 솔버 경로

```
network_optimizer.py
└── cli.main()
    ├── loader.load_network_data() → NetworkData
    ├── loader.validate_network_data()
    ├── serializers.build_input_payload() → input.json 저장
    ├── optimizer.solve_case("best_model") → CaseResult
    ├── sampling.sample_neighboring_warehouse_sets()
    ├── optimizer.solve_case("sampled_case_N") × max_samples
    ├── ranking.build_summary_workbook() → 점수·순위
    └── output.write_case_output() × (1 + max_samples) → .xls 파일
```

### 웹 API 경로

```
POST /runs/upload → service.create_run() → meta.json
POST /runs/{id}/validate → service.validate_run() → input.json, validation.json
POST /runs/{id}/execute → service.execute_run() [async]
    ├── optimizer.solve_case() × (1 + max_samples)
    ├── ranking.build_summary_workbook()
    ├── serializers.build_case_payload()
    └── storage.save_json() → summary.json, cases/*.json, events.jsonl
GET  /runs/{id}/... → storage.load_json()
```

### AI 분석 에이전트 경로

```
analysis_agent/main.py
└── data_loader.load_run(run_dir)   # cli/web_run 자동 감지
    └── agent.run_analysis(run_data)
        ├── tools.make_tools(run_data) → 10개 LangChain 툴
        ├── ChatLiteLLM("claude-sonnet-4-6")
        └── create_react_agent → ReAct 루프(최대 50회)
            [툴 호출 → JSON 결과 → 분석 → 반복]
            └── 한국어 마크다운 보고서 → report_<timestamp>.md
```

### AI 불가능성 진단 에이전트 경로

```
infeasibility_agent/main.py
└── data_loader.load_failed_run(run_dir)  # input.json 로드
    └── agent.run_diagnosis(run_data)
        ├── tools.make_tools(run_data) → 10개 진단·실험 툴
        │   ├── 진단 툴(1-5): 입력 데이터 분석만 수행
        │   └── 실험 툴(6-10): optimizer.build_and_solve() 호출
        │       └── _apply_overrides(data, SolveOverrides) → 복사본 수정
        ├── ChatLiteLLM("claude-sonnet-4-6")
        └── create_react_agent → ReAct 루프(최대 60회)
            [툴 호출 → JSON 결과 → 분석 → 반복]
            └── 한국어 진단 보고서 → diagnosis_<timestamp>.md
```

---

## 주요 설계 원칙

1. **관심사 분리**: domain(데이터) · loader(I/O) · optimizer(솔버) · ranking(후처리) · serializers(포맷 변환) · storage(영속성) 각각 독립
2. **다형 입력 지원**: Excel XLS / JSON 두 형식 모두 동일 파이프라인으로 처리
3. **재현성**: 결정론적 솔버 + 시드 기반 샘플링
4. **민감도 분석**: 1-swap 이웃 탐색으로 창고 교체 비용 영향 정량화
5. **LLM 에이전트**: 구조화된 툴(JSON 반환)로 LLM이 정확한 수치 기반 분석 수행
6. **멀티 프로바이더 LLM**: LiteLLM 레이어로 Claude / OpenAI 등 모델 교체를 `.env`만 수정으로 처리

---

## 주요 의존성

| 분류 | 패키지 |
|------|--------|
| MILP 솔버 | `ortools` |
| 데이터 처리 | `pandas`, `numpy` |
| Excel I/O | `xlrd`, `xlwt`, `openpyxl` |
| 웹 프레임워크 | `fastapi`, `uvicorn` |
| LLM 오케스트레이션 | `langgraph`, `langchain-litellm`, `langchain-core` |
| LLM 추상화 | `litellm` |
| 환경 설정 | `python-dotenv` |
