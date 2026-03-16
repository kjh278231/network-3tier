# IR의 필요성, 현재 장점, 발전 방향

이 문서는 현재 저장소 구현을 기준으로 IR(Intermediate Representation)의 역할을 설명한다.
대상 독자는 최적화 모델링과 solver 사용 경험은 있지만, 이 저장소의 IR 설계 의도는 처음 보는 사람이다.

핵심 전제는 다음과 같다.

- 현재 운영 경로의 기준 진실은 [`src/network3tier/optimizer.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/optimizer.py)다.
- 설명형 IR은 [`docs/best_model_ir.json`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/best_model_ir.json), [`docs/designated_model_ir.json`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/designated_model_ir.json)에 정리되어 있다.
- 실행형 IR과 빌더는 [`docs/best_model.exir.json`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/best_model.exir.json), [`docs/executable_ir_schema.md`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/executable_ir_schema.md), [`src/network3tier/ir_model_builder.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/ir_model_builder.py)에 있다.
- 따라서 이 저장소에서 IR는 단순 설명 문서가 아니라, 모델 의미를 외부 아티팩트로 고정하고 향후 실행 경로로 승격시키기 위한 중간 계층이다.

## 현재 저장소에서 IR가 차지하는 위치

현재 최적화 모델은 `optimizer.py`에서 직접 생성된다. 변수 `y`, `x`, `f`를 만들고, customer single-sourcing, warehouse capacity, flow conservation, plant supply, warehouse count, Mapping ID 강제 배정, objective coefficient 설정을 코드에서 바로 정의한다.

이 구조는 실행에는 충분히 직접적이지만, 모델의 의미가 파이썬 제어 흐름 안에 묻힌다. 예를 들어 어떤 제약이 존재하는지, designated 모델과 best 모델이 정확히 무엇이 다른지, 특정 변경이 제약 의미를 바꿨는지는 코드 diff만으로는 빠르게 확인하기 어렵다.

이 문제를 완화하기 위해 저장소는 두 종류의 IR를 이미 갖고 있다.

- 설명형 IR: 모델의 집합, 파라미터, 결정변수, 제약, 가정, 데이터 매핑을 사람이 읽기 좋은 구조로 고정한다.
- 실행형 IR: expression tree와 구조화된 set/parameter/variable/constraint 정의를 통해 모델 빌더가 문자열 파싱 없이 solver model을 구성할 수 있게 한다.

즉 현재 상태는 "코드만 있는 단계"를 이미 지나 있다. 다만 아직 운영 solve 경로가 executable IR builder를 직접 사용하지는 않는다. 이 점은 장점과 한계를 함께 판단할 때 중요하다.

## 왜 IR가 필요한가

### 1. 모델 의미를 코드 외부에 고정할 필요가 있다

최적화 코드만으로도 모델은 실행할 수 있다. 하지만 실행 가능하다는 것과 모델 의미가 명시적이라는 것은 다르다.

현재 `optimizer.py`는 다음 정보를 모두 포함한다.

- 어떤 index 공간에 변수를 생성하는지
- 각 변수의 도메인이 무엇인지
- 어떤 제약이 어떤 반복 범위에서 추가되는지
- objective coefficient가 어떤 데이터와 연결되는지
- Mapping ID 같은 비즈니스 규칙이 어디에서 hard constraint로 반영되는지

이런 정보가 코드에만 있으면, 모델 semantics를 확인하려면 항상 구현을 다시 읽어야 한다. IR는 이 의미를 별도 아티팩트로 고정한다. 그 결과 "코드가 무엇을 하도록 작성되었는가"와 "모델이 무엇을 의미하는가"를 분리해서 볼 수 있다.

### 2. 변경 검토를 코드 diff가 아니라 모델 diff로 볼 수 있다

IR의 가장 실질적인 장점 중 하나는 변경 검토의 관점을 바꾼다는 점이다.

코드 diff는 보통 다음 질문에 바로 답하지 못한다.

