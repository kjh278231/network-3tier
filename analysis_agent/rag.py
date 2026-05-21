from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from data_loader import RunData


class RAGIndex:
    def __init__(self) -> None:
        self._docs: list[dict] = []
        self._vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
        self._matrix = None

    def build(self, documents: list[dict]) -> None:
        self._docs = documents
        texts = [d["text"] for d in documents]
        self._matrix = self._vectorizer.fit_transform(texts)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        if self._matrix is None or not self._docs:
            return []
        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix).flatten()
        indices = np.argsort(scores)[::-1][:top_k]
        return [
            {"doc_id": self._docs[i]["id"], "text": self._docs[i]["text"], "score": float(scores[i])}
            for i in indices
            if scores[i] > 0
        ]


def _safe(v, fmt=None) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    if fmt:
        return fmt.format(v)
    return str(v)


def build_documents(run_data: RunData) -> list[RAGIndex]:
    docs: list[dict] = []

    # 1. Simulation context
    sim = run_data.simulation
    total_demand = sum(c.get("doQty", 0) or 0 for c in run_data.customers)
    total_supply = sum(p.get("productQty", 0) or 0 for p in run_data.plants)
    total_capacity = sum(w.get("capacityQty", 0) or 0 for w in run_data.warehouses)
    docs.append({
        "id": "sim_context",
        "text": (
            f"SIMULATION: {sim.get('simulationName', '')}\n"
            f"Warehouse Qty Required: {sim.get('warehouseQty', 0)}, "
            f"Speed: {sim.get('speedKmh', 0)} km/h, Coverage: {sim.get('coverageHours', 0)} hours\n"
            f"Plants: {len(run_data.plants)} plant(s), total product qty = {total_supply:,.0f}\n"
            f"Warehouse candidates: {len(run_data.warehouses)}, total throughput capacity = {total_capacity:,.0f}\n"
            f"Customers: {len(run_data.customers)}, total Do Qty = {total_demand:,.0f}"
        ),
    })

    # 2. Cross-case summary
    if run_data.summary_rows:
        lines = [f"CROSS-CASE RANKING SUMMARY ({len(run_data.summary_rows)} cases):"]
        for row in run_data.summary_rows:
            lines.append(
                f"Rank {_safe(row.get('Total Rank'))} | {row.get('Case Name', '')} | "
                f"Type={row.get('Case Type', '')} | Cost={_safe(row.get('Optimal Cost'), '{:,.0f}')} | "
                f"LT={_safe(row.get('Optimal Lead Time (Sec.)'), '{:.0f}')}s | "
                f"CovTime={_safe(row.get('Coverage Time (%)'), '{:.1f}')}% | "
                f"CovVol={_safe(row.get('Coverage Vol (%)'), '{:.1f}')}% | "
                f"Score={_safe(row.get('Total Score'), '{:.4f}')}"
            )
        docs.append({"id": "cross_case_summary", "text": "\n".join(lines)})

    for case in run_data.cases:
        s = case.summary
        cname = case.case_name

        # 3. Per-case summary
        docs.append({
            "id": f"case_summary_{cname}",
            "text": (
                f"CASE: {cname} (Type: {case.case_type}, Rank: {_safe(s.get('Total Rank'))})\n"
                f"Total Cost: {_safe(s.get('Optimal Cost'), '{:,.0f}')} "
                f"(Inbound: {_safe(s.get('Inbound Cost'), '{:,.0f}')}, "
                f"Warehouse: {_safe(s.get('Warehouse Cost'), '{:,.0f}')}, "
                f"Outbound: {_safe(s.get('Outbound Cost'), '{:,.0f}')}) \n"
                f"Lead Time: {_safe(s.get('Optimal Lead Time (Sec.)'), '{:.0f}')} sec | "
                f"Coverage Time: {_safe(s.get('Coverage Time (%)'), '{:.1f}')}% | "
                f"Coverage Vol: {_safe(s.get('Coverage Vol (%)'), '{:.1f}')}%\n"
                f"Scores: Cost={_safe(s.get('Cost Score'), '{:.4f}')}, "
                f"LeadTime={_safe(s.get('Lead Time Score'), '{:.4f}')}, "
                f"Coverage={_safe(s.get('Coverage Score'), '{:.4f}')}, "
                f"Total={_safe(s.get('Total Score'), '{:.4f}')}\n"
                f"Selected Warehouses ({_safe(s.get('Selected Warehouse Count'))}): "
                f"{s.get('Selected Warehouses', '')}"
            ),
        })

        # 4. Per-warehouse detail
        for w in case.warehouse_summary:
            wid = w.get("Warehouse Id", "")
            inbound = w.get("Inbound Qty") or 0
            outbound = w.get("Outbound Qty") or 0
            capacity = w.get("Throughput Capacity Qty") or 0
            util = (outbound / capacity * 100) if capacity else 0
            docs.append({
                "id": f"warehouse_{cname}_{wid}",
                "text": (
                    f"WAREHOUSE: {wid} {w.get('Warehouse Location Name', '')} (Case: {cname})\n"
                    f"Inbound: {inbound:,.0f} | Outbound: {outbound:,.0f} | "
                    f"Capacity: {capacity:,.0f} | Utilization: {util:.1f}%\n"
                    f"Fixed Cost: {_safe(w.get('Fixed Cost'), '{:,.0f}')} | "
                    f"Operation Cost: {_safe(w.get('Operation Cost'), '{:,.0f}')}\n"
                    f"Assigned Customers: {_safe(w.get('Assigned Customer Count'))} | "
                    f"Coverage: {_safe(w.get('Covered Customer Pct'), '{:.1f}')}% (customers) / "
                    f"{_safe(w.get('Covered DoQty Pct'), '{:.1f}')}% (DoQty)"
                ),
            })

        # 5. Plant-warehouse routes summary
        if case.plant_warehouse_routes:
            lines = [f"PLANT-WAREHOUSE ROUTES (Case: {cname}):"]
            for r in case.plant_warehouse_routes:
                lines.append(
                    f"  {r.get('Plant Id', '')} → {r.get('Warehouse Id', '')}: "
                    f"DoQty={_safe(r.get('Do Qty'), '{:,.0f}')}, "
                    f"Cost={_safe(r.get('Cost'), '{:,.0f}')}, "
                    f"LT={_safe(r.get('Lead Time (Sec.)'), '{:.0f}')}s, "
                    f"Dist={_safe(r.get('Distance (km)'), '{:.1f}')}km"
                )
            docs.append({"id": f"pw_routes_{cname}", "text": "\n".join(lines)})

        # 6. Customer-warehouse assignment summary (aggregated by warehouse)
        if case.warehouse_customer_routes:
            import pandas as pd
            wc_df = pd.DataFrame(case.warehouse_customer_routes)
            lines = [f"CUSTOMER-WAREHOUSE ASSIGNMENTS (Case: {cname}):"]
            for wid, grp in wc_df.groupby("Warehouse Id"):
                avg_dist = grp["Distance (km)"].mean() if "Distance (km)" in grp.columns else 0
                total_do = grp["Do Qty"].sum() if "Do Qty" in grp.columns else 0
                covered = (grp["Coverage YN"] == "Y").sum() if "Coverage YN" in grp.columns else 0
                cov_pct = covered / len(grp) * 100 if len(grp) else 0
                lines.append(
                    f"  {wid}: {len(grp)} customers, DoQty={total_do:,.0f}, "
                    f"avg Dist={avg_dist:.1f}km, Coverage={cov_pct:.1f}%"
                )
            docs.append({"id": f"wc_assignments_{cname}", "text": "\n".join(lines)})

        # 7. Lead time distribution
        if case.warehouse_customer_routes:
            import pandas as pd
            wc_df = pd.DataFrame(case.warehouse_customer_routes)
            lt_col = "Lead Time (Sec.)"
            if lt_col in wc_df.columns:
                lts = wc_df[lt_col].dropna().values
                if len(lts) > 0:
                    p50, p90, p95 = np.percentile(lts, [50, 90, 95])
                    docs.append({
                        "id": f"lt_distribution_{cname}",
                        "text": (
                            f"LEAD TIME DISTRIBUTION (Case: {cname}):\n"
                            f"Total system lead time: {_safe(s.get('Optimal Lead Time (Sec.)'), '{:.0f}')} sec\n"
                            f"Outbound (WH→Customer) lead times:\n"
                            f"  mean={lts.mean():.0f}s, median={p50:.0f}s, "
                            f"p90={p90:.0f}s, p95={p95:.0f}s, max={lts.max():.0f}s"
                        ),
                    })

    return docs


def build_rag_index(run_data: RunData) -> RAGIndex:
    docs = build_documents(run_data)
    idx = RAGIndex()
    idx.build(docs)
    return idx
