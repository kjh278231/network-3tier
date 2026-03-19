# Network 3-Tier Optimizer Web App 개발 기획서

## 1. 문서 목적

본 문서는 현재 Python/OR-Tools 기반 `network-3tier` 최적화 모델을 웹에서 직관적으로 확인하고 분석할 수 있는 웹 앱의 개발 방향을 정의한다.

목표는 단순히 결과를 예쁘게 보여주는 것이 아니라, 물류 네트워크 최적화 컨설턴트가 아래 질문에 빠르게 답할 수 있는 분석 도구를 만드는 것이다.

- 입력 데이터가 모델 가정과 제약에 맞는가
- 어떤 창고가 왜 선택되었는가
- 비용이 어디서 발생하는가
- coverage와 lead time은 어떤 고객/권역에서 나빠지는가
- best model과 designated model을 비교하면 어떤 trade-off가 있는가
- Mapping ID, capacity, 공급량, 운송비가 결과에 어떤 영향을 주는가

---

## 2. 현재 모델 기준 업무 해석

현재 모델은 다음 의사결정을 수행한다.

- 어떤 warehouse를 열지 결정
- 각 customer를 정확히 하나의 warehouse에 배정
- 각 plant에서 각 warehouse로 정수 물량을 배분

현재 분석자가 반드시 확인해야 하는 핵심 입력은 다음이다.

- `simulation`: warehouse 수, speed, coverage 기준
- `plant`: 공급량과 shipment qty
- `warehouse`: capacity, fixed cost, operation cost, active 여부
- `customer`: 수요, shipment qty, Mapping ID
- `plantWarehouseCost`: plant -> warehouse 비용 및 거리
- `warehouseCustomerCost`: warehouse -> customer 비용 및 거리

현재 분석자가 반드시 확인해야 하는 핵심 출력은 다음이다.

- case별 총비용, inbound/outbound, lead time, coverage, total rank
- plant -> warehouse route별 물량/비용/lead time
- warehouse별 inbound/outbound/capacity/fixed cost/operation cost
- warehouse -> customer route별 수요/비용/coverage 여부
- customer 단위 coverage 상세

즉, 웹 앱은 "최적화 실행기"이면서 동시에 "시나리오 분석 콘솔"이어야 한다.

---

## 3. 백엔드 필요 여부 판단

### 결론

백엔드는 필요하다.

### 이유

브라우저 단독 앱만으로는 아래 요구를 안정적으로 처리하기 어렵다.

- 대용량 Excel 업로드 및 정규화 파싱
- 현재 Python 기반 검증 로직 재사용
- OR-Tools 최적화 실행
- 실행 로그 저장
- 실행 결과 이력 관리
- 여러 case 결과를 서버 기준으로 재조회/비교
- 향후 사용자/프로젝트/시나리오 단위 저장

### 예외

아래와 같은 매우 제한된 범위라면 프론트엔드 전용도 가능하다.

- 이미 생성된 `output_case*.xls`와 `output_summary.xls`를 업로드해서 읽기만 하는 viewer
- 최적화 실행은 로컬 CLI에서만 하고, 웹은 리포트 탐색만 담당

하지만 사용자가 원하는 것은 "input과 output을 보면서 분석"하는 앱에 가깝고, 실제로는 실행 전 검증과 실행 후 비교가 한 흐름으로 이어져야 하므로 백엔드가 있는 구조가 맞다.

### 권장 아키텍처

- Frontend: React 기반 SPA
- Backend API: Python
- Optimizer Worker: 기존 Python 코드 재사용
- Storage: 로컬 파일 또는 DB + 객체 저장소 성격의 run artifact 저장

초기에는 단일 Python 백엔드에서 API + 실행 job + 파일 저장을 같이 처리하고, 이후 job queue를 분리하는 단계적 구조가 적절하다.

---

## 4. 제품 목표

### 4.1 1차 목표

