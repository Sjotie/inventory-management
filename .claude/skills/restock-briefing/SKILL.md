---
name: restock-briefing
description: Write a short purchasing briefing: what to reorder now, within a given budget, and why, ready for a buyer or operations manager to approve. Use when someone asks what to order, how to spend a restocking budget, which items are at risk of running out, or wants the weekly reorder memo.
---

# Restock briefing

The reader is a buyer or operations manager who has a few minutes and a budget to approve. They need to decide, not to analyse. Produce a one-page briefing (Markdown, or the format they ask for) with:

1. **The recommendation in one line**: spend X of budget Y on N items, earliest full delivery date.
2. **The order list**: item, quantity, cost, lead time, and the reason in a few words ("demand up 50%, 2 weeks of stock left"). Most urgent first.
3. **What was left out and why**: items that need ordering but did not fit the budget, and items bought only partly (the endpoint fills the last slot with a partial quantity), with what it would cost to include them. This is often the most useful part for the reader; it tells them whether to ask for more budget.
4. **Risks worth a sentence**: open backlog that these orders do or don't cover, items already below reorder point, long lead times.

If they did not give a budget, ask once; if they want a quick answer, show the result for two or three budgets side by side.

## How to get there

`/api/restocking/recommendations?budget=` does the ranking and the budget fill; its logic is in `server/main.py` (`recommend_restock`). Use it as the starting point and add the context it lacks: current stock and reorder points from `/api/inventory`, and shortages from `/api/backlog`. The data sources, definitions and quirks are in [`../explain-the-numbers/references/data-map.md`](../explain-the-numbers/references/data-map.md); read it first. The quirk that matters most here: few forecast SKUs exist in inventory, so "stock left" is unknown for most recommended items. Say that rather than guessing.

Do not place the order (`POST /api/restocking/orders`) unless the person explicitly approves the briefing. Placing it changes what everyone sees on the Orders tab.

## Quality bar

- Every number in the briefing can be traced to an endpoint call; list the calls at the bottom in a small "Sources" line.
- Totals add up: the order list sums to the spend in line one, and spend never exceeds budget.
- Plain language. No SKUs without the item name, no field names, no JSON.
