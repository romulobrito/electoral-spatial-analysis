# E016 — Guarding E007/E013 online turnout extrapolation

Goal: investigate E015's 61.454 pp early-stage error (quadratic regression with smallest municipalities revealed first, at 0.25% coverage of registered electorate). This is **exploratory engineering**, not a post-hoc independent validation.

Reuse the E014/E015 5,569-municipality audited panel and 245 fixed synthetic arrival paths; leave the eight previous estimators unmodified. Evaluate two guarded regression variants.

Fixed guard settings (not selected from E016 outcome metrics):
- At least 8 revealed UFs, Kish weighted effective sample size >=25.
- Among the unrevealed electorate, no more than 35% outside the train-only 5th–95th percentile feature support expanded by 1 train SD. Historical feature values are allowed for unrevealed municipalities.
- Turnout percentage-point swing bounds from revealed 5th/95th percentiles plus/minus 2 pp, also restricted to [-8,+8] pp.
- Maximum 75% contribution of guarded regression versus UF-shrunk reference; novelty reduces regression weight as 0.75/(1+distance^2).
- If a gate fails, use the unchanged E014 UF-shrunk swing estimator.

All 2026 turnout values of **unrevealed** municipalities are excluded from model fitting, preprocessing and guard decisions. Known 2022 features and 2026 registered electorate are permitted. The 2026 full observed turnout is accessed solely to score errors.

Outputs include paired comparison with E014/E015, MAE, 90th percentile and maximum errors for each scenario/coverage, fallback reasons, effective sample size, UF coverage, extrapolation share and bounded predicted swings.

**Important:** The E016 setting is developed on exactly the same 2026 election; a lower retrospective error here would not constitute prospective validation, and the numerical guards need future temporal and independent-arrival validation before operational adoption.

Reproduction via `.github/workflows/e016-robustness.yml` and official E005/E006 archived artifacts.
