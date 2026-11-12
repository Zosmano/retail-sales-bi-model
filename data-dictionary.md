# Data dictionary

## `Sales_All` — fact table

One row per invoice line. 1,067,371 rows loaded, 34,335 duplicates removed during transformation.

| Field | Type | Source | Meaning |
|---|---|---|---|
| `Invoice` | Text | Source | Invoice number. A `C` prefix marks a cancellation. Kept as text so the prefix survives. |
| `StockCode` | Text | Source | Product identifier. **The correct key for product grouping.** Some codes carry letter suffixes (`85099B`). |
| `Description` | Text | Source | Product name as entered. Inconsistent — one StockCode may carry several descriptions. Display only; never group by this. |
| `Quantity` | Whole Number | Source | Units on the line. Negative on cancellations. |
| `InvoiceDate` | Date/Time | Source | Timestamp of the invoice. Joins to `Calendar[Date]`. |
| `Price` | Decimal Number | Source | Unit price in GBP at time of sale. |
| `Customer ID` | Whole Number | Source | Customer identifier. Blank on a substantial share of rows — guest or unidentified transactions. |
| `Country` | Text | Source | Customer country. Predominantly United Kingdom. |
| `IsCancellation` | Whole Number | Derived | `1` where `Invoice` starts with `C`, else `0`. |
| `IsProduct` | Whole Number | Derived | `0` for postage, fees, adjustments and other non-product lines; `1` otherwise. |
| `LineRevenue` | Decimal Number | Derived | `Quantity * Price`. Negative on cancellations. |

### Non-product StockCodes

Flagged `IsProduct = 0`:

`POST`, `DOT`, `M`, `BANK CHARGES`, `AMAZONFEE`, `C2`, `D`, `S`, `CRUK`, `PADS`, `B`, `TEST001`, `TEST002`

These are postage, carriage, manual adjustments, bank charges, samples and test rows. They carry revenue but are not assortment, so product-level analysis excludes them while total revenue stays reconcilable to source.

---

## `Calendar` — date dimension

Continuous daily rows across the full `InvoiceDate` span. Marked as a **Date Table** in Power Pivot.

| Field | Type | Meaning |
|---|---|---|
| `Date` | Date | Primary key. Joins to `Sales_All[InvoiceDate]`. |
| `Year` | Whole Number | Calendar year |
| `Quarter` | Text | `Q1`–`Q4` |
| `Month` | Text | Month name. **Sort by Column → `MonthNum`.** |
| `MonthNum` | Whole Number | 1–12, sort key for `Month` |
| `YearMonth` | Text | `YYYY-MM`, for sorting across year boundaries |

---

## Relationships

| From | To | Cardinality | Direction |
|---|---|---|---|
| `Sales_All[InvoiceDate]` | `Calendar[Date]` | Many to one | Single |

A star schema with one fact table and one dimension. Deliberately simple: the complexity sits in the measure layer, not the model.

---

## Known data quality issues

| Issue | Handling |
|---|---|
| 34,335 fully duplicated rows | Removed in Power Query via `Table.Distinct` |
| One StockCode, multiple Descriptions (e.g. `85099B`) | Group by `StockCode`; `Description` is display only |
| Blank `Customer ID` on many rows | Retained. Excluded from customer-level analysis, included in revenue totals. |
| Negative quantities | Legitimate — these are cancellations, flagged rather than deleted |
| Non-product revenue lines | Flagged `IsProduct = 0` rather than deleted |
| Leading/trailing whitespace in text fields | Trimmed and cleaned in Power Query |
