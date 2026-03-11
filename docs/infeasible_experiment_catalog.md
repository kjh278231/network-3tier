# Infeasible Experiment Catalog

이 문서는 `best_model`이 solver 실행 후 infeasible일 때,
후속 LLM/IR 기반 서브모델이 어떤 실험을 우선 시도할 수 있는지 정리한 카탈로그다.

목적은 두 가지다.

- infeasible 원인을 더 빠르게 분리 진단
- 실행형 IR 기반 모델 빌더가 어떤 서브모델 조작을 지원해야 하는지 기준 제공

Precheck fail-fast 케이스는 여기의 실험 대상으로 간주하지 않는다.
그 경우는 deterministic하게 불가능이 증명된 상태이므로 LLM infeasible 분석기를 시작하지 않는다.

## 공통 원칙

- 실험은 원 문제를 “해결”하는 것이 아니라 infeasibility 원인을 분해하는 진단용이다.
- 각 실험은 원 모델 대비 어떤 제약/목적을 바꾸는지 명확해야 한다.
- 하나의 실험은 한 가지 가설만 검증하도록 유지한다.

## 후보군

### 1. Relax warehouse count

- Purpose: `simulation.Warehouse Qty`가 너무 작아서 infeasible인지 확인
- Builder support: 가능
- Current-stage method: baseline EXIR에서 `warehouse_count_exact` RHS를 바꾸거나 대체 EXIR를 사용
- Trigger:
  - `top_k_capacity_shortage`
  - `mapped_warehouse_count_exceeds_k`
- Model change:
  - `sum_w y[w] = K` 를 `sum_w y[w] <= K'` 또는 `= K+1, K+2...`로 변경
- Expected insight:
  - warehouse 수 제약이 병목인지 여부

### 2. Relax mapping-id hard assignment

- Purpose: `Mapping ID` 고정 배정이 infeasibility의 직접 원인인지 확인
- Builder support: 가능
- Current-stage method: mapping assignment/open fixing constraint를 비활성화한 대체 EXIR 사용
- Trigger:
  - `mapped_customer_missing_required_arc`
  - `mapped_warehouse_capacity_shortage`
- Model change:
  - `x[map[c], c] = 1` 제거
  - mapped warehouse open fixing 제거 또는 soft penalty화
- Expected insight:
  - hard mapping이 문제인지, 네트워크 전체 capacity/arc가 문제인지 구분

### 3. Allow split customer assignment

- Purpose: single-sourcing이 infeasibility를 유발하는지 확인
- Builder support: 가능하나 추가 EXIR 필요
- Current-stage method: `x[w,c]`를 대체하는 연속/정수 flow 변수와 대응 제약을 가진 별도 EXIR 작성
- Trigger:
  - 고객별 단일 warehouse 할당이 강한 의심일 때
- Model change:
  - binary `x[w,c]`를 flow `g[w,c] >= 0`로 치환
  - `sum_w g[w,c] = d[c]`
- Expected insight:
  - single-sourcing 완화만으로 feasible해지는지 확인

### 4. Allow unmet demand with penalty

- Purpose: 정확히 어떤 customer demand가 충족 불가능한지 확인
- Builder support: 가능하나 추가 EXIR 필요
- Current-stage method: slack 변수/penalty objective term이 포함된 별도 EXIR 작성
- Trigger:
  - 총수요 부족
  - 특정 coverage/mapping 영역 부족
- Model change:
  - slack `u[c] >= 0` 추가
  - `sum_w assigned_to_c + u[c] = d[c]`
  - objective에 큰 penalty 추가
- Expected insight:
  - 어떤 customer 또는 지역 demand가 미충족되는지

### 5. Allow warehouse overflow with penalty

- Purpose: warehouse capacity가 병목인지 정량적으로 확인
- Builder support: 가능하나 추가 EXIR 필요
- Current-stage method: overflow 변수/penalty objective term이 포함된 별도 EXIR 작성
- Trigger:
  - `top_k_capacity_shortage`
  - `mapped_warehouse_capacity_shortage`
