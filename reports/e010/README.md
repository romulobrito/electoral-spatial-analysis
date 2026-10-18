# E010: historical spatial lag and evaluation

The methods protocol is frozen in `docs/e010_protocol.md` before reading empirical E010 results.

This branch tests whether 2022-only geographic neighbors add retrospective out-of-state explanatory value to models of **aggregate turnout** between 2022 and 2026. No candidate support estimate, geography targeting score or household behavior is modeled.

The CI `.github/workflows/e010-historical-spatial.yml` runs the full evaluation against SHA256-frozen official-data snapshots. Commit only evidence-backed numbers after successful execution; never treat projected runs or unit-test fixtures as experimental results.