- 입력 workbook을 업로드하고 구조화해서 확인할 수 있어야 한다
- 데이터 검증 결과를 시트/행/컬럼 수준으로 확인할 수 있어야 한다
- 최적화 실행을 웹에서 시작하고 상태를 볼 수 있어야 한다
- best model과 designated model 결과를 비교할 수 있어야 한다
- map/table/chart를 넘나들며 원인 분석이 가능해야 한다

### 4.2 비목표

- 수리모형을 브라우저에서 재구현하는 것
- 범용 GIS 플랫폼 수준의 지도 엔진 개발
- APS/ERP급 마스터데이터 관리 기능 전체 구현

---

## 5. 핵심 사용자와 사용 시나리오

### 5.1 주요 사용자

- 물류 네트워크 최적화 컨설턴트
- 공급망 기획 담당자
- 운영 리더 또는 의사결정자

### 5.2 대표 사용 시나리오

#### 시나리오 A. 신규 입력 검증

1. workbook 업로드
2. 입력 요약 확인
3. validation issue 확인
4. Mapping ID 이상, arc 누락, 총수요/총capacity 불일치 확인
5. 문제 수정 후 재업로드

#### 시나리오 B. 최적화 실행 및 결과 해석

1. 실행 조건 확인
2. best model 실행
3. selected warehouses 확인
4. 비용 구조 확인
5. coverage가 낮은 고객과 warehouse를 drill-down

#### 시나리오 C. 시나리오 비교

1. best model과 designated model 비교
2. 비용 증가 대비 lead time/coverage 개선 여부 확인
3. 특정 warehouse를 강제로 포함했을 때 trade-off 판단

#### 시나리오 D. 경영진 설명용 요약

1. 선택 창고와 고객 커버리지를 지도에서 보여줌
2. 비용 분해와 coverage 성과를 한 화면에서 설명
3. 대안 시나리오를 비교해 의사결정 근거 제시

---

## 6. 정보 구조

권장 정보 구조는 아래와 같다.

1. 프로젝트 홈
2. 업로드/실행
3. 입력 분석
4. 결과 요약
5. 네트워크 맵
6. 창고 분석
7. 고객 분석
8. Route 분석
9. 시나리오 비교
10. 모델 설명/제약 설명

이 구조는 "입력 확인 -> 실행 -> 결과 요약 -> 원인 drill-down -> 비교" 흐름을 그대로 반영한다.

---

## 7. 화면 구성 제안

## 7.1 프로젝트 홈 / Run 목록

### 목적

사용자가 어떤 workbook과 어떤 run을 보고 있는지 바로 이해하게 한다.

### 핵심 구성

- 최근 run 목록
- run status: uploaded, validated, running, completed, failed
- 입력 파일명, 실행 시각, solver, case 수
- 주요 KPI 미리보기: best cost, selected warehouse count, coverage
- 실패 run의 에러 요약

### 왜 필요한가

컨설턴트는 한 번만 실행하지 않는다. 입력 수정 후 여러 번 돌리며 비교하기 때문에 run 이력 관리가 핵심이다.

## 7.2 업로드 / 실행 화면

### 목적

입력을 올리고 실행 조건을 설정하는 통제 화면이다.

### 핵심 구성

- workbook 업로드
- 입력 파일 메타 요약
- solver 선택
- max samples 설정
- random seed 설정
- 실행 버튼
- validation 선실행 버튼
- execution log 패널

### UX 원칙

- 실행 전 validation 결과를 반드시 먼저 노출
- 실행 중에는 현재 단계 표시
- 실패 시 traceback 전체가 아니라 business-friendly 오류 요약 우선 표시

## 7.3 입력 분석 화면

### 목적

입력 구조와 품질을 "모델 관점"에서 읽게 한다.

### 화면 탭 제안

- `Simulation`
- `Plants`
- `Warehouses`
- `Customers`
- `P->W Arc`
- `W->C Arc`
- `Validation`

### 각 탭 공통 기능