- 이번 변경이 제약 추가인지, 조건 완화인지, 단순 리팩터링인지
- 목적함수 가중치가 바뀐 것인지, 데이터 매핑만 바뀐 것인지
- designated variant에서만 의미가 변했는지, 공통 모델이 변했는지

반면 descriptive IR나 executable IR가 있으면 diff 단위가 `constraints`, `variables`, `parameters`, `rules`가 된다. 이 형태는 최적화 관점의 의미 변화와 훨씬 직접적으로 대응한다.

### 3. 과거 대비 코드가 의도대로 동작하는지 확인할 기준선이 생긴다

사용자 관점에서 중요한 장점은 여기다. IR가 있으면 "예전과 같은 모델이 맞는가"를 확인할 기준선을 만들 수 있다.

예를 들어 다음과 같은 검증 흐름을 생각할 수 있다.

- 리팩터링 전후의 descriptive IR를 비교해 제약 수, 제약 정의, 변수 집합, 가정이 동일한지 확인
- executable IR를 기준 모델로 두고, 코드 변경 후에도 같은 expression tree와 binding 구조가 유지되는지 점검
- infeasible 분석 실험에서 baseline EXIR는 그대로 두고 일부 constraint만 변형한 실험 IR를 비교해, 원인 분리 진단이 실제로 한 가지 가설만 바꾸고 있는지 확인

IR가 자동으로 정답을 보장하지는 않는다. 하지만 무엇이 바뀌었는지와 무엇을 검증해야 하는지를 훨씬 명확하게 만든다. 이 점이 코드만 있을 때와의 가장 큰 차이다.

### 4. 후속 분석과 자동화를 위한 안정적인 입력 형식이 필요하다

현재 저장소는 infeasible 상황에서 [`src/network3tier/infeasible_analysis.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/infeasible_analysis.py)를 통해 `engine_infeasible_analysis_context.json`을 만들고, baseline artifact로 `docs/best_model.exir.json`을 참조한다.

이 설계는 중요한 의미를 가진다.

- solver가 실제로 실행된 뒤 infeasible가 난 경우에만 분석을 시작한다.
- 분석기의 입력은 코드 조각이 아니라 executable IR와 schema, experiment catalog다.
- 따라서 후속 실험은 "코드를 직접 수정하는 방식"이 아니라 "baseline IR를 변형하는 방식"으로 확장될 수 있다.

이런 안정적인 입력 형식이 없으면 infeasible 분석 자동화는 결국 구현 의존적인 ad-hoc 스크립트로 흘러가기 쉽다.

## 현재 구현 기준 IR의 장점

### 설명형 IR의 장점

설명형 IR는 현재 운영 경로와 가장 직접적으로 연결되어 있다. [`docs/best_model_ir.json`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/best_model_ir.json)과 [`docs/designated_model_ir.json`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/designated_model_ir.json)은 각각 best model, designated model의 집합, 파라미터, 결정변수, 제약, objective를 구조화해 담고 있고, 각 제약에는 `source_locations`가 붙어 있다.

이 구조의 장점은 다음과 같다.

- 코드와 IR 사이의 역추적이 가능하다.
- best model과 designated model의 차이를 JSON 수준에서 비교할 수 있다.
- 리뷰 시 "이 제약이 왜 존재하는가"를 코드 맥락과 함께 설명하기 쉽다.

특히 `source_locations`는 단순 메모 이상의 의미가 있다. 제약 정의가 실제로 어느 코드 블록에서 나오는지 추적 가능하므로, IR가 추상 설명으로 붕 뜨지 않는다. 현재처럼 운영 경로가 아직 코드 중심일 때는 이 연결성이 특히 중요하다.

### 실행형 IR의 장점

실행형 IR의 목표는 [`docs/executable_ir_schema.md`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/executable_ir_schema.md)에 명확하게 드러나 있다.

- `build_model_from_ir(ir, data)` 형태의 모델 빌더 지원
- 문자열 파싱 없는 expression tree 기반 모델 구성
- 선형 MIP/CP-SAT 계열 백엔드로의 변환 가능성 확보

실제 [`src/network3tier/ir_model_builder.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/ir_model_builder.py)는 이미 다음 기능을 갖고 있다.

