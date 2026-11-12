# Data

The source data is **not committed to this repository**. It is publicly available and large, and committing it would add nothing.

## Obtaining the data

Download **Online Retail II** from the UCI Machine Learning Repository:

https://archive.ics.uci.edu/dataset/502/online+retail+ii

The download contains a single Excel workbook with two worksheets:

- `Year 2009-2010`
- `Year 2010-2011`

Place the file in this folder. The Power Query steps in [`../docs/power-query-steps.md`](../docs/power-query-steps.md) expect both sheets to be present.

## Expected shape

| | |
|---|---|
| Combined rows | 1,067,371 |
| Columns | Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country |
| Period | December 2009 – December 2011 |

If the append step does not return 1,067,371 rows, check that a `Counted Rows` step has not been left at the end of the applied-steps list.

## Citation

The dataset is provided by the UCI Machine Learning Repository under its own terms. Cite the original source if you use it.