- 표 형태 데이터 조회
- 컬럼별 필터/정렬
- 이상치 하이라이트
- CSV/XLS export
- row count / unique count / null count / range summary

### 꼭 필요한 입력 분석 포인트

- `simulation.Warehouse Qty`와 active warehouse 수 비교
- 총수요 vs 총공급 vs 총capacity
- Mapping ID가 걸린 customer 수
- warehouse별 capacity / fixed cost / operation cost 분포
- customer 수요 상위 목록
- arc 누락 여부
- plant/warehouse/customer 좌표 존재 여부

### 추천 시각화

- warehouse capacity histogram
- customer demand histogram
- plant supply vs total demand summary card
- Mapping ID 강제 고객 비율 donut

## 7.4 Validation 화면

### 목적

최적화 실행 가능성과 데이터 품질 이슈를 가장 빠르게 진단하게 한다.

### 핵심 구성

- Error / Warning / Info 분리
- rule별 통과 여부
- 영향받는 row 수
- 클릭 시 원본 row drill-down

### rule 표현 방식

- 규칙명
- 의미
- 실패 이유
- 영향 객체
- 수정 권장안

예시:

- 총수요가 총capacity를 초과함
- 특정 customer의 assignment arc가 없음
- Mapping ID가 inactive warehouse를 가리킴

이 화면은 단순 로그 뷰가 아니라, 모델 feasibility gate 역할을 해야 한다.

## 7.5 결과 요약 대시보드

### 목적

한 run의 전체 성능을 한눈에 보여준다.

### 핵심 KPI 카드

- Optimal Cost
- Inbound Cost
- Warehouse Cost
- Outbound Cost
- Selected Warehouse Count
- Optimal Lead Time
- Coverage Time
- Coverage Vol

### 핵심 시각화

- 비용 분해 stacked bar
- case별 Total Score 비교
- case별 Cost / Lead Time / Coverage radar
- selected warehouses 리스트

### 중요한 UX 포인트

- 숫자 카드만 있으면 부족하다
- "왜 이 값이 나왔는지"로 넘어가는 drill-down 링크가 있어야 한다

## 7.6 네트워크 맵 화면

### 목적

공간적으로 네트워크를 해석하게 한다.

### 핵심 레이어

- Plant
- Warehouse 후보
- Selected warehouse
- Customer
- Plant -> Warehouse route
- Warehouse -> Customer assignment

### 시각 표현

- plant: 큰 아이콘
- selected warehouse: 강조 색상
- 미선정 warehouse: 옅은 색상
- customer: demand 크기에 따라 점 크기 차등
- route: 물량 또는 비용에 비례한 선 굵기

### 필수 인터랙션

- warehouse 선택 시 연결 고객만 필터
- customer 선택 시 소속 warehouse와 plant 경로 동시 강조
- coverage 미달 고객만 보기
- distance / cost / do qty 기준 선 필터

### 컨설턴트 관점에서 중요한 질문

- 특정 hub가 왜 넓은 권역을 커버하는가
- coverage 실패가 특정 지리권에 몰려 있는가
- long-haul customer가 어떤 warehouse에 물려 있는가

## 7.7 네트워크 그래프 화면

### 목적

지리 좌표 기반 지도가 아니라, 네트워크 구조 자체를 노드-링크 그래프로 해석하게 한다.

### 왜 별도 화면이 필요한가

지도는 공간적 해석에 강하지만 아래 질문에는 약하다.

- 어떤 plant가 어떤 warehouse들을 얼마나 공급하는가
- 특정 warehouse가 몇 개 customer를 거느리는가
- 어떤 warehouse가 네트워크 중심 허브처럼 동작하는가
- Mapping ID 고객이 네트워크 구조상 어디에 묶여 있는가

그래프 화면은 이 구조적 질문에 답하기 위한 화면이다.

### 그래프 모델링 방식

