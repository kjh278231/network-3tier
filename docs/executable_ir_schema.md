# Executable IR Schema

이 문서는 현재 저장소의 설명형 IR(`best_model_ir.json`, `designated_model_ir.json`)을
실행 가능한 IR로 승격하기 위한 스키마를 정의한다.

목표는 다음과 같다.

- `build_model_from_ir(ir, data)` 형태의 모델 빌더가 문자열 파싱 없이 동작
- OR-Tools CP-SAT / MIP 백엔드로 변환 가능한 선형 모델 표현
- 기존 3-tier 네트워크 설계 문제와 designated 변형 모두 표현 가능

## 설계 원칙

- 제약식과 목적식은 자연어가 아니라 구조화된 expression tree로 표현한다.
- 변수 도메인과 인덱스 확장 규칙은 명시적으로 기록한다.
- 데이터 값은 IR에 직접 내장하지 않고, `parameter_bindings`와 `sets.source`를 통해 외부 데이터와 연결한다.
- 실행 경로에서 필요한 분기 로직(`Mapping ID`, designated warehouse fixing 등)은 `rules` 또는 일반 constraint로 표현한다.
- 선형 모델만 대상으로 하므로 비선형 곱은 금지한다. 허용되는 곱은 `scalar * term` 형태만 허용한다.

## Top-level Shape

```json
{
  "ir_version": "1.0",
  "model_name": "best_model",
  "problem_type": "three_tier_network_design",
  "backend_class": "linear_mip",
  "objective": {},
  "sets": [],
  "parameters": [],
  "variables": [],
  "constraints": [],
  "rules": [],
  "parameter_bindings": [],
  "notes": []
}
```

## 필드 설명

### `sets`

집합과 아크 정의를 기계가 확장할 수 있도록 표현한다.

```json
{
  "name": "warehouses",
  "symbol": "W",
  "type": "entity",
  "source": {
    "kind": "table",
    "table": "warehouse",
    "key": ["Warehouse ID"],
    "filters": [
      {
        "column": "Active Y/N",
        "op": "eq",
        "value": "Y"
      }
    ]
  }
}
```

아크 집합은 `type = "arc"`로 두고 `from`, `to`, `source.key`를 명시한다.

```json
{
  "name": "warehouse_customer_arcs",
  "symbol": "A_wc",
  "type": "arc",
  "from": "warehouses",
  "to": "customers",
  "source": {
    "kind": "table",
    "table": "warehouseCustomerCost",
    "key": ["Warehouse ID", "Customer ID"]
  }
}
```

### `parameters`

파라미터는 값 타입과 인덱스를 함께 가진다.

```json
{
  "name": "customer_demand",
  "symbol": "d",
  "value_type": "integer",
  "index_sets": ["customers"],
  "binding": {
    "kind": "column",
    "table": "customer",
    "key": ["Customer ID"],
    "value_column": "Do Qty"
  }
}
```

스칼라 파라미터 예시:

```json
{
  "name": "required_warehouse_count",
  "symbol": "K",
  "value_type": "integer",
  "index_sets": [],
  "binding": {
    "kind": "scalar",
    "table": "simulation",
    "row": 0,
    "value_column": "Warehouse Qty"
  }
}
```

### `variables`

변수는 타입, 인덱스, 도메인, 활성 인덱스 조건을 명시한다.

```json
{
  "name": "plant_to_warehouse_flow",
  "symbol": "f",
  "var_type": "integer",
  "index_sets": ["plant_warehouse_arcs"],
  "domain": {
    "lb": 0,
    "ub_expr": {
      "op": "min",
      "args": [
        { "op": "param", "name": "plant_supply", "index": ["plant"] },
        { "op": "param", "name": "warehouse_capacity", "index": ["warehouse"] }
      ]
    }
  }
}
```

`index_sets`가 arc일 경우 구현체는 해당 아크의 endpoint key를 통해 `(plant, warehouse)` 인덱스를 확장한다.

### `constraints`

제약은 `forall` 범위와 `lhs`, `sense`, `rhs`를 구조화해서 저장한다.

