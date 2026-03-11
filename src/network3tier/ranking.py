from __future__ import annotations

import pandas as pd


WEIGHT_COST = 0.9
WEIGHT_LEADTIME = 0.1
WEIGHT_COVERAGE = 0.1
WEIGHT_SUM = WEIGHT_COST + WEIGHT_LEADTIME + WEIGHT_COVERAGE


def build_summary_workbook(cases) -> pd.DataFrame:
    summary_df = pd.concat([case.summary for case in cases], ignore_index=True)

    best_cost = float(summary_df["Optimal Cost"].min())
    best_leadtime = float(summary_df["Optimal Lead Time (Sec.)"].min())
    best_coverage_time = float(summary_df["Coverage Time (%)"].max())
    best_coverage_vol = float(summary_df["Coverage Vol (%)"].max())

    summary_df["Cost Score"] = best_cost / summary_df["Optimal Cost"]
    summary_df["Lead Time Score"] = best_leadtime / summary_df["Optimal Lead Time (Sec.)"]
    summary_df["Coverage Time Score"] = summary_df["Coverage Time (%)"] / best_coverage_time if best_coverage_time else 0.0
    summary_df["Coverage Vol Score"] = summary_df["Coverage Vol (%)"] / best_coverage_vol if best_coverage_vol else 0.0
    summary_df["Coverage Score"] = (
        summary_df["Coverage Time Score"] + summary_df["Coverage Vol Score"]
    ) / 2.0
    summary_df["Total Score"] = (
        WEIGHT_COST * summary_df["Cost Score"]
        + WEIGHT_LEADTIME * summary_df["Lead Time Score"]
        + WEIGHT_COVERAGE * summary_df["Coverage Score"]
    ) / WEIGHT_SUM

    summary_df["Total Rank"] = summary_df["Total Score"].rank(method="dense", ascending=False).astype(int)
    summary_df["Cost Rank"] = summary_df["Optimal Cost"].rank(method="dense", ascending=True).astype(int)
    summary_df["Lead Time Rank"] = summary_df["Optimal Lead Time (Sec.)"].rank(method="dense", ascending=True).astype(int)
    summary_df["Coverage Rank(Time)"] = summary_df["Coverage Time (%)"].rank(method="dense", ascending=False).astype(int)
    summary_df["Coverage Rank(Vol)"] = summary_df["Coverage Vol (%)"].rank(method="dense", ascending=False).astype(int)

    return summary_df.sort_values(
        ["Total Rank", "Cost Rank", "Optimal Cost"], ascending=[True, True, True]
    ).reset_index(drop=True)