- Node 타입 1: Plant
- Node 타입 2: Warehouse
- Node 타입 3: Customer
- Edge 타입 1: Plant -> Warehouse flow
- Edge 타입 2: Warehouse -> Customer assignment

### 시각 표현

- Plant: 가장 큰 노드, 사각형 또는 강조 아이콘
- Warehouse: 중간 크기 노드, 선택 여부에 따라 색상 차등
- Customer: 작은 노드, demand 크기에 따라 size 차등
- Edge 두께: `Do Qty` 기준
- Edge 색상: route type 기준 분리
- Node border 또는 badge: Mapping ID, coverage issue, high-cost 여부 표시

### 필수 인터랙션

- warehouse 노드 클릭 시 연결 customer/plant만 남기기
- customer 노드 클릭 시 upstream warehouse와 plant 경로 동시 강조
- edge hover 시 `Do Qty`, `Cost`, `Lead Time` tooltip
- coverage 미달 customer만 보기
- demand 상위 customer만 보기
- selected warehouse만 보기
- warehouse 중심 ego-network 보기

### 추천 레이아웃

- 기본: 계층형 좌우 레이아웃
  - Plant -> Warehouse -> Customer
- 보조: force layout
  - 복잡 연결 구조 탐색
- 보조: 선택 warehouse 중심 radial layout
  - hub 구조 설명

### 컨설턴트 관점에서 중요한 질문

- 특정 warehouse가 과도하게 많은 customer를 담당하는가
- flow가 한 warehouse에 편중되는가
- 공급 source가 사실상 단일 plant에 종속되는가
- low coverage customer가 특정 hub 주변에 집중되는가

## 7.8 창고 분석 화면

### 목적

warehouse 단위의 성능과 부담 구조를 평가한다.

### 핵심 표

- Warehouse Id
- Inbound Qty
- Outbound Qty
- Throughput Capacity Qty
- Capacity Utilization
- Fixed Cost
- Operation Cost
- Assigned Customer Count
- Coverage within target 비율

### 핵심 차트

- warehouse별 utilization bar chart
- warehouse별 총비용 waterfall
- warehouse별 담당 customer 수 bubble chart

### drill-down

- warehouse 클릭 -> 해당 warehouse의 고객 목록
- warehouse 클릭 -> inbound source plant route 확인

## 7.9 고객 분석 화면

### 목적

customer service quality를 고객 단위로 확인한다.

### 핵심 표

- Customer Id
- Assigned Warehouse
- Do Qty
- Shipment Qty
- Warehouse-Customer Lead Time
- Total Lead Time
- Coverage YN
- Route Cost
- Mapping ID 여부

### 핵심 기능

- coverage 미달 고객만 보기
- lead time 상위 worst customer 보기
- demand 상위 customer 보기
- Mapping ID customer만 보기

### 컨설턴트 가치

대부분의 의사결정 논쟁은 "왜 이 고객이 저 창고에 배정되었나"에서 발생한다. 이 화면은 설명 가능성을 높이는 핵심 화면이다.

## 7.10 Route 분석 화면

### 목적

운송 관점에서 비용과 lead time을 분해한다.

### 서브탭

- Plant -> Warehouse
- Warehouse -> Customer

### Plant -> Warehouse 탭

- route별 `Do Qty`, `Cost`, `Shipment Qty Ratio`, `Lead Time`
- 총공급량 대비 warehouse별 inbound 비중

### Warehouse -> Customer 탭

- route별 `Do Qty`, `Cost`, `Lead Time`, `One-way Time`, `Coverage YN`
- 고비용 route, 장거리 route, low-coverage route 탐색

### 필수 정렬/필터

- cost descending
- lead time descending
- do qty descending
- selected warehouse
- coverage YN

## 7.11 시나리오 비교 화면

### 목적

best model과 designated model 간 trade-off를 판단하게 한다.

### 비교 단위

- case 대 case
- best model vs 전체 sample
- warehouse set 변화 기준

### 핵심 비교 항목

