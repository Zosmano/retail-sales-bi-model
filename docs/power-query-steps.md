# Power Query transformation steps

The sequence below is the applied-steps order in the `Sales_All` query. Each step is listed with what it does and why it is there.

---

## 1. Load the two source sheets

The workbook ships the data as two worksheets, one per year range:

| Query | Source sheet | Load destination |
|---|---|---|
| `Year 2009-2010` | 2009–2010 | Connection only |
| `Year 2010-2011` | 2010–2011 | Connection only |
| `Sales_All` | append of the two above | Data Model |

Both source queries are set to **Connection Only**. Only `Sales_All` loads to the Data Model. Loading all three to worksheets would triple the file size for no benefit, and a worksheet cannot hold 1,067,371 rows alongside the other two anyway.

> **If a source query disappears** after you delete its worksheet, rebuild it with **Get Data → Blank Query → Advanced Editor** and paste the M back in. Deleting the worksheet deletes the query with it.

---

## 2. Append

`Table.Combine` on the two source queries. Result: **1,067,371 rows**.

Verify the count here before going further. If the append returns a handful of rows, a `Counted Rows` step is still sitting at the end of the applied-steps list from an earlier row count — delete it.

---

## 3. Set data types

| Column | Type |
|---|---|
| Invoice | Text |
| StockCode | Text |
| Description | Text |
| Quantity | Whole Number |
| InvoiceDate | Date/Time |
| Price | Decimal Number |
| Customer ID | Whole Number |
| Country | Text |

`Invoice` and `StockCode` must be **Text**, not number. Cancellation invoices are prefixed `C`, and many StockCodes carry letter suffixes (`85099B`). Typing either as a number silently drops those rows or strips the suffix.

---

## 4. Trim and clean text columns

`Text.Trim` and `Text.Clean` on `Description`, `StockCode` and `Country`. Leading and trailing whitespace is the most common cause of a single product splitting into several rows in a PivotTable.

---

## 5. Remove duplicates

`Table.Distinct` across all columns. **34,335 rows removed.**

Applied across the full row, not a subset of columns, so only genuinely identical invoice lines are dropped.

---

## 6. Add flag columns

Two custom columns, both kept as flags rather than used to filter rows:

```m
// IsCancellation — cancellation invoices are prefixed with "C"
if Text.StartsWith([Invoice], "C") then 1 else 0
```

```m
// IsProduct — exclude postage, fees, adjustments and other non-product lines
if List.Contains(
      {"POST","DOT","M","BANK CHARGES","AMAZONFEE","C2","D","S","CRUK","PADS","B","TEST001","TEST002"},
      Text.Upper([StockCode]))
   then 0 else 1
```

Flagging rather than filtering is deliberate. It keeps the model reconcilable to source: total revenue in the model still ties back to the raw file, and the measure layer decides what to include.

---

## 7. Add a line-revenue column

```m
[Quantity] * [Price]
```

Computed in Power Query rather than DAX so the fact table carries it, and so the row-level value can be checked directly against the source.

---

## 8. Load to the Data Model

`Sales_All` loads to the Data Model only, not to a worksheet.

---

## Calendar table

A separate `Calendar` query provides the date dimension:

- A continuous date range covering the full `InvoiceDate` span
- `Year`, `Month` (name), `MonthNum`, `Quarter`, `YearMonth`
- Loaded to the Data Model
- **Marked as a Date Table** in Power Pivot — without this, the time-intelligence measures return wrong results rather than errors
- `Month` is set to **Sort by Column → MonthNum**, otherwise months sort alphabetically and every chart reads April, August, December

---

## Common failures and their causes

| Symptom | Cause |
|---|---|
| Query returns 1 row | A `Counted Rows` step left at the end of the applied steps |
| "Download failed" / model will not save | Workbook is open read-only; Save As a new editable file |
| Source query vanished | Its worksheet was deleted; rebuild via Blank Query + Advanced Editor |
| Months sort alphabetically | `Month` has no Sort by Column set |
| Time intelligence returns blanks or nonsense | Calendar not marked as a Date Table |
