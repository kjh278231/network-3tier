# Network 3-Tier Optimizer

Plant-Warehouse-Customer 3단 물류 네트워크에서 어떤 창고 후보를 열어야 총비용이 최소가 되는지 계산하는 Python/OR-Tools 프로그램이다.

## 문제 정의

의사결정 대상은 다음 3가지다.

- 어떤 `Warehouse`를 오픈할지
- 각 `Customer`를 어떤 `Warehouse` 하나에 배정할지
- 각 `Plant`에서 각 `Warehouse`로 얼마를 보낼지

현재 구현은 다음 제약을 만족한다.

- 창고 유입 물량은 창고 `Capacity Qty`를 초과할 수 없다.
- Plant 출하량은 Plant `Product Qty`를 초과할 수 없다.
- 각 Customer는 정확히 하나의 Warehouse에만 연결된다.
- `customer.Mapping ID`가 있으면 해당 Customer는 지정된 `Warehouse ID`로만 배정된다.
- `customer.Mapping ID`로 참조된 warehouse는 반드시 오픈된다.
- Customer가 배정된 Warehouse만 오픈된다.
- Warehouse 유입량 = 해당 Warehouse가 담당하는 Customer 수요 합계
- `simulation.Warehouse Qty` 만큼의 warehouse를 정확히 사용한다.
- 사용된 warehouse는 최소 1개 이상의 customer를 반드시 배정받는다.
- Plant -> Warehouse 물량은 정수 단위로 여러 plant에 자유롭게 분할될 수 있다.

## 비용 구조

총비용은 아래 항목의 합으로 계산한다.

- Warehouse 고정비: `warehouse.Fixed Cost * open_warehouse`
- Plant -> Warehouse 운송비: `plantWarehouseCost.Trns Cost * Do Qty`
- Warehouse -> Customer 운송비: `warehouseCustomerCost.Trns Cost * Do Qty`
- Warehouse 운영비: `warehouse.Operation Cost * Do Qty`

가정:

- 비용 목적식은 `Do Qty`만 사용한다.
- `Operation Cost`와 `Trns Cost`는 1:1로 비교 가능한 동일 cost basis를 사용한다.
- `Shipment Qty`는 비용 목적식에 사용하지 않고 `leadtime` 계산에만 사용한다.
- Plant 공급한도는 `Product Qty`를 사용한다.

## Leadtime / Coverage 계산

최적화로 매핑이 결정된 뒤 정적 계산을 수행한다.

- Warehouse -> Customer leadtime:
  `Distance (km) / Speed (km/h) * Customer Shipment Qty`
- Plant -> Warehouse leadtime:
  `Distance (km) / Speed (km/h) * (Warehouse inbound Do Qty / Plant Shipment Qty)`
- Coverage:
  `simulation.Coverage (hour)` 이내에 `warehouse -> customer` one-way time으로 도달 가능한 customer 비율과 Do Qty 비율을 계산

출력 파일의 leadtime 값은 비교가 쉽도록 초(`Sec.`) 단위로 저장한다.

## 모델 종류

두 종류의 모델을 실행한다.

1. `best_model`
   창고 오픈 여부까지 최적화해서 전체 최소비용 해를 구한다.
2. `designated warehouse model`
   `simulation.Warehouse Qty`를 유지한 상태에서 `best_model` 주변의 1-swap warehouse 조합을 최대 10건 샘플링한 뒤,
   각 조합을 강제로 오픈 상태로 고정하고 최선의 mapping 결과를 다시 계산한다.

## Total Rank

종합 점수는 1등 값을 기준으로 0~1로 정규화한 후 계산한다.

- Cost Score: `best_cost / case_cost`
- Lead Time Score: `best_leadtime / case_leadtime`
- Coverage Time Score: `case_coverage_time / best_coverage_time`
- Coverage Vol Score: `case_coverage_vol / best_coverage_vol`
- Coverage Score: `(Coverage Time Score + Coverage Vol Score) / 2`
- Total Score: `(0.9 * Cost Score + 0.1 * Lead Time Score + 0.1 * Coverage Score) / 1.1`

`Total Rank`는 `Total Score` 내림차순으로 산정한다.

## 실행 방법

```bash
pip3 install -r requirements.txt
python3 network_optimizer.py --input TRNS_DOWNLOAD_20260311081304.xls --output-root output
```

옵션:

- `--solver`: `SCIP` 또는 `CBC`
- `--max-samples`: 샘플링할 지정 창고 케이스 수
- `--random-seed`: 샘플링 시드
- `--log-level`: `DEBUG`, `INFO`, `ERROR`

## 출력 파일

- `output/<run_timestamp>/output_summary.xls`: 전체 케이스 비용 순위 종합
- `output/<run_timestamp>/output_case1.xls`: case 상세 결과
- `output/<run_timestamp>/output_case2.xls`: case 상세 결과
- `output/<run_timestamp>/run.log`: 단계별 실행 로그
- `output/<run_timestamp>/run_summary.json`: 실행 요약

각 case 상세 파일에는 다음 시트가 들어간다.

- `summary`
- `plantWarehouseRoute`
- `warehouse`
- `warehouseCustomerRoute`
- `coverageDetail`

## 프로젝트 구조

```text
network-3tier/
|-- network_optimizer.py
|-- src/
|   |-- network3tier/
|   |   |-- cli.py
|   |   |-- domain.py
|   |   |-- loader.py
|   |   |-- logging_utils.py
|   |   |-- optimizer.py
|   |   |-- output.py
|   |   |-- ranking.py
|   |   `-- sampling.py
|-- requirements.txt
`-- README.md
```