- Total Cost
- Lead Time
- Coverage Time
- Coverage Vol
- Selected Warehouses
- warehouse swap 차이

### 추천 시각화

- scatter: Cost vs Coverage
- scatter: Cost vs Lead Time
- side-by-side warehouse selection diff
- KPI delta 카드

### 반드시 있어야 하는 기능

- 특정 case 두 개 선택 후 비교
- best 대비 증가/감소 수치 표시
- 어떤 warehouse가 추가/제외되었는지 강조

## 7.12 모델 설명 / Explain 화면

### 목적

결과를 보는 사람이 수리모형 배경을 이해하게 한다.

### 포함 내용

- 문제 정의
- 제약식 설명
- 비용 구조 설명
- lead time 계산식
- coverage 정의
- ranking 산식
- Mapping ID 의미

### 왜 필요한가

컨설팅 현장에서는 화면만 예쁘게 보여주는 것보다 "이 결과가 어떤 룰에서 나온 것인지" 설명하는 능력이 더 중요하다.

---

## 8. 권장 사용자 흐름

### 흐름 1. 신규 데이터 검토

`홈 -> 업로드 -> 입력 분석 -> Validation -> 실행 -> 결과 요약`

### 흐름 2. 원인 분석

`결과 요약 -> 네트워크 맵 -> 창고 분석 -> 고객 분석 -> Route 분석`

### 흐름 3. 대안 비교

`결과 요약 -> 시나리오 비교 -> warehouse diff -> 고객 영향 분석`

---

## 9. 시각화 라이브러리 권장안

### 비교 대상

- Sigma.js
- Cytoscape.js
- React Flow

### Sigma.js 평가

장점:

- 대규모 그래프를 위한 WebGL 기반 시각화에 강함
- 수천 개 노드/엣지 시각화에 적합
- graphology 기반으로 네트워크 표현이 자연스러움

한계:

- 제품형 필터 UX, 선택 상태 관리, 노드 패널 구성은 직접 구현 비중이 큼
- 계층형 업무 그래프를 "분석 툴 UX"로 만들 때 부가 개발량이 커질 수 있음

적합한 경우:

- 매우 큰 네트워크를 성능 우선으로 렌더링해야 할 때

### Cytoscape.js 평가

장점:

- 그래프 시각화와 그래프 분석 기능을 함께 제공
- selector, filtering, traversal, layout 선택지가 강함
- directed graph와 네트워크 분석 use case에 잘 맞음
- 확장성과 인터랙션 구성이 풍부함

한계:

- React 앱과 디자인 시스템에 자연스럽게 녹이려면 wrapper 설계가 필요함
- 일반적인 product UI 구성요소는 별도로 설계해야 함

적합한 경우:

- 네트워크 분석 자체가 핵심이고, 노드/엣지 중심 상호작용이 많을 때

### React Flow 평가

장점:

- React 기반 UI 통합이 쉽고 커스텀 노드 제작이 편함
- 패널, 컨트롤, 미니맵 등 앱형 UX를 빠르게 만들 수 있음
- 상태관리와 사이드 패널 연동이 자연스러움

한계:

- 본질적으로는 node-based editor 성격이 강함
- 대규모 network analysis 성능이나 graph 알고리즘 중심 도구로는 상대적으로 덜 적합함
- Plant -> Warehouse -> Customer처럼 엣지가 매우 많아지면 관리 비용이 커질 수 있음

적합한 경우:

- 편집형 플로우, 시나리오 편집기, 설명형 다이어그램에 가까운 경우

### 최종 권장

1차 권장안은 `Cytoscape.js`다.

이유:

- 현재 앱은 단순 시각화가 아니라 분석 도구다
- directed network, filtering, neighborhood 탐색, 그래프 질의가 중요하다
- warehouse/customer/route 중심 drill-down UX와 궁합이 좋다
- 지도와 별도의 "구조 분석 화면"을 만들기 가장 균형이 좋다

### 차선 권장

