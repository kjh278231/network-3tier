from __future__ import annotations

from pathlib import Path

import pandas as pd
import xlwt

from .domain import CaseResult


def write_xls_workbook(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    workbook = xlwt.Workbook()
    header_style = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
    float_style = xlwt.easyxf(num_format_str="0.000")

    for raw_sheet_name, frame in sheets.items():
        sheet = workbook.add_sheet(raw_sheet_name[:31])
        df = frame.copy()

        for col_idx, column in enumerate(df.columns):
            sheet.write(0, col_idx, str(column), header_style)

        for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
            for col_idx, value in enumerate(row):
                if pd.isna(value):
                    sheet.write(row_idx, col_idx, "")
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    sheet.write(row_idx, col_idx, float(value), float_style)
                else:
                    sheet.write(row_idx, col_idx, str(value))

        for col_idx, column in enumerate(df.columns):
            max_width = max([len(str(column))] + [len(str(v)) for v in df.iloc[:, col_idx].fillna("").tolist()])
            sheet.col(col_idx).width = min((max_width + 2) * 256, 256 * 60)

    workbook.save(str(path))


def write_case_output(run_dir: Path, case_index: int, case_result: CaseResult) -> Path:
    case_path = run_dir / f"output_case{case_index}.xls"
    write_xls_workbook(
        case_path,
        {
            "summary": case_result.summary,
            "precheckIssues": case_result.precheck_issues,
            "plantWarehouseRoute": case_result.plant_warehouse_routes,
            "warehouse": case_result.warehouse_summary,
            "warehouseCustomerRoute": case_result.warehouse_customer_routes,
            "coverageDetail": case_result.coverage_detail,
        },
    )
    return case_path
