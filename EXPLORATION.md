# Payee Cleanup Tool — Exploration Notes

> Captured during a thinking-mode session. No code was written. This is a
> reference for the design space, not a commitment.

## Goal

Build a tool for the YNAB HTTP MCP that:

1. Analyzes the payee list to find probable duplicates.
2. Combines two signals — fuzzy name overlap and category overlap — into a
   per-pair confidence score.
3. Returns a report the user (or an LLM agent) can review and amend.
4. Merges above a user-set confidence threshold automatically; below that,
   asks for approval.

YNAB already auto-imports bank payee names; the goal is to surface the cases
its built-in matcher missed.

## Current state of the codebase

These findings ground the design:

- **No native YNAB merge endpoint.** The YNAB Python SDK exposes only
  `create_payee`, `get_payees`, `get_payee_by_id`, `update_payee` on
  payees. The merge primitive is `TransactionsApi.update_transactions`
  (bulk) — patch each source transaction's `payee_id` to the canonical
  payee's id. Once all transactions are reassigned, YNAB auto-hides the
  orphaned source payees.
- **Lean payee shape** (`schemas/payees.py`): `id`, `name`, `deleted`,
  `transfer_account_id`. Anything we want to score against (last used,
  transaction counts) lives in `full_details` for drill-in.
- **Closest precedent:** the `data://transactions/insights` resource
  (transaction-aggregate-resource capability). Same shape we want here:
  a parameterized read resource returning a structured aggregate.
- **No fuzzy library yet.** `pyproject.toml` dependencies are `dotenv`,
  `httpx`, `pydantic`, `ynab`, `fastmcp`. Adding `rapidfuzz` is the
  natural choice (MIT, fast, no compile pain). `difflib.SequenceMatcher`
  is the no-dep fallback.
- **Resource vs tool split:** resources (`data://…`) are read-only;
  tools are for actions. The cleanup flow fits as one analyzer
  resource + one merge tool.

## Proposed surfaces

```
                      ANALYZE                              MERGE
                (read-only resource)                  (action tool)

  ┌────────────────────────────┐              ┌──────────────────────────────┐
  │  data://payees/duplicates  │              │  tool: merge_payees          │
  │  ?threshold=…              │              │  - target_payee_id           │
  │  ?since_date=…             │              │  - source_payee_ids[]        │
  │  ?until_date=…             │   amend      │  - rename_target_to?         │
  │  ?include_transfers=false  │  ──────▶     │  - dry_run=true (default)    │
  │                            │  (user/LLM)  │                              │
  │  → PayeeDuplicateReport    │              │  → PayeeMergeResult          │
  └────────────────────────────┘              └──────────────────────────────┘
```

The analyze step returns a report. The user or agent amends it (drops a
group, swaps the canonical, force-splits). The merge tool takes the
amended list. Dry-run by default — matching the human-initiated,
non-100%-confident spirit of the feature.

## Scoring formula

Two signals the user specified, extended with two more we get for free:

```
                       name overlap (string distance)
                       ─────────────────────────────
   Payee A  ──────▶  jaro_winkler / token_sort_ratio   0–100
                       ─────────────────────────────
   Payee B  ──────▶  overlap_coefficient(cats_A, cats_B)
                       ────────────────────────────────
                          category overlap
                                │
                                ▼
                       ┌────────────────────┐
                       │ magnet_payee?      │  ← Amazon, Walmart, Google,
                       │ (Amazon etc.)      │     PayPal, Target, …
                       └────────────────────┘    lower category penalty

   Combined:
   ┌──────────────────────────────────────────────────────────────┐
   │ confidence = clamp(                                          │
   │     0.40 * name_score                                        │
   │   + 0.35 * category_score                                   │
   │   + 0.15 * account_score       ← bonus signal               │
   │   + 0.10 * volume_balance      ← equal-volume payees score  │
   │   + disjoint_penalty,                                       │
   │   0, 100                                                    │
   │ )                                                            │
   └──────────────────────────────────────────────────────────────┘
```

- **Account overlap** is free — `account_id` is on every transaction.
  Same account on both payees is corroborating evidence; disjoint
  accounts + weak name match is a quiet signal of "probably different."
- **Volume balance** prevents conflating a 50-txn payee with a
  2-txn payee. Asymmetric pairs score lower than symmetric ones.
- **Disjoint penalty:** when both payees have ≥5 transactions AND
  category overlap is < 50%, knock off ~20 points. Magnet payees are
  exempt.

## Algorithm at scale

Naive pairwise comparison on 500 payees is 125k comparisons. Blocking
cuts this dramatically:

```
payees = filter(deleted, transfer, internal, txn_count >= 2)
                 │
                 ▼
        ┌──────────────────┐
        │  tokenize names  │  split on space, lowercase, strip digits/punct
        └──────────────────┘
                 │
                 ▼  union-find on shared tokens
   ┌─────────────────────────────────────────────────┐
   │  STARBUCKS #1234  ─┐                            │
   │  STARBUCKS #5678  ─┤── {A, B, C}  ──┐           │
   │  STARBUCKS COFFEE ─┘                │           │
   │                                      │           │
   │  UBER TRIP         ───────── {D, E} ─┤           │
   │  UBER EATS        ──────────────────┘           │
   │                                                  │
   │  Within each block, score every pair.           │
   │  Threshold the pairs, union-find cluster them.   │
   └─────────────────────────────────────────────────┘
                 │
                 ▼
        candidate_groups = clusters
                          │
                          ▼
              sort by confidence desc
              return top N
```

For ~500 payees this is ~1–5k pair comparisons instead of 125k. Token
blocking is conservative — it might miss "Amzn" vs "Amazon"; trigram
blocking could be added as a fallback for low-confidence pairs.

## Threshold UX

The analyze response encodes tiers so the UI / agent doesn't have to
compute them:

```jsonc
{
  "report_id": "uuid",           // opaque id for executing the merge later
  "groups": [
    {
      "canonical_suggestion": {"id": "uuid-c", "name": "Starbucks"},
      "candidates": [
        {"id": "uuid-a", "name": "STARBUCKS #1234 SEATTLE WA", "txn_count": 12, "categories": ["Coffee", "Lunch"]},
        {"id": "uuid-b", "name": "STARBUCKS #5678 BELLEVUE WA", "txn_count":  8, "categories": ["Coffee"]}
      ],
      "signals": {
        "name_score":     92,
        "category_score": 88,
        "account_score":  100,
        "volume_balance": 75
      },
      "confidence": 89,
      "tier": "auto_merge"        // or "needs_review" or "skip"
    }
  ],
  "summary": {"auto_merge": 3, "needs_review": 7, "skip": 12}
}
```

`threshold` is the analyze-time parameter that decides which tier each
group lands in. The merge tool takes `report_id` + a filtered list of
groups to execute. The human / agent can:

- Re-run with a different `threshold` to see what auto-merges at a
  different bar.
- Edit the JSON: drop a group, swap the canonical, force-split a
  candidate out.
- Pass the edited list to the merge tool with `dry_run=true` first.
- Re-run with `dry_run=false` to commit.

## Edge cases

| Case | Handling |
|---|---|
| Transfer payees (account-bound) | Skip — never merge |
| Deleted / hidden payees | Skip |
| Payees with < 2 transactions | Skip — no category signal to compute |
| YNAB internal payees (Starting Balance, Reconciliation, etc.) | Skip via name allowlist |
| Split transactions | Use parent `payee_id` |
| Same name, different UUID | Detect explicitly and **flag**, never auto-merge |
| Payee with all txns in single category | Need a min-txn-count safeguard so category_score doesn't trivially hit 100 |
| Magnet payees (Amazon, Walmart, Google, etc.) | Lower category penalty via starter list + config hook |
| Undo | Capture `(txn_id → source_payee_id)` in merge result; offer a revert function that re-patches |

## Design decisions to make

These are the axes without a single right answer:

1. **Scoring library** — `rapidfuzz` (fast, MIT, new dep) vs
   `difflib.SequenceMatcher` (stdlib, slower, fine at ~500 payees).
2. **Magnet list** — hardcoded starter list vs `.env`-configurable vs
   both.
3. **Date window default** — last 12 months (cleaner signal, misses
   old duplicates) vs all-time (catches old ones, noisier) vs
   user-specified.
4. **Canonical pick algorithm** — most-transactions wins (deterministic,
   conservative) vs longest-name wins (often the cleanest label) vs
   user-must-pick.
5. **Threshold tiers** — single threshold (above = merge, below =
   review) vs three tiers (auto-merge / review / skip).
6. **Same-name explicit merge** — YNAB occasionally creates separate
   payees with identical names; should the tool flag those as "exact
   name match" candidates regardless of fuzzy score?
7. **LLM assist boundary** — scoring is pure algorithm (per the user's
   brief); the amend step is where an LLM agent adds value (reviews
   the report, recommends changes). Confirm this boundary.

## Recommended phasing

A two-phase MVP that maps to existing conventions:

**Phase 1 — Analyzer resource** (`data://payees/duplicates`):
pure read, returns the report. No destructive capability yet. This
is where we tune scoring weights and the magnet list. We can iterate
the algorithm against real data without any risk.

**Phase 2 — Merge tool** (`merge_payees`): dry-run by default, takes
the `report_id` + a filtered group list, bulk-patches via
`update_transactions`, optionally renames the canonical.

Pause after Phase 1, look at the report against the real budget, tune
weights, then expose mutating capability. That feels like the right
balance of "build something useful quickly" and "don't accidentally
nuke payees."

## Open next steps

- Walk through scoring against a few real payee pairs.
- Sketch the Pydantic schemas (`PayeeDuplicateReport`, `PayeeMergeResult`,
  per-group signals, tiers).
- Compare `rapidfuzz` vs `difflib` for this workload.
- If the design crystallizes, capture it as an OpenSpec change
  (`proposal.md`, `design.md`, `tasks.md`).