- 매우 큰 그래프 성능이 핵심이면 `Sigma.js`
- 향후 사용자가 시나리오를 직접 편집하는 node editor까지 가려면 `React Flow`

### 실제 구현 권고

- 지도: 별도 map 라이브러리 사용
- 그래프: Cytoscape.js 사용
- 표/필터/KPI 패널: 일반 React UI 컴포넌트로 별도 구성

즉, "그래프 엔진"과 "제품 UI"를 분리하는 편이 맞다.

---

## 10. 화면 레이아웃 가이드

### 공통 레이아웃

- 상단: 현재 프로젝트 / run / case 컨텍스트
- 좌측: 화면 전환 네비게이션
- 중앙: 핵심 차트 또는 지도
- 우측: 필터, KPI 요약, 선택 객체 상세
- 하단: 원본 데이터 테이블

### 레이아웃 원칙

- 지도와 차트는 탐색용, 하단 테이블은 검증용으로 역할을 분리한다
- 선택 상태가 화면 전체에 일관되게 전파되어야 한다
- warehouse 하나를 선택하면 맵, KPI, route 표, customer 표가 동시에 같은 컨텍스트로 바뀌어야 한다
- 데스크톱 우선으로 설계하되, 모바일은 조회 전용 수준으로 축소한다

### 가장 중요한 상세 화면 패턴

- 상단 KPI
- 좌측 필터
- 중앙 시각화
- 하단 상세 테이블

이 패턴을 결과 요약, 맵, warehouse 분석, customer 분석에 공통 적용하면 사용자가 학습 비용 없이 화면을 이동할 수 있다.

---

## 11. 기능 우선순위

### MVP

- workbook 업로드
- validation 결과 화면
- 최적화 실행
- run 목록
- 결과 요약 대시보드
- case 상세 테이블
- 기본 네트워크 맵
- best/designated 비교

### Phase 2

- 저장된 run 재사용
- 필터 상태 공유 URL
- 보고서 export
- 민감도 분석용 파라미터 복제

### Phase 3

- 협업 코멘트
- 승인 workflow
- 시나리오 템플릿
- 권역/고객군 세그먼트 분석

---

## 12. 성공 지표

### 사용자 성공 지표

- 입력 업로드 후 validation 이슈를 5분 내 식별 가능
- best model 결과에서 low coverage customer 원인을 3클릭 이내에 추적 가능
- best와 designated case의 trade-off를 10분 내 비교 가능

### 제품 성공 지표

- run 성공/실패 이력 재조회 가능
- workbook 업로드부터 결과 조회까지 end-to-end 흐름 완성
- 주요 화면에서 export 가능

### 운영 성공 지표

- 실행 실패 원인의 80% 이상이 validation 또는 run log에서 해석 가능
- 동일 입력 재실행 시 결과 재현 가능

---

## 13. 권장 기술 구조

### Frontend

- React
- TypeScript
- 데이터 테이블 라이브러리
- 지도 시각화 라이브러리
- 차트 라이브러리

### Backend

- Python API
- 기존 `loader.py`, `optimizer.py`, `ranking.py`, `output.py` 재사용
- run artifact 저장 계층

### 데이터 저장

- 초기: 파일 기반 저장 + 메타데이터 JSON
- 확장: PostgreSQL 등으로 run / case / issue 메타데이터 관리

### 작업 실행

- 초기: 동기/준동기 실행
- 확장: 비동기 job queue

---

## 14. 데이터 모델 제안

웹 앱 내부에서는 최소한 아래 개체를 가져야 한다.

- Project
- Run
- InputWorkbook
- ValidationIssue
- Case
- WarehouseAssignmentSummary
- PlantWarehouseRoute
- WarehouseCustomerRoute
- CoverageDetail

핵심은 "run 중심" 데이터 모델이다. 입력과 출력이 모두 run에 묶여야 비교와 재현이 가능하다.

---

## 15. API 초안

### 입력/실행

