# Data map

All data is mock data, loaded into memory at server start from `server/data/*.json` by `server/mock_data.py`. Endpoints and filters are defined in `server/main.py`; read it when this file and the code disagree, and fix this file.

## Sources

| Question about | Endpoint | File | Filters that work |
|---|---|---|---|
| Stock on hand, low stock, stock value | `/api/inventory` | `inventory.json` | warehouse, category (no month: stock has no time dimension) |
| Customer orders, revenue, delivery | `/api/orders` | `orders.json` | warehouse, category, status, month |
| Dashboard KPIs | `/api/dashboard/summary` | derived | all four |
| Demand outlook | `/api/demand` | `demand_forecasts.json` | none |
| Items short for open orders | `/api/backlog` | `backlog_items.json` + `purchase_orders.json` | none |
| Costs by type, month, category | `/api/spending/summary`, `/monthly`, `/categories` | `spending.json` | **none**: static yearly figures |
| Individual cost lines | `/api/spending/transactions` | `transactions.json` | none |
| What to reorder within a budget | `/api/restocking/recommendations?budget=` | derived from forecasts | budget |
| Quarterly and monthly order reports | `/api/reports/quarterly`, `/monthly-trends` | derived from orders | the global filters |

## Definitions the dashboard uses

- **Low stock**: `quantity_on_hand <= reorder_point` (equal counts as low).
- **Pending orders**: status `Processing` or `Backordered`. `Shipped` is not pending.
- **Inventory value**: `quantity_on_hand * unit_cost`, summed.
- **Order value**: `total_value` on the order, not recomputed from line items.
- **Month filter**: `YYYY-MM` (substring match on `order_date`) or a quarter as `Q1-2025`; only the 2025 quarters exist in `QUARTER_MAP`, and any other `Q...` value (such as `Q1-2026` or `Q1`) is silently ignored: you get every order, unfiltered. See `filter_by_month` in `server/main.py`.

## Quirks that produce wrong answers

Check these against the files when you rely on them; mock data gets regenerated.

- **Spending ignores filters.** "Spending in London" cannot be answered from `/api/spending/*`; say so instead of returning the global number.
- **Two warehouse vocabularies.** Inventory and orders use city names (San Francisco, London, Tokyo); transactions use letters (A, B, C). There is no mapping in the data; do not invent one.
- **Transactions cover one month only** (September 2025), while `spending.json` holds a full year. They will not add up to each other.
- **Order category is set per order, not per line item.** An order in category Sensors can contain a Compression Spring. Category answers describe the order's label, not what was physically in it.
- **Forecast SKUs mostly don't exist in inventory.** Only a small share of `demand_forecasts.json` SKUs appear in `inventory.json`, so "forecast vs stock" comparisons cover very few items. Count the overlap and report it.
- **Restocking orders live in memory** and disappear when the server restarts.