```json
{
  "id": "customer_single_sourcing",
  "kind": "linear",
  "forall": [
    { "name": "customer", "set": "customers" }
  ],
  "lhs": {
    "op": "sum",
    "over": [
      { "name": "arc", "set": "warehouse_customer_arcs", "where": [
        { "left": { "op": "item", "name": "arc", "field": "customer" }, "cmp": "eq", "right": { "op": "index", "name": "customer" } }
      ] }
    ],
    "expr": {
      "op": "var",
      "name": "assign_customer",
      "index_from": { "arc": ["warehouse", "customer"] }
    }
  },
  "sense": "eq",
  "rhs": { "op": "const", "value": 1 }
}
```

### `objective`

목적함수도 선형식으로만 표현한다.

```json
{
  "sense": "min",
  "expr": {
    "op": "add",
    "terms": [
      {
        "op": "sum",
        "over": [{ "name": "warehouse", "set": "warehouses" }],
        "expr": {
          "op": "mul",
          "left": { "op": "param", "name": "warehouse_fixed_cost", "index": ["warehouse"] },
          "right": { "op": "var", "name": "open_warehouse", "index": ["warehouse"] }
        }
      }
    ]
  }
}
```

### `rules`

비즈니스 규칙을 별도 메타데이터로 유지하되, 모델 빌더는 이를 일반 constraint 생성으로 치환한다.
이 필드는 필수가 아니다. 설명성과 검증 용도다.

예시:

```json
{
  "name": "mapping_id_forces_assignment",
  "enabled": true,
  "input_parameter": "customer_mapping_id",
  "effect": [
    "force_assignment_to_mapped_warehouse",
    "force_open_mapped_warehouse"
  ]
}
```

## Expression Grammar

허용되는 expression node:

- `const`
- `param`
- `var`
- `index`
- `item`
- `add`
- `sub`
- `mul`
- `sum`
- `min`

제약/목적식에서 허용되는 선형성 규칙:

- `mul`은 한쪽이 상수/파라미터여야 한다.
- `var * var` 금지
- `min`은 변수 domain 상한 계산 같은 메타 표현에서만 허용하고, 일반 선형식 내부에서는 금지

## 현재 프로젝트 기준 권장 모델 분리

### `best_model.exir.json`

- 변수
  - `open_warehouse`
  - `assign_customer`
  - `plant_to_warehouse_flow`
- 제약
  - assignment
  - mapping-forced assignment
  - capacity-activation
  - opened warehouse must serve
  - warehouse flow balance
  - plant supply
  - mapped warehouse open fixing
  - exact warehouse count

### `designated_model.exir.json`

- `designated_warehouses` 집합이 외생 입력
- `open_warehouse_fixed`는 선택적으로 생략 가능
  - 생략 시 `y[w] = 1`은 변수 없이 상수 처리
- 제약
  - assignment
  - mapping-forced assignment
  - capacity
  - warehouse must serve
  - flow balance
  - plant supply
  - designated warehouse count consistency

## 현재 설명형 IR에서의 변환 규칙

- `sets`의 `source` 텍스트를 `source.kind/table/key/filters` 구조로 분해
- `parameters.source`를 `binding` 구조로 정규화
- `decision_variables.type`을 `var_type`으로 유지하되 `domain.lb`, `domain.ub` 또는 `domain.ub_expr`를 추가
- `constraints.expression_summary`는 삭제하고 `forall/lhs/sense/rhs`로 대체
- `objective.terms`는 개별 term 리스트 대신 하나의 `objective.expr` tree로 통합
- `assumptions` 중 실행에 필요한 내용은 `rules`나 명시적 constraint로 승격
- `unknowns`는 실행형 IR에 남기지 않고 사전에 데이터 계약으로 해결

## 구현상 장점

- `build_model_from_ir()`가 family별 문자열 해석 없이 AST를 순회해 선형식을 생성 가능
- CP-SAT과 MIP 빌더가 같은 IR를 공유 가능
- 설명형 IR와 실행형 IR를 병행 유지할 수 있음

## 구현상 남는 제약

- 일반 선형식 AST를 도입하면 스키마는 명확해지지만, authoring 난이도는 올라간다.
- 사람이 수동으로 작성하기엔 장황하므로, 장기적으로는
  `descriptive IR -> executable IR` 변환기가 필요하다.