- `POST /runs/upload`
- `POST /runs/{runId}/validate`
- `POST /runs/{runId}/execute`
- `GET /runs`
- `GET /runs/{runId}`

### 입력 조회

- `GET /runs/{runId}/input/simulation`
- `GET /runs/{runId}/input/plants`
- `GET /runs/{runId}/input/warehouses`
- `GET /runs/{runId}/input/customers`
- `GET /runs/{runId}/input/plant-warehouse-arcs`
- `GET /runs/{runId}/input/warehouse-customer-arcs`
- `GET /runs/{runId}/validation-issues`

### 결과 조회

- `GET /runs/{runId}/summary`
- `GET /runs/{runId}/cases`
- `GET /runs/{runId}/cases/{caseName}/warehouse-summary`
- `GET /runs/{runId}/cases/{caseName}/plant-warehouse-routes`
- `GET /runs/{runId}/cases/{caseName}/warehouse-customer-routes`
- `GET /runs/{runId}/cases/{caseName}/coverage-details`

---

## 16. UX 설계 원칙

### 원칙 1. 지도보다 표가 먼저다

네트워크 문제는 지도가 직관적이지만, 실제 분석은 표와 필터가 더 중요하다. 지도는 탐색용, 표는 검증용으로 역할을 분리해야 한다.

### 원칙 2. KPI에서 원인으로 2클릭 안에 가야 한다

예를 들어 Coverage Time이 낮으면 바로 low-coverage customer 목록으로 이동되어야 한다.

### 원칙 3. 모델 용어와 업무 용어를 함께 보여준다

예:

- `Do Qty (수요량)`
- `Coverage Time (%) (시간 기준 커버율)`

### 원칙 4. 실패도 자산으로 저장한다

infeasible run이나 validation fail도 기록해야 한다. 컨설턴트에게는 "왜 안 풀렸는가"도 중요한 분석 결과다.

### 원칙 5. 비교가 기본 모드여야 한다

절대값보다 best 대비 차이를 더 빠르게 읽을 수 있어야 한다.

---

## 17. 화면별 필수 지표 정리

### 홈

- run 수
- 최근 성공/실패 실행
- 최신 best cost

### 입력 분석

- total demand
- total supply
- total throughput capacity
- active warehouse count
- mapped customer count

### 결과 요약

- total cost
- inbound/outbound cost
- lead time
- coverage time / vol
- selected warehouse count

### 창고 분석

- warehouse utilization
- 담당 customer 수
- warehouse별 비용

### 고객 분석

- low coverage customer 수
- worst lead time customer
- high cost customer route

---

## 18. 개발 순서 제안

### Step 1. 결과 viewer부터 구축

- 기존 output workbook / run summary를 읽어 웹에 표시
- 결과 요약, warehouse/customer/route 화면부터 구현
- 지도와 그래프는 이 단계에서 read-only로 함께 붙일 수 있음

장점:

- 현재 모델 변경 없이 빠르게 가치 확인 가능
- 화면 구조 검증이 쉽다

### Step 2. 입력 분석과 validation 연결

- workbook 업로드
- 시트별 데이터 조회
- validation issue 시각화

### Step 3. 웹에서 실행

- backend에서 optimizer job 실행
- run 상태 표시
- 결과 저장 및 재조회

이 순서가 가장 현실적이다. 처음부터 완전한 end-to-end 앱을 만들면 실패 가능성이 높다.

---

## 19. 주요 리스크와 대응

### 리스크 1. 대용량 엑셀 처리

대응:

- 업로드 직후 서버에서 정규화
- 원본 파일과 파싱 결과를 분리 저장

### 리스크 2. 지도 성능 저하

대응:

- customer 점 clustering
- route 선 수 제한
- 상위 N개만 우선 렌더링

### 리스크 3. 모델 설명 부족

대응:

- Explain 화면 별도 제공
- KPI 카드마다 계산식 tooltip 제공

