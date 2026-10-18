# E005 — Retrospective municipal voting and participation (first round)

**Scope:** Neutral, observed first-round municipal presidential voting statistics for **all candidate options** in 2022 and 2026; a simple turnout-persistence baseline. No candidate persuasion scores, future support probabilities, targeted campaign priorities or neighborhood inference.

**Official sources:** [TSE results 2022](https://dadosabertos.tse.jus.br/dataset/resultados-2022), [TSE results 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), official TSE–IBGE municipality mapping generated 2026-10-11. Freeze source SHA256. Never silently accept different versions.

**Audit:** Streaming national vote-by-section CSV; validate national nominal/blank/null totals, all candidate options, join exact official municipality crosswalk, independently verify municipal ballot totals against detailed section attendance. Retain unmatched geographies. Exclude overseas `ZZ` from Brazilian municipality comparisons without removing it from national vote checks. No zero-filling absent municipalities.

**Denominators:** Candidate vote share means *share of observed valid votes*, not probability of future candidate support. Municipality turnout is calculated using conserving-section eligible counts; an exceptional 2022 Amazonas record remains to be locally allocated. A polling place is not a residential-neighborhood boundary.

**Baseline:** Forecast 2026 municipality turnout by simply carrying forward its 2022 participation rate. Report retrospective MAE, RMSE and weighted MAE without tuning; do not mistake descriptive performance for candidate-vote forecasting or spatial out-of-sample skill.

**Execution:** `.github/workflows/e005-municipal-results.yml`. Outputs are temporarily retained in GitHub Actions; commit only compact audited summaries when completed. No user-level data or political targeting.
