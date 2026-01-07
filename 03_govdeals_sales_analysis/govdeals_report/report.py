from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ---- Your CSV column names ----
COL_FY = "Fiscal Year"
COL_ITEM = "Description"
COL_CATEGORY = "Category"
COL_SOLD_AMT = "Sold Amount"
COL_NET = "Net Results"
COL_STATUS = "Sold/Unsold"
COL_VISITORS = "Visitors"
COL_SPLIT_OLD = "% Split"
COL_SPLIT_NEW = "New % Split"


def _ensure_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(r"[$,() ]", "", regex=True)
        .str.replace(r"^-$", "0", regex=True),
        errors="coerce",
    )


def load_govdeals_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="latin1", low_memory=False)


    df[COL_FY] = pd.to_numeric(df[COL_FY], errors="coerce")
    df[COL_SOLD_AMT] = _ensure_numeric(df[COL_SOLD_AMT])
    df[COL_NET] = _ensure_numeric(df[COL_NET])
    df[COL_VISITORS] = _ensure_numeric(df[COL_VISITORS])

    return df



def _barh(series: pd.Series, title: str, xlabel: str, outpath: Path, money: bool = False) -> None:
    s = series.sort_values(ascending=True)

    plt.figure(figsize=(10, 6))
    plt.barh(s.index.astype(str), s.values)
    plt.title(title)
    plt.xlabel(xlabel)

    if money:
        ax = plt.gca()
        ax.xaxis.set_major_formatter(lambda x, pos: f"${x:,.0f}")

    plt.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outpath, dpi=200)
    plt.close()


def top10_gross_sales_items(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    s = df.groupby(COL_ITEM)[COL_SOLD_AMT].sum().sort_values(ascending=False).head(10)
    table = s.reset_index().rename(columns={COL_SOLD_AMT: "Sum of Sold Amount"})
    return table, s


def top10_no_bid_items_by_visitors(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    # “No bid / unsold” items
    mask = df[COL_STATUS].astype(str).str.contains("unsold|no bid", case=False, na=False)
    s = df.loc[mask].groupby(COL_ITEM)[COL_VISITORS].sum().sort_values(ascending=False).head(10)
    table = s.reset_index().rename(columns={COL_VISITORS: "Sum of Visitors"})
    return table, s


def top10_categories_net_results(df: pd.DataFrame, years: Iterable[int]) -> Tuple[pd.DataFrame, pd.Series]:
    sub = df[df[COL_FY].isin(list(years))].copy()
    s = sub.groupby(COL_CATEGORY)[COL_NET].sum().sort_values(ascending=False).head(10)
    table = s.reset_index().rename(columns={COL_NET: "Sum of Net Results"})
    return table, s


def items_needed_to_reach_overhead(df: pd.DataFrame, overhead: float, years: Iterable[int]) -> pd.DataFrame:
    sub = df[df[COL_FY].isin(list(years))].copy()

    rows = []
    for y, g in sub.groupby(COL_FY):
        total_net = g[COL_NET].sum(skipna=True)
        items_listed = len(g)
        avg_net = total_net / items_listed if items_listed else np.nan
        needed = overhead / avg_net if avg_net and avg_net > 0 else np.nan

        rows.append(
            {
                "Fiscal Year": int(y) if pd.notna(y) else y,
                "Items Listed": items_listed,
                "Total Net Results": total_net,
                "Avg Net / Item": avg_net,
                "Items Needed for Overhead": needed,
            }
        )

    return pd.DataFrame(rows).sort_values("Fiscal Year")


def _pct_to_float(x: str) -> float:
    s = str(x).strip()
    if not s or s.lower() in {"nan", "none"}:
        return 1.0
    if "%" in s:
        return float(s.replace("%", "").strip()) / 100.0
    # fallback: already numeric-like
    try:
        return float(s)
    except ValueError:
        return 1.0


def split_comparison_by_year(df: pd.DataFrame) -> pd.DataFrame:
    # Interpret "% Split" columns like "80%" => 0.8
    out = df.copy()
    out["_old_pct"] = out[COL_SPLIT_OLD].map(_pct_to_float)
    out["_new_pct"] = out[COL_SPLIT_NEW].map(_pct_to_float)

    out["_old_net"] = out[COL_NET] * out["_old_pct"]
    out["_new_net"] = out[COL_NET] * out["_new_pct"]

    yearly = (
        out.groupby(COL_FY)[["_old_net", "_new_net"]]
        .sum()
        .reset_index()
        .rename(columns={"_old_net": "Original Split Net Total", "_new_net": "New Split Net Total"})
        .sort_values(COL_FY)
    )
    yearly["Percent Change"] = (yearly["New Split Net Total"] - yearly["Original Split Net Total"]) / yearly["Original Split Net Total"]
    return yearly


def build_outputs(
    csv_path: Path,
    output_dir: Path,
    years_for_report=(2022, 2023, 2024),
    overhead: float = 240_000.0,
) -> None:
    df = load_govdeals_csv(csv_path)

    (output_dir / "tables").mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)

    # Top 10 Gross Sales Items
    gross_table, gross_series = top10_gross_sales_items(df)
    gross_table.to_csv(output_dir / "tables" / "top10_gross_sales_items.csv", index=False)
    _barh(
        gross_series,
        title=f"Top 10 Gross Sales Items FY {years_for_report[0]}-{str(years_for_report[-1])[-2:]}",
        xlabel="Sum of Sold Amount",
        outpath=output_dir / "figures" / "top10_gross_sales_items.png",
        money=True,
    )

    # Top 10 No Bid Items
    nobid_table, nobid_series = top10_no_bid_items_by_visitors(df)
    nobid_table.to_csv(output_dir / "tables" / "top10_no_bid_items_visitors.csv", index=False)
    _barh(
        nobid_series,
        title="Top 10 No Bid Items (Visitors)",
        xlabel="Sum of Visitors",
        outpath=output_dir / "figures" / "top10_no_bid_items_visitors.png",
        money=False,
    )

    # Top 10 Categories
    cat_table, cat_series = top10_categories_net_results(df, years_for_report)
    cat_table.to_csv(output_dir / "tables" / "top10_categories_net_results.csv", index=False)
    _barh(
        cat_series,
        title=f"Highest Net Sales Categories {years_for_report[0]}-{str(years_for_report[-1])[-2:]}",
        xlabel="Sum of Net Results",
        outpath=output_dir / "figures" / "top10_categories_net_results.png",
        money=True,
    )

    # Items needed for overhead
    overhead_table = items_needed_to_reach_overhead(df, overhead=overhead, years=years_for_report)
    overhead_table.to_csv(output_dir / "tables" / "items_needed_for_overhead.csv", index=False)

    # Split comparison
    split_tbl = split_comparison_by_year(df)
    split_tbl.to_csv(output_dir / "tables" / "split_comparison_by_year.csv", index=False)

    # Plot split comparison (Original vs New)
    plt.figure(figsize=(9, 5))
    x = split_tbl[COL_FY].astype(int)

    plt.bar(x - 0.15, split_tbl["Original Split Net Total"].fillna(0), width=0.3, label="Original")
    plt.bar(x + 0.15, split_tbl["New Split Net Total"].fillna(0), width=0.3, label="New")

    plt.title("Change in Net Sales (Split Scenario)")
    plt.xlabel("Fiscal Year")
    plt.ylabel("Net Sales")
    plt.gca().yaxis.set_major_formatter(lambda v, p: f"${v:,.0f}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "split_comparison.png", dpi=200)
    plt.close()