### 리스크 4. 사용자가 결과만 보고 입력 이상을 놓침

대응:

- validation 결과를 실행 화면 상단에 고정
- critical issue가 있으면 실행 차단

### 리스크 5. 그래프 시각화 과밀

대응:

- 기본 필터를 둬서 전체 customer를 한 번에 다 그리지 않음
- warehouse 중심 ego-network, demand 상위 N, low coverage만 보기 등을 기본 제공
- 그래프는 탐색용, 전체 정합성 검증은 테이블에서 수행

---

## 20. 최종 권고안

가장 적절한 제품 정의는 아래와 같다.

`웹 기반 물류 네트워크 최적화 분석 워크벤치`

이 앱은 단순 대시보드가 아니라 아래 4가지가 결합된 형태여야 한다.

- 입력 데이터 검증 도구
- 최적화 실행 도구
- 네트워크 결과 분석 도구
- 시나리오 비교 도구

즉, 최적화 컨설턴트 입장에서는 "한 번 보고 끝나는 리포트 화면"보다 "지도와 그래프, 표를 오가며 질문을 던지고 원인을 따라가며 설명할 수 있는 분석 콘솔"이 되어야 한다.

---

## 21. 자체 리뷰 기록

본 기획서는 아래 리뷰를 거쳐 수정했다.

### 리뷰 1. 백엔드 필요 여부 재검토

- 초안에서는 viewer 중심으로 볼 여지가 있었음
- 최적화 실행, validation, run 이력 관리를 고려해 backend 필요로 확정

### 리뷰 2. 화면 구조 과다 단순화 문제 수정

- 처음에는 업로드/결과/비교 정도의 3개 화면으로 축약 가능해 보였음
- 실제 컨설턴트 분석 흐름에는 validation, customer drill-down, route 분석이 필수라 세분화함

### 리뷰 3. 지도 중심 설계 편향 수정

- 네트워크 문제라 지도에 치우치기 쉬움
- 실제 원인 분석은 표 기반이 핵심이므로 테이블/필터를 우선 구조로 재정렬함

### 리뷰 4. 입력 분석 기능 부족 보완

- output 분석만으로는 실행 전 품질 문제를 못 잡음
- input explorer와 validation 화면을 독립 모듈로 강화함

### 리뷰 5. 비교 기능 부족 보완

- best model만 보여주면 designated model의 의미가 약해짐
- case diff, warehouse swap, KPI delta 중심 비교 기능을 추가함

### 리뷰 6. 개발 난이도 현실화

- 처음부터 풀스코프 제품으로 잡으면 개발 리스크가 큼
- 결과 viewer -> 입력 검증 -> 웹 실행 순서의 단계적 개발 전략으로 수정함

### 리뷰 7. 설명 가능성 강화

- 컨설팅 현장에서는 결과보다 설명이 중요함
- Explain 화면과 계산식 tooltip, 실패 run 저장 원칙을 추가함

### 리뷰 8. 화면 배치 기준 보강

- 처음 문서에는 화면 목록은 있었지만 공통 레이아웃 기준이 약했음
- KPI, 필터, 시각화, 테이블의 기본 배치 원칙을 추가함

### 리뷰 9. 성공 기준 명확화

- 문서가 기능 나열 중심이라 완료 정의가 모호했음
- 사용자 성공 지표와 운영 성공 지표를 추가해 개발 완료 기준을 보강함

### 리뷰 10. 지도 외 구조 시각화 부족 보완

- 지도는 공간 해석에는 강하지만 네트워크 구조 분석에는 부족했음
- 별도의 그래프 화면과 라이브러리 권장안을 추가함

---

## 22. 최종 제안 한 줄 요약

백엔드가 포함된 웹 분석 워크벤치를 만들고, 화면은 `입력 검증 -> 실행 -> 결과 요약 -> 지도/그래프/표 drill-down -> 시나리오 비교` 흐름으로 구성하는 것이 가장 적절하다.