- Model change:
  - overflow `o[w] >= 0` 추가
  - inbound[w] <= cap[w] + o[w]`
  - objective에 큰 penalty 추가
- Expected insight:
  - capacity를 얼마나 초과해야 feasible한지

### 6. Drop warehouse must-serve constraint

- Purpose: “열린 창고는 최소 1개 customer 필요” 제약이 영향을 주는지 확인
- Builder support: 가능
- Current-stage method: 해당 constraint를 제거한 대체 EXIR 사용
- Trigger:
  - mandatory warehouse가 많고 일부가 실제로는 비어 있어야 feasible해 보일 때
- Model change:
  - `sum_c x[w,c] >= y[w]` 제거
- Expected insight:
  - mandatory warehouse 고정과 non-empty 제약의 충돌 여부

### 7. Freeze warehouse set and test assignment-only feasibility

- Purpose: 선택된 warehouse 집합이 주어졌을 때 downstream assignment가 가능한지 분리 확인
- Builder support: 가능
- Current-stage method: warehouse 집합을 외생 입력으로 두는 EXIR 또는 지정 warehouse용 EXIR 사용
- Trigger:
  - designated set 또는 mapped mandatory set 검증
- Model change:
  - `y[w]` 고정
  - `f[p,w]` 제거
  - assignment/capacity/mapping만 유지
- Expected insight:
  - 문제 원인이 downstream assignment인지 upstream supply인지 분리

### 8. Freeze assignment and test upstream flow feasibility

- Purpose: assignment는 가능하지만 plant->warehouse 공급 분배가 불가능한지 확인
- Builder support: 가능
- Current-stage method: assignment를 외생 입력 파라미터로 고정한 별도 EXIR 작성
- Trigger:
  - assignment 후보를 이미 확보한 경우
- Model change:
  - `x[w,c]`를 고정 입력으로 두고 `f[p,w]`만 최적화
- Expected insight:
  - upstream supply/arc 부족이 원인인지 확인

### 9. Drop fixed cost and test pure feasibility

- Purpose: 비용 항은 무시하고 제약만 놓고 feasible set이 존재하는지 확인
- Builder support: 가능
- Current-stage method: objective를 0 또는 단순 slack-minimization 형태로 바꾼 대체 EXIR 사용
- Trigger:
  - infeasible 원인 분석의 기본 1차 진단
- Model change:
  - objective를 0 또는 단순 feasibility objective로 대체
- Expected insight:
  - 순수 제약 infeasibility인지, solver/목적식 영향인지 분리

### 10. Restrict to mapped mandatory subset

- Purpose: mandatory warehouse/customer 부분문제만 떼어 feasibility를 확인
- Builder support: 가능
- Current-stage method: subset filter가 적용된 별도 EXIR 또는 외부 입력 기반 set filtering 사용
- Trigger:
  - Mapping ID 관련 이슈
- Model change:
  - mapped customer와 mapped warehouse만 남긴 서브모델 구성
- Expected insight:
  - 문제의 핵심이 mapping subset 내부에 있는지 확인

## 실행형 IR 빌더에 필요한 지원

후속 `build_model_from_ir()`는 최소한 아래 조작을 서브모델 실험 단위로 지원해야 한다.

- constraint enable/disable
- equality/inequality RHS 교체
- hard constraint를 penalty slack 포함 제약으로 대체
- variable type 변경
- variable fixing
- subset filtering for sets/arcs
- objective replacement or penalty term injection

## IR 빌더 외 별도 구현으로 가능한 것

아래는 현재 단계에서 구현하지 않지만, 별도 구현으로 가능하다.

- LLM이 solver log, precheck issue, EXIR 차이를 함께 읽고 자동으로 실험 우선순위를 제안
  - 방법: `engine_infeasible_analysis_context.json`과 candidate catalog를 입력으로 프롬프트 체인 구성
- EXIR를 자동 변형하는 experiment planner
  - 방법: baseline EXIR를 입력으로 받아 constraint on/off, RHS 교체, slack 추가를 수행하는 transformation layer 추가
- 자연어 IR와 EXIR의 차이 자동 분석
  - 방법: 두 IR를 공통 중간 포맷으로 normalize한 뒤 semantic diff 수행
