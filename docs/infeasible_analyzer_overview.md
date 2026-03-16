# Infeasible 원인 분석기 개요

이 문서는 현재 저장소의 IR 자산을 이용해 infeasible 원인 분석기를 어떻게 구성할 수 있는지 설명한다.
목표는 "solver가 infeasible를 반환했다"는 사실을 단순 로그로 남기는 데서 끝내지 않고, 어떤 제약군이 병목인지 단계적으로 분리 진단하는 것이다.

전제는 다음과 같다.

- Precheck fail-fast는 분석기 대상이 아니다.
- 분석기는 오직 solver가 실제로 실행된 뒤 `INFEASIBLE`을 반환한 경우에만 시작한다.
- 분석의 기준 모델은 실행형 IR(EXIR)이다.

이 전제는 이미 [`src/network3tier/cli.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/cli.py)와 [`src/network3tier/infeasible_analysis.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/infeasible_analysis.py)에 반영되어 있다.

## 왜 별도 분석기가 필요한가

최적화 모델에서 infeasible는 단일 원인이 아닐 수 있다. 현재 모델만 봐도 후보군이 여러 층으로 나뉜다.

- 총 공급 부족
- 창고 총 capacity 부족
- `K`개 창고 제약과 수요의 충돌
- Mapping ID에 의한 hard assignment 충돌
- 단일 할당(single-sourcing) 제약의 경직성
- 특정 아크 부재로 인한 downstream 또는 upstream 불가능

