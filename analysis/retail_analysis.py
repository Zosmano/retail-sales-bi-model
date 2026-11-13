"""
Retail Sales BI Model — independent Python reproduction.

Reproduces the Excel Power Query / Power Pivot model from the raw source file and
extends it with RFM segmentation, cohort retention and return-rate analysis.

Its second job is to act as a cross-check: the headline figures printed to the
console should match the Excel dashboard. If they do not, one of the two is wrong.

Usage
-----
    python retail_analysis.py ../data/online_retail_II.xlsx

Writes `retail_analysis_output.xlsx` next to this script, with one sheet per
analysis. Does NOT touch the source file, and does NOT touch the Excel model
workbook — opening that with openpyxl would strip its Power Pivot data model.

Requires: pandas, openpyxl
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# StockCodes that carry revenue but are not product lines: postage, carriage,
# manual adjustments, bank charges, samples and test rows.
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE", "C2", "D", "S",
    "CRUK", "PADS", "B", "TEST001", "TEST002",
}

SHEETS = ["Year 2009-2010", "Year 2010-2011"]


# ----------------------------------------------------------------------------
# Load and clean — mirrors the Power Query applied steps, in the same order
# ----------------------------------------------------------------------------

def load_raw(path: Path) -> pd.DataFrame:
    """Append both source sheets. Mirrors the Sales_All append step."""
    frames = []
    book = pd.ExcelFile(path)
    sheets = [s for s in SHEETS if s in book.sheet_names] or book.sheet_names
    for sheet in sheets:
        df = book.parse(sheet)
        df["SourceSheet"] = sheet
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    raw.columns = [str(c).strip() for c in raw.columns]
    return raw


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Type, trim, de-duplicate and flag. Returns the frame and a step log."""
    log = {"rows_raw": len(raw)}

    df = raw.copy()

    # Invoice and StockCode stay text: cancellations are prefixed "C" and many
    # StockCodes carry letter suffixes (85099B). Typing either as a number
    # silently drops those rows.
    for col in ("Invoice", "StockCode", "Description", "Country"):
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Customer ID"] = pd.to_numeric(df["Customer ID"], errors="coerce")

    # Remove fully duplicated invoice lines, across every source column.
    before = len(df)
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "SourceSheet"])
    log["duplicates_removed"] = before - len(df)

    # Flags, not filters: keeps the model reconcilable to source.
    df["IsCancellation"] = df["Invoice"].str.upper().str.startswith("C").fillna(False)
    df["IsProduct"] = ~df["StockCode"].str.upper().isin(NON_PRODUCT_CODES)
    df["HasCustomer"] = df["Customer ID"].notna()
    df["LineRevenue"] = df["Quantity"] * df["Price"]

    log["rows_clean"] = len(df)
    log["date_min"] = df["InvoiceDate"].min()
    log["date_max"] = df["InvoiceDate"].max()
    return df, log


# ----------------------------------------------------------------------------
# Headline measures — these must match the Excel dashboard
# ----------------------------------------------------------------------------

def headline(df: pd.DataFrame) -> pd.DataFrame:
    prod = df[df["IsProduct"]]
    gross = prod.loc[~prod["IsCancellation"], "LineRevenue"].sum()
    returns = abs(prod.loc[prod["IsCancellation"], "LineRevenue"].sum())
    net = gross - returns
    orders = prod.loc[~prod["IsCancellation"], "Invoice"].nunique()

    return pd.DataFrame(
        [
            ("Gross Sales", gross),
            ("Returns", returns),
            ("Net Sales", net),
            ("Return Rate %", returns / gross * 100 if gross else np.nan),
            ("Orders", orders),
            ("Average Order Value", gross / orders if orders else np.nan),
            ("Customers (identified)", df.loc[df["HasCustomer"], "Customer ID"].nunique()),
            ("Products (StockCodes)", prod["StockCode"].nunique()),
        ],
        columns=["Measure", "Value"],
    )


def concentration(df: pd.DataFrame, by: str, top: int = 10) -> pd.DataFrame:
    """Top-N share of net sales. Products group by StockCode, never Description."""
    prod = df[df["IsProduct"]]
    if by == "Customer ID":
        prod = prod[prod["HasCustomer"]]

    net = prod.groupby(by, observed=True)["LineRevenue"].sum().sort_values(ascending=False)
    total = net.sum()
    head = net.head(top).rename("Net Sales").to_frame()
    head["Share %"] = head["Net Sales"] / total * 100
    head.loc["TOP %d TOTAL" % top] = [head["Net Sales"].sum(), head["Share %"].sum()]
    return head.reset_index(names=by)


