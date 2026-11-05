---
name: explain-the-numbers
description: Answer a business question about this factory's inventory, orders, spending or demand with numbers traced to the source records. Use when someone asks "why is X up", "which warehouse/category/customer...", "how much did we...", "is this number right", or wants a figure from the dashboard explained in plain language.
---

# Explain the numbers

The person asking is an operations manager, buyer or controller, not a developer. They want an answer they can repeat in a meeting and defend when someone asks "where does that come from?". So the deliverable is:

1. **The answer first**, in one or two sentences, in their words (no field names, no JSON).
2. **The numbers behind it**, each with where it came from (endpoint or file, and the filter used) so anyone can reproduce it.
3. **What the data can't tell them**, when that matters for the question: missing months, mock-data quirks, a filter that silently does nothing. An answer that hides a gap is worse than one that names it.

## Where the data lives

Read [`references/data-map.md`](references/data-map.md) before you compute anything. It lists every source, what each one covers, and the quirks that produce plausible but wrong answers (for example: spending endpoints ignore the dashboard filters, and transactions use warehouse letters, not city names).

Use the running API (`http://localhost:8001`) when it is up, because that is what the dashboard shows and the person will compare against it. Otherwise read `server/data/*.json` directly and apply the same logic as `server/main.py`.

## Quality bar

- Before you report a total, look at a handful of the records it is made of. A sum over the wrong set looks just as reasonable as the right one.
- If your number differs from what the dashboard shows, find out why before you answer. Usually it is a filter, a month format or a status definition; say which.
- Round for the reader (`$1.2M`, `about 1 in 5 orders`) and keep the exact figure in the sources line.
- If the question is ambiguous ("last quarter", "late orders"), pick the most likely reading, state it in one line, and offer the other.
