# E018 — Incremental official-source archive and replay adapter

**Status:** implemented normalized-snapshot replay and defensive tests; there is **not yet a real-time TSE connector**. Historical official TSE data snapshots should only be classified as empirical real-time arrival evidence if archived original timestamps and source bytes can be authenticated. Never reconstruct official arrival order from final results.

## Contract
CSV columns in strict order:
`election_id,unit_id,source_generated_utc,received_utc,reported_sections,total_sections,eligible_reported,attended_reported,source_sha256`.

Each row is a **cumulative snapshot** for one uniquely identified reporting unit, not a delta. Timestamps UTC with Z suffix. SHA256 identifies the raw source file corresponding to that normalized snapshot and must be independently verified in ingestion. This adapter checks SHA256 string shape but cannot verify the raw source bytes unless supplied by a separate authenticated collector.

The processor sorts in actual receiver time, deduplicates repeats, discards stale later-arriving versions, rejects conflicting equal-time snapshots, rejects regressed section/registered-elector counts, and permits newer corrections of attended counts. Replayed aggregate percentages use only eligible voters in already reported sections. This is an **observed partial statistic**, not a national turnout forecast because reporting selection is biased.

The implementation intentionally does **not** invent TSE JSON keys or URLs; an authenticated source-schema adapter and immutable collection are still required before true live ingestion. Snapshot generation time and receipt time are kept separate.

## Temporal validation
Current 2026 first-round trained E007/E013 turnout regression may update as municipal observations are revealed, but this is not independent-election validation. Backtests across genuinely separate election years require archived past-year features as-of the election and a strict temporal holdout. It would be improper to call random 2026 arrivals independent year validation.

## Charts
The E018 figure generator uses the normalized replay CSV and renders observed turnout and section coverage against receipt time, labeling output as **synthetic** unless original verified source snapshots are supplied. Do not infer timing from a final aggregate CSV.