이 중 일부는 [`src/network3tier/precheck.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/precheck.py)에서 deterministic하게 걸러낼 수 있다. 하지만 precheck를 통과했는데도 engine infeasible가 발생하는 경우는, 원인이 제약 상호작용 수준에 숨어 있을 가능성이 크다.

이때 필요한 것은 "원인을 추정하는 설명"이 아니라 "한 번에 한 가설만 바꾼 서브모델 실험"이다. IR 기반 분석기는 바로 이 역할을 한다.

## 대략적인 프로세스

분석기 전체 흐름은 5단계로 이해하면 된다.

### 1. Trigger gating

분석기는 모든 실패 케이스에 대해 동작하지 않는다.

- precheck fail-fast면 종료
- solver가 실행되어 `INFEASIBLE`을 반환하면 분석 컨텍스트 생성

현재 CLI는 best model solve가 infeasible일 때 `engine_infeasible_analysis_context.json`을 저장한다. 이 파일은 분석기 시작점 역할을 한다.

### 2. Baseline model 고정

분석기의 첫 번째 원칙은 baseline model을 고정하는 것이다.

- baseline EXIR: `docs/best_model.exir.json`
- schema: `docs/executable_ir_schema.json`
- experiment catalog: `docs/infeasible_experiment_catalog.md`

즉 분석기는 파이썬 코드 자체를 수정 대상으로 보지 않는다. 먼저 baseline EXIR를 기준 truth로 두고, 이후의 모든 실험은 "이 baseline에서 무엇을 바꿨는가"로 표현한다.

### 3. Hypothesis generation

다음 단계는 어떤 원인 가설을 우선 시험할지 정하는 것이다. 이 판단에는 세 입력이 들어간다.

- precheck에서 이미 수집한 issue 목록
- solver가 반환한 infeasible 사실과 로그
- baseline EXIR가 표현하는 제약 구조

예를 들어 다음과 같은 연결이 가능하다.

- `top_k_capacity_shortage`가 있었으면 `warehouse_count_exact` 완화 실험 우선
- `mapped_warehouse_count_exceeds_k`가 있었으면 Mapping ID 고정 또는 warehouse count 충돌 실험 우선
- mapped customer 관련 issue가 있었으면 mapping hard assignment 완화 실험 우선

이 단계의 산출물은 "실험 후보 우선순위 목록"이다. 중요한 점은, 여기서도 아직 정답을 단정하지 않는다는 것이다.

### 4. Submodel experiment execution

각 가설은 baseline EXIR를 부분 수정한 실험 모델로 실행된다. 이 저장소의 카탈로그는 이미 그 방향을 정의하고 있다.

대표 실험은 다음과 같다.

- warehouse count 완화
- Mapping ID hard assignment 제거
- single-sourcing 완화
- unmet demand slack 추가
- warehouse overflow slack 추가
- opened warehouse must-serve 제거
- warehouse set 고정 후 assignment-only feasibility 확인
- assignment 고정 후 upstream flow feasibility 확인

핵심은 한 실험이 한 가설만 바꾸도록 유지하는 것이다. 이렇게 해야 "feasible가 되었는가"라는 결과를 병목 원인과 연결할 수 있다.

### 5. Result interpretation and report

실험 결과는 단순히 feasible/infeasible로만 끝나면 아쉽다. 분석기는 각 실험 결과를 다음 질문에 연결해야 한다.

- 어떤 제약 완화가 feasibility 회복에 직접 기여했는가
- 어느 범주의 병목이 의심되는가
- 원 문제를 바꾸지 않고는 해결이 불가능한가
- 추가로 어떤 세분 실험이 필요한가

최종 산출물은 "원인 후보와 근거"를 담은 진단 리포트가 된다. 형태는 JSON이어도 되고 Markdown이어도 되지만, 핵심은 baseline 대비 어떤 실험이 어떤 결과를 냈는지 추적 가능해야 한다는 점이다.

## 권장 구조

현재 저장소 기준으로 분석기는 4개 계층으로 나누는 것이 자연스럽다.

### 1. Trigger and context layer

역할:

- solver infeasible 발생 여부 감지
- analysis context 생성
- baseline artifact 위치 기록

현재 구현 대응:

- [`src/network3tier/cli.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/cli.py)
- [`src/network3tier/infeasible_analysis.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/infeasible_analysis.py)

이 계층은 분석기의 시작 조건을 엄격히 제한한다. 그 결과 precheck로 이미 증명된 실패와 engine-level infeasible를 혼동하지 않는다.

### 2. Knowledge layer

역할:

- baseline EXIR 읽기
- executable IR schema 검증
- experiment catalog에서 실험 후보 로드
- precheck issue와 실험 trigger 간 매핑 유지

현재 구현 대응:

- [`docs/best_model.exir.json`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/best_model.exir.json)
- [`docs/executable_ir_schema.json`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/executable_ir_schema.json)
- [`docs/infeasible_experiment_catalog.md`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/infeasible_experiment_catalog.md)

이 계층은 분석기의 "지식 베이스"다. 모델 의미와 실험 규칙이 코드 바깥에 있으므로, 분석기는 구현 세부사항에 덜 묶인다.

### 3. Experiment planning and transformation layer

역할:

- baseline EXIR에서 실험 EXIR 생성
- constraint on/off, RHS 교체, slack 주입 같은 변형 수행
- 실험별 변경 이력 기록

현재 상태:

- 완전한 자동 변형 계층은 아직 없다.
- 하지만 catalog가 어떤 조작이 필요한지 이미 정의하고 있다.
- [`src/network3tier/ir_model_builder.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/ir_model_builder.py)는 이런 EXIR를 실행 모델로 내릴 기반을 제공한다.

이 계층이 구축되면 분석기는 "코드를 바꿔 보는 방식"이 아니라 "모델 계약을 변형하는 방식"으로 동작하게 된다.

### 4. Execution and diagnosis layer

역할:

- 실험 EXIR를 solver model로 빌드
- 실험 실행
- 결과 비교
- 원인 후보, 추가 실험 필요성, 권장 후속 조치를 정리

현재 상태:

- conceptually는 정의되어 있지만 end-to-end 자동화는 아직 없다.
- 저장소는 이미 baseline context와 experiment catalog를 제공하므로, 이 계층을 추가할 준비는 되어 있다.

## 적용 시 장점

### 1. 원인 분석이 재현 가능해진다

코드 중심 디버깅은 개인의 숙련도와 기억에 강하게 의존한다. 반면 IR 기반 분석은 "어떤 baseline에서 어떤 제약을 어떻게 바꿨는가"가 artifact로 남는다.

그 결과 다음이 가능해진다.

