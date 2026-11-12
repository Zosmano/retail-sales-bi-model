# DAX measure layer

All measures sit in the `Sales_All` table. Where a measure already filters internally, **do not** apply the same filter again in the PivotTable — doing so double-filters and produces wrong results (see Pitfalls at the end).

---

## Base revenue measures

```dax
Gross Sales :=
CALCULATE (
    SUMX ( Sales_All, Sales_All[Quantity] * Sales_All[Price] ),
    Sales_All[IsCancellation] = 0,
    Sales_All[IsProduct] = 1
)
```
Product sales before returns. Cancellations excluded, non-product lines excluded.

```dax
Returns :=
ABS (
    CALCULATE (
        SUMX ( Sales_All, Sales_All[Quantity] * Sales_All[Price] ),
        Sales_All[IsCancellation] = 1,
        Sales_All[IsProduct] = 1
    )
)
```
Returned value as a positive number, so it reads naturally in a chart.

```dax
Net Sales := [Gross Sales] - [Returns]
```

```dax
Return Rate % :=
DIVIDE ( [Returns], [Gross Sales] )
```

---

## Volume and customer measures

```dax
Total Quantity :=
CALCULATE (
    SUM ( Sales_All[Quantity] ),
    Sales_All[IsCancellation] = 0,
    Sales_All[IsProduct] = 1
)
```

```dax
Order Count :=
CALCULATE (
    DISTINCTCOUNT ( Sales_All[Invoice] ),
    Sales_All[IsCancellation] = 0
)
```

```dax
Customer Count :=
DISTINCTCOUNT ( Sales_All[Customer ID] )
```

```dax
Average Order Value :=
DIVIDE ( [Net Sales], [Order Count] )
```

---

## Concentration measures

These are the two that matter most to the findings, and the two easiest to get wrong.

```dax
Customer Share % :=
DIVIDE (
    [Net Sales],
    CALCULATE ( [Net Sales], ALL ( Sales_All[Customer ID] ) )
)
```

```dax
Product Share % :=
DIVIDE (
    [Net Sales],
    CALCULATE ( [Net Sales], ALL ( Sales_All[StockCode] ) )
)
```

**The column inside `ALL()` must match the column on the rows.** A customer-share measure removes the filter on `Customer ID`; a product-share measure removes it on `StockCode`. Use the customer version on a product breakdown and every row returns 100% — plausible-looking output, completely wrong.

**Group products by `StockCode`, never by `Description`.** StockCode `85099B` carries three different descriptions in the source. Grouped by description it splits into three mid-sized rows; grouped by StockCode it totals **$180,512**.

---

## Time intelligence

Requires the `Calendar` table to be **marked as a Date Table**.

```dax
Net Sales LY :=
CALCULATE ( [Net Sales], SAMEPERIODLASTYEAR ( 'Calendar'[Date] ) )
```

```dax
YoY Growth % :=
DIVIDE ( [Net Sales] - [Net Sales LY], [Net Sales LY] )
```

```dax
Net Sales YTD :=
TOTALYTD ( [Net Sales], 'Calendar'[Date] )
```

---

## Pitfalls

**Gross Sales equal to Net Sales.** The `IsCancellation` or `IsProduct` filters were also applied as report filters in the PivotTable, on top of measures that already filter. Remove them from the PivotTable; the measures handle it.

**Every share row shows 100%.** Wrong column inside `ALL()`. See above.

**Excel rejects a pasted measure with "Add an equal sign".** A hidden character came in with the paste. Retype the formula by hand.

**Time intelligence returns blanks.** The Calendar table is not marked as a Date Table, or the relationship to `Sales_All[InvoiceDate]` is missing or inactive.

**Months out of order.** `Calendar[Month]` needs Sort by Column set to `MonthNum`.