# ----------------------------------------------------------------------------
# RFM segmentation
# ----------------------------------------------------------------------------

SEGMENT_RULES = [
    (lambda r, f: r >= 4 and f >= 4, "Champions"),
    (lambda r, f: r >= 3 and f >= 3, "Loyal"),
    (lambda r, f: r >= 4 and f <= 2, "New / Promising"),
    (lambda r, f: r == 3 and f <= 2, "Potential"),
    (lambda r, f: r <= 2 and f >= 4, "At Risk"),
    (lambda r, f: r <= 2 and f == 3, "Needs Attention"),
    (lambda r, f: r == 1 and f <= 2, "Lost"),
]


def label(r: int, f: int) -> str:
    for test, name in SEGMENT_RULES:
        if test(r, f):
            return name
    return "Other"


def quintile(series: pd.Series, ascending_is_good: bool) -> pd.Series:
    """Score 1-5 by quintile. Recency is reversed: a low value is a good one."""
    ranks = series.rank(method="first", pct=True)
    score = np.ceil(ranks * 5).clip(1, 5).astype(int)
    return 6 - score if ascending_is_good else score


def rfm(df: pd.DataFrame) -> pd.DataFrame:
    prod = df[df["IsProduct"] & df["HasCustomer"]]
    ref_date = prod["InvoiceDate"].max()

    purchases = prod[~prod["IsCancellation"]]
    agg = purchases.groupby("Customer ID", observed=True).agg(
        FirstPurchase=("InvoiceDate", "min"),
        LastPurchase=("InvoiceDate", "max"),
        Frequency=("Invoice", "nunique"),
    )
    # Monetary is net of returns: a customer who sent most of it back is worth less.
    agg["Monetary"] = prod.groupby("Customer ID", observed=True)["LineRevenue"].sum()
    agg["Recency"] = (ref_date - agg["LastPurchase"]).dt.days

    agg = agg[(agg["Frequency"] > 0) & (agg["Monetary"] > 0)].copy()

    agg["R"] = quintile(agg["Recency"], ascending_is_good=True)
    agg["F"] = quintile(agg["Frequency"], ascending_is_good=False)
    agg["M"] = quintile(agg["Monetary"], ascending_is_good=False)
    agg["RFM Score"] = agg["R"].astype(str) + agg["F"].astype(str) + agg["M"].astype(str)
    agg["Segment"] = [label(r, f) for r, f in zip(agg["R"], agg["F"])]

    return agg.reset_index()


def segment_summary(rfm_df: pd.DataFrame) -> pd.DataFrame:
    out = rfm_df.groupby("Segment", observed=True).agg(
        Customers=("Customer ID", "count"),
        Net_Sales=("Monetary", "sum"),
        Avg_Recency_Days=("Recency", "mean"),
        Avg_Frequency=("Frequency", "mean"),
        Avg_Monetary=("Monetary", "mean"),
    )
    out["Customer Share %"] = out["Customers"] / out["Customers"].sum() * 100
    out["Revenue Share %"] = out["Net_Sales"] / out["Net_Sales"].sum() * 100
    return out.sort_values("Net_Sales", ascending=False).round(1).reset_index()


# ----------------------------------------------------------------------------
# Cohort retention
# ----------------------------------------------------------------------------