- 같은 infeasible 사례를 반복 재현
- 과거 분석과 현재 분석 비교
- 팀 내에서 동일한 진단 절차 공유

### 2. 원인 분리가 훨씬 명확해진다

infeasible 분석에서 가장 흔한 실패는 한 번에 여러 조건을 동시에 바꿔 버리는 것이다. 그러면 feasible가 되어도 무엇이 원인이었는지 모른다.

IR 기반 분석은 실험을 constraint 단위로 제한하므로 다음 질문에 답하기 쉬워진다.

- warehouse count가 병목인가
- Mapping ID hard constraint가 병목인가
- capacity 부족인가
- downstream assignment 문제인가, upstream flow 문제인가

즉 "수정해서 되긴 됐다"가 아니라 "무엇을 완화했더니 feasibility가 회복됐다"를 말할 수 있다.

### 3. 분석기와 운영 모델의 연결이 명확해진다

baseline을 EXIR로 고정하면 분석기는 운영 모델과 분리된 장난감 모델을 다루지 않는다. 원 모델과 같은 의미를 가진 baseline 위에서 실험하기 때문에, 진단 결과를 실제 모델 개선 논의로 연결하기 쉽다.

이 점은 단순 로그 기반 root-cause summary보다 훨씬 강하다. 로그만으로는 제약의 대안 경로를 시험할 수 없지만, EXIR 기반 분석은 실제 서브모델을 실행해 볼 수 있다.

### 4. 향후 자동화 범위를 넓히기 쉽다

한 번 구조가 잡히면 다음 기능을 순차적으로 붙일 수 있다.

- precheck issue 기반 실험 우선순위 자동 추천
- baseline EXIR 자동 변형
- 실험 결과 자동 요약
- semantic diff 기반 원인 후보 설명
- LLM이 결과를 읽고 후속 실험 제안

즉 분석기는 단일 기능이 아니라, IR를 중심으로 한 실험 자동화 파이프라인의 시작점이 된다.

### 5. 모델 변경 검증에도 다시 활용할 수 있다

이 분석기는 infeasible 상황만 위한 도구가 아니다. 같은 구조는 모델 변경 후 회귀 검증에도 재활용할 수 있다.

- 이전 baseline과 현재 baseline 비교
- 변경 전후 동일 실험 결과 비교
- 어떤 모델 개정이 특정 infeasible 패턴을 줄였는지 추적

결국 분석기를 위해 만든 IR/실험 구조가 모델 검증 체계 전반으로 확장된다.

## 현실적인 적용 순서

현재 저장소 기준으로는 다음 순서가 가장 현실적이다.

1. 현재처럼 engine infeasible 시 analysis context를 남긴다.
2. catalog에 정의된 실험 중 EXIR 수정이 쉬운 것부터 수동 또는 반자동으로 추가한다.
3. `build_model_from_ir()` 경로와 실험 EXIR 실행을 연결한다.
4. 실험 결과를 JSON 리포트로 정리한다.
5. 그 위에 LLM 또는 규칙 기반 planner를 올려 우선순위 추천을 자동화한다.

이 순서는 현재 코드베이스가 이미 가진 자산을 그대로 활용한다. 즉 새로운 분석기를 처음부터 만드는 것이 아니라, 이미 있는 EXIR, schema, catalog, context 생성 로직을 연결해 점진적으로 완성하는 방식이다.

## 결론

IR를 이용한 infeasible 원인 분석기의 본질은 "infeasible를 설명하는 도구"가 아니라 "가설을 분리해서 검증하는 도구"라는 데 있다.

현재 저장소는 이미 그 출발점에 와 있다.

- precheck와 engine infeasible를 분리하고
- baseline EXIR를 정의해 두었고
- 실험 카탈로그로 어떤 변형이 필요한지 정리했고
- executable IR builder라는 실행 기반도 갖고 있다

남은 일은 이 자산들을 하나의 분석 파이프라인으로 연결하는 것이다. 그렇게 되면 infeasible는 더 이상 solver의 최종 에러 코드가 아니라, 구조적으로 분해 가능한 진단 대상이 된다.
