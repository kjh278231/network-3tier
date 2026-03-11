from __future__ import annotations

import pandas as pd


WEIGHT_COST = 0.9
WEIGHT_LEADTIME = 0.1
WEIGHT_COVERAGE = 0.1
WEIGHT_SUM = WEIGHT_COST + WEIGHT_LEADTIME + WEIGHT_COVERAGE


def build_summary_workbook(cases) -> pd.DataFrame:
    summary_df = pd.concat([case.summary for case in cases], ignore_index=True)
    if "Run Status" not in summary_df.columns:
        summary_df["Run Status"] = "SUCCESS"
    if "Fail Stage" not in summary_df.columns:
        summary_df["Fail Stage"] = None
    if "Fail Reason Count" not in summary_df.columns:
        summary_df["Fail Reason Count"] = None
    if "Fail Reason Summary" not in summary_df.columns:
        summary_df["Fail Reason Summary"] = None

    success_mask = summary_df["Run Status"].fillna("SUCCESS") == "SUCCESS"
    if not success_mask.any():
        return summary_df.reset_index(drop=True)

    success_df = summary_df.loc[success_mask].copy()
    best_cost = float(success_df["Optimal Cost"].min())
    best_leadtime = float(success_df["Optimal Lead Time (Sec.)"].min())
    best_coverage_time = float(success_df["Coverage Time (%)"].max())
    best_coverage_vol = float(success_df["Coverage Vol (%)"].max())

    success_df["Cost Score"] = best_cost / success_df["Optimal Cost"]
    success_df["Lead Time Score"] = best_leadtime / success_df["Optimal Lead Time (Sec.)"]
    success_df["Coverage Time Score"] = (
        success_df["Coverage Time (%)"] / best_coverage_time if best_coverage_time else 0.0
    )
    success_df["Coverage Vol Score"] = (
        success_df["Coverage Vol (%)"] / best_coverage_vol if best_coverage_vol else 0.0
    )
    success_df["Coverage Score"] = (
        success_df["Coverage Time Score"] + success_df["Coverage Vol Score"]
    ) / 2.0
    success_df["Total Score"] = (
        WEIGHT_COST * success_df["Cost Score"]
        + WEIGHT_LEADTIME * success_df["Lead Time Score"]
        + WEIGHT_COVERAGE * success_df["Coverage Score"]
    ) / WEIGHT_SUM

    success_df["Total Rank"] = success_df["Total Score"].rank(method="dense", ascending=False).astype(int)
    success_df["Cost Rank"] = success_df["Optimal Cost"].rank(method="dense", ascending=True).astype(int)
    success_df["Lead Time Rank"] = success_df["Optimal Lead Time (Sec.)"].rank(method="dense", ascending=True).astype(int)
    success_df["Coverage Rank(Time)"] = success_df["Coverage Time (%)"].rank(method="dense", ascending=False).astype(int)
    success_df["Coverage Rank(Vol)"] = success_df["Coverage Vol (%)"].rank(method="dense", ascending=False).astype(int)

    summary_df.loc[success_mask, success_df.columns] = success_df
    return summary_df.sort_values(
        ["Total Rank", "Cost Rank", "Optimal Cost"], ascending=[True, True, True]
    ).reset_index(drop=True)