- set source를 테이블 또는 외부 입력에서 materialize
- parameter binding을 scalar/column/input 형태로 해석
- variable index expansion과 domain evaluation 수행
- 구조화된 constraint와 objective를 solver expression으로 변환

이것의 의미는 "모델을 코드로 직접 쓰는 단계"에서 "구조화된 모델을 실행하는 단계"로 갈 수 있는 최소 기반이 이미 있다는 것이다. 현재 builder는 `backend_class='linear_mip'` 중심이고, 단일 index set 같은 제약도 있지만, IR를 실행 경로로 승격시키는 핵심 축은 이미 마련되어 있다.

### 분석 및 실험 측면의 장점

[`docs/infeasible_experiment_catalog.md`](/mnt/c/Users/ADMIN/Workspace/network-3tier/docs/infeasible_experiment_catalog.md)는 executable IR 기반 서브모델 실험이 왜 중요한지를 잘 보여준다.

예를 들어 다음 실험은 모두 "원 모델에서 어떤 제약 또는 목적을 바꾸는가"를 명확히 정의하고 있다.

- warehouse count 완화
- Mapping ID hard assignment 제거
- single-sourcing 완화
- unmet demand slack 추가
- warehouse overflow slack 추가
- opened warehouse must-serve 제약 제거

이런 실험을 코드 분기만으로 관리하면 variant 수가 늘수록 유지보수가 급격히 어려워진다. 반면 IR 중심으로 보면 baseline model과 experiment model의 차이를 제약 단위로 다룰 수 있다. 즉 IR는 단순 재현성 도구가 아니라, 실험 공간을 제어 가능한 단위로 쪼개는 도구다.

## "과거 대비 의도대로 동작하는지" 확인하는 관점에서의 가치

이 저장소에서 IR의 가장 설득력 있는 사용 사례는 회귀 검증 기준선으로서의 역할이다.

### 시나리오 1. 리팩터링 후에도 모델 semantics가 유지되는지 확인

`optimizer.py` 내부를 정리하거나 helper 함수로 분리하는 리팩터링은 코드 구조를 크게 바꾸지만 모델 의미는 바꾸지 않아야 할 수 있다. 이때 descriptive IR를 다시 생성하거나 유지 기준과 비교하면, 변경이 단순 구조 정리인지 실제 constraint 변경인지 빠르게 구분할 수 있다.

### 시나리오 2. designated 변형이 정확히 어떤 차이만 도입하는지 확인

best model과 designated model의 차이를 코드 분기로만 관리하면 의도하지 않은 공통 경로 변경이 섞일 수 있다. 하지만 두 descriptive IR를 비교하면 "지정 창고 고정 관련 제약과 파라미터만 늘었는지", "공통 objective나 flow 제약까지 바뀌었는지"를 구조적으로 볼 수 있다.

### 시나리오 3. infeasible 진단 실험이 한 가지 가설만 바꾸는지 확인

실험용 서브모델은 원 문제를 해결하기 위한 것이 아니라 infeasibility 원인을 분해하기 위한 것이다. 이때 baseline EXIR와 실험 EXIR의 차이를 constraint on/off, RHS 변경, slack 주입 단위로 유지하면, 진단 결과를 해석하기 쉬워진다.

요약하면 IR는 "동작 결과가 같아 보인다"는 수준의 확인을 넘어서, "같아야 하는 모델 계약이 실제로 유지됐는가"를 따질 수 있게 해준다.

## 현재 한계

현재 저장소의 IR는 가치가 분명하지만, 아직 완결된 상태는 아니다.

