# Python reproduction and cross-check

`retail_analysis.py` rebuilds the Excel model independently in pandas and extends it with RFM segmentation, cohort retention and return-rate analysis.

Its first job is verification. The Excel dashboard and this script start from the same raw file and share no code, so if their headline figures agree, both are probably right; if they disagree, one of them is wrong and the difference says where to look. Building a model and then checking it against an independent implementation is the difference between a number you believe and a number you can defend.

## Running it

```bash
pip install pandas openpyxl
python retail_analysis.py ../data/online_retail_II.xlsx
```

Writes `retail_analysis_output.xlsx` beside the script. It reads the source file and writes nothing else.

> **Do not point this, or any other script, at the Excel model workbook.** Power Query queries, the Power Pivot model and the DAX measures live in XML parts that openpyxl does not understand. Opening that workbook in Python and saving it strips the data model out, and the loss is not recoverable.

## What it produces

| Sheet | Contents |
|---|---|
| **Headline** | Gross sales, returns, net sales, return rate, orders, AOV, customer and product counts — the figures to check against the dashboard |
| **Data Quality** | The twelve checks: row counts, duplicates removed, date range, blank customer IDs, cancellations, non-product lines, negative quantities, StockCodes carrying more than one description |
| **Top Customers** / **Top Products** | Top ten by net sales with share of total — the 16.3% against 7.6% concentration contrast |
| **RFM Segments** | Customers, net sales, averages and share by segment |
| **RFM Customers** | Per-customer recency, frequency, monetary, 1–5 scores, RFM code and segment |
| **Cohort Retention %** | Share of each first-purchase cohort still buying, by months since acquisition |
| **Cohort Counts** | The underlying customer counts behind those percentages |
| **Returns by Country** / **Returns by Product** | Gross, returns and return rate, filtered to a $1,000 minimum so tiny denominators do not dominate |

## Method notes

**The cleaning mirrors Power Query, in the same order.** Append both sheets, trim and type, remove fully duplicated rows, then add flags rather than filter. `Invoice` and `StockCode` stay text: cancellations carry a `C` prefix and StockCodes carry letter suffixes, and typing either as a number silently loses those rows.

**Cancellations and non-product lines are flagged, never deleted.** That keeps revenue reconcilable to the raw file and keeps the return rate measurable. Deleting them is the obvious first instinct with this dataset and it destroys the return analysis permanently.

**Recency scoring is reversed.** A low recency means a recent purchase, which is good, so it scores 5. Frequency and monetary run the other way. Inverting this is the most common RFM error and it produces output that looks entirely plausible.

**Monetary is net of returns**, so a customer who sent most of their order back scores low. Frequency and last-purchase date exclude cancellations, so a return does not count as a visit.

**Products group by `StockCode`, never `Description`.** One StockCode in this dataset carries three different descriptions; grouped by description it splits into three mid-sized rows, grouped by its key it totals $180,512.

**Segment boundaries are quintiles of this dataset**, not fixed industry thresholds. They describe where a customer sits relative to this customer base, and are not comparable to RFM scores computed elsewhere.

## Known limits

- December 2011 is a partial month; the data ends on 9 December. Any final-period figure is understated.
- Roughly a fifth of rows carry no Customer ID. They are kept in revenue totals and excluded from all customer-level analysis, so the two will not tie.
- Cohort retention counts a customer as retained if they placed any order in that month. It does not weight by value.