def cohorts(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retention by first-purchase month, measured in months since acquisition."""
    prod = df[df["IsProduct"] & df["HasCustomer"] & ~df["IsCancellation"]].copy()
    prod["OrderMonth"] = prod["InvoiceDate"].dt.to_period("M")
    prod["Cohort"] = prod.groupby("Customer ID", observed=True)["InvoiceDate"].transform("min").dt.to_period("M")
    prod["MonthIndex"] = (
        (prod["OrderMonth"].dt.year - prod["Cohort"].dt.year) * 12
        + (prod["OrderMonth"].dt.month - prod["Cohort"].dt.month)
    )

    counts = (
        prod.groupby(["Cohort", "MonthIndex"], observed=True)["Customer ID"]
        .nunique()
        .unstack(fill_value=0)
    )
    sizes = counts[0].replace(0, np.nan)
    rates = counts.div(sizes, axis=0).mul(100).round(1)

    counts.index = counts.index.astype(str)
    rates.index = rates.index.astype(str)
    return counts.reset_index(), rates.reset_index()


# ----------------------------------------------------------------------------
# Return-rate analysis
# ----------------------------------------------------------------------------

def return_rates(df: pd.DataFrame, by: str, min_gross: float = 1000.0) -> pd.DataFrame:
    prod = df[df["IsProduct"]]
    gross = prod[~prod["IsCancellation"]].groupby(by, observed=True)["LineRevenue"].sum()
    rets = prod[prod["IsCancellation"]].groupby(by, observed=True)["LineRevenue"].sum().abs()

    out = pd.DataFrame({"Gross Sales": gross, "Returns": rets}).fillna(0)
    out = out[out["Gross Sales"] >= min_gross]
    out["Net Sales"] = out["Gross Sales"] - out["Returns"]
    out["Return Rate %"] = (out["Returns"] / out["Gross Sales"] * 100).round(2)
    return out.sort_values("Return Rate %", ascending=False).reset_index()


# ----------------------------------------------------------------------------
# Data-quality checks
# ----------------------------------------------------------------------------

def quality_checks(df: pd.DataFrame, log: dict) -> pd.DataFrame:
    prod = df[df["IsProduct"]]
    multi_desc = (
        df.groupby("StockCode", observed=True)["Description"].nunique().pipe(lambda s: s[s > 1])
    )
    checks = [
        ("Rows loaded from source", log["rows_raw"], ""),
        ("Fully duplicated rows removed", log["duplicates_removed"], ""),
        ("Rows after cleaning", log["rows_clean"], ""),
        ("Date range start", log["date_min"], ""),
        ("Date range end", log["date_max"], "December is a partial month"),
        ("Rows with no Customer ID", int((~df["HasCustomer"]).sum()),
         "Retained; excluded from customer analysis only"),
        ("Cancellation rows", int(df["IsCancellation"].sum()), "Flagged, not deleted"),
        ("Non-product rows", int((~df["IsProduct"]).sum()), "Postage, fees, adjustments"),
        ("Negative-quantity rows", int((df["Quantity"] < 0).sum()), "Expected: cancellations"),
        ("Zero or negative price rows", int((df["Price"] <= 0).sum()), "Inspect before trusting"),
        ("StockCodes with >1 Description", int(len(multi_desc)),
         "Group by StockCode, never Description"),
        ("Distinct StockCodes (products)", prod["StockCode"].nunique(), ""),
    ]
    return pd.DataFrame(checks, columns=["Check", "Value", "Note"]).fillna("")


# ----------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1

    src = Path(argv[1]).expanduser().resolve()
    if not src.exists():
        print(f"Source file not found: {src}")
        return 1

    print(f"Reading {src.name} ...")
    raw = load_raw(src)
    df, log = clean(raw)

    print(f"  {log['rows_raw']:,} rows loaded, "
          f"{log['duplicates_removed']:,} duplicates removed, "
          f"{log['rows_clean']:,} retained")

    head = headline(df)
    print("\nHeadline measures — compare these against the Excel dashboard:")
    for _, row in head.iterrows():
        val = float(row["Value"])
        fmt = f"{val:,.0f}" if float(val).is_integer() else f"{val:,.2f}"
        print(f"  {row['Measure']:<28} {fmt}")

    cust_conc = concentration(df, "Customer ID")
    prod_conc = concentration(df, "StockCode")
    rfm_df = rfm(df)
    seg = segment_summary(rfm_df)
    coh_counts, coh_rates = cohorts(df)
    ret_country = return_rates(df, "Country")
    ret_product = return_rates(df, "StockCode").head(40)
    checks = quality_checks(df, log)

    print(f"\nRFM: {len(rfm_df):,} identified customers scored into {rfm_df['Segment'].nunique()} segments")
    print(seg[["Segment", "Customers", "Revenue Share %"]].to_string(index=False))

    out_path = Path(__file__).resolve().parent / "retail_analysis_output.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as xl:
        head.to_excel(xl, sheet_name="Headline", index=False)
        checks.to_excel(xl, sheet_name="Data Quality", index=False)
        cust_conc.to_excel(xl, sheet_name="Top Customers", index=False)
        prod_conc.to_excel(xl, sheet_name="Top Products", index=False)
        seg.to_excel(xl, sheet_name="RFM Segments", index=False)
        rfm_df.to_excel(xl, sheet_name="RFM Customers", index=False)
        coh_rates.to_excel(xl, sheet_name="Cohort Retention %", index=False)
        coh_counts.to_excel(xl, sheet_name="Cohort Counts", index=False)
        ret_country.to_excel(xl, sheet_name="Returns by Country", index=False)
        ret_product.to_excel(xl, sheet_name="Returns by Product", index=False)

    print(f"\nWritten: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