- 운영 solve 경로는 아직 [`src/network3tier/optimizer.py`](/mnt/c/Users/ADMIN/Workspace/network-3tier/src/network3tier/optimizer.py)를 직접 사용하고, executable IR builder를 호출하지 않는다.
- executable IR는 현재 best model 중심이다. designated model에 대한 executable IR는 아직 없다.
- descriptive IR에서 executable IR로 가는 자동 변환기는 없다.
- `optimizer.py`와 `build_model_from_ir()`가 semantic equivalence를 만족하는지 검증하는 테스트 하네스가 없다.
- builder 구현은 현재 `linear_mip`과 일부 단순화된 인덱싱 규칙에 초점을 맞추고 있다.

따라서 현재 시점에 "IR 기반 실행 경로가 완전히 운영에 통합되었다"거나 "코드와 IR의 자동 등가성 검증이 이미 된다"고 말하면 과장이다. 맞는 표현은 "그 방향으로 가기 위한 골격이 확보되어 있다"이다.

## 향후 발전 방향

### 1. 운영 코드와 EXIR builder의 등가성 검증 추가

가장 먼저 필요한 것은 성능 최적화가 아니라 의미 검증이다. 동일 입력에 대해 `optimizer.py` 경로와 `build_model_from_ir()` 경로가 같은 변수 집합, 같은 제약 의미, 같은 최적해를 내는지 비교하는 테스트가 있어야 한다.

이 단계가 있어야 IR가 설명 자산을 넘어 실행 계약으로 승격된다.

### 2. designated model용 executable IR 추가

현재 descriptive IR는 best와 designated를 모두 다루지만, executable IR는 best model 중심이다. designated 모델도 executable IR로 표현되면 variant 관리가 코드 분기에서 IR 차이 관리로 이동할 수 있다.

### 3. EXIR transformation layer 추가

`docs/infeasible_experiment_catalog.md`가 요구하는 실험 대부분은 baseline EXIR에 대해 다음 조작을 지원하면 된다.

- constraint enable/disable
- RHS 교체
- slack + penalty 주입
- variable fixing
- subset filtering
- objective replacement

이 계층이 생기면 infeasible 분석용 서브모델 실험을 코드 수정 없이 생성할 수 있다.

### 4. descriptive IR -> executable IR 자동 변환

현재 두 IR는 목적이 다르기 때문에 병존하지만, 장기적으로는 설명형 IR와 실행형 IR 사이의 중복 관리 비용이 커질 수 있다. 자동 변환 계층이 있으면 사람이 읽는 모델 설명과 기계가 실행하는 모델 정의를 더 강하게 연결할 수 있다.

### 5. solver backend 확장과 semantic diff 도구 추가

실행형 IR가 안정화되면 backend 확장과 semantic diff 도구가 자연스러운 다음 단계가 된다.

- 동일 EXIR를 다른 backend로 내려 solver 의존성을 줄일 수 있다.
- descriptive IR와 EXIR를 normalize해서 비교하면, 문서 의미와 실행 의미가 어긋나는 지점을 자동으로 찾을 수 있다.

## 결론

현재 저장소에서 IR의 가치는 "모델을 예쁘게 문서화했다"는 데 있지 않다.
더 중요한 가치는 다음 세 가지다.

- 모델 semantics를 코드 밖에 명시적으로 고정한다.
- 변경 검토와 회귀 검증을 모델 단위로 수행할 수 있게 한다.
- infeasible 분석과 서브모델 실험을 구조적으로 확장할 수 있게 한다.

즉 이 저장소에서 IR는 문서가 아니라, 점진적으로 실행 가능해지는 모델 계약(model contract)으로 보는 것이 맞다. 현재는 아직 운영 경로와 완전히 통합되지는 않았지만, 이미 검증성과 확장성을 높이는 실질적인 역할을 하고 있고, 향후에는 코드 중심 모델 생성의 상당 부분을 대체할 수 있는 방향으로 발전할 수 있다.
