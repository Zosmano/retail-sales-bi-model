# Findings

All figures are net of returns and exclude non-product lines, unless stated otherwise.

---

## 1. Revenue is concentrated in customers, not products

| Grouping | Net sales, top 10 | Share of total |
|---|---|---|
| Customers | $2,660,068 | **16.3%** |
| Products | $1,443,504 | **7.6%** |

For scale: total net sales across the period are **$18,926,266** on **44,715** orders, an average order value of **$439**.

The single largest customer (`18102`) accounts for **3.5%** of net sales on their own. The single largest product (`22423`) reaches only **1.7%**.

Ten customers out of thousands carry roughly a sixth of net sales. Ten products out of several thousand carry well under a tenth.

These point in opposite commercial directions. The customer base has a short head, so losing a handful of accounts is a material revenue event and retention effort has an obvious target. The assortment has a long tail, so revenue does not depend on a few hero products, and pruning the range on revenue rank alone would remove breadth that customers may be buying across.

---

## 2. One product was hiding as three

StockCode `85099B` appears in the source data under three different `Description` values.

Grouped by `Description`, each fragment looks like an unremarkable mid-tier line. Grouped by `StockCode` — the actual product key — it totals **$180,512**.

Any assortment or purchasing decision taken from a description-level view would have understated this product by roughly two thirds. The general lesson sits in the data dictionary now: **`StockCode` is the key, `Description` is a label.**

---

## 3. Returns and cancellations are structural, not noise

Cancellations are a standing feature of this business, not an anomaly to be cleaned away. Modelling them as a flag rather than deleting them makes three things measurable that would otherwise be invisible:

- Gross Sales, Returns and Net Sales as separate quantities
- Return rate as a ratio, sliceable by product, customer and country
- A revenue total that still reconciles to the raw source file

Deleting cancellation rows is the obvious first instinct with this dataset. It also destroys the return-rate analysis permanently and silently.

---

## 4. Non-product revenue needed separating

Postage, carriage, manual adjustments, bank charges and test rows all carry revenue but are not assortment. Mixed into a product analysis they distort rankings; deleted outright they break reconciliation to source.

Flagging them resolved both: product analysis filters them out through the measure layer, while total revenue still ties back to the raw file.

---

## Still to come

These findings cover the first phase. Planned next:

- RFM segmentation of the customer base
- Cohort retention by first-purchase month
- Return rate by product and by country
- Basket analysis on co-purchased StockCodes
- A SQL reproduction of the core measures as an independent cross-check
