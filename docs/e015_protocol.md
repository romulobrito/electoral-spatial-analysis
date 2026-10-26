# E015 — Sequential E007/E013 extensions for municipal turnout

**Scope:** Neutral first-round aggregate turnout, not candidate preference or second-round voting.

## Protocol
Freeze E014 5,569-municipality panel, 2022 historical turnout, 2026 eligible-elector weights, nine coverage targets and all 245 counterfactual municipality-arrival permutations (seed 20261026).

Compare four unchanged E014 estimators against:
- E007 fixed-alpha=10 linear ridge (2022 turnout, log1p 2022 population/density), fitted only on revealed 2026 municipal turnout changes.
- E007 ridge + train-only macrorregional residual intercept shrunk by n/(n+100).
- E013 quadratic ridge with squared standardized predictors, train-only fitted.
- E013 quadratic ridge + separately calculated train-only macrorregional residual intercept.

All normalizations and residual corrections are computed on revealed units. Predictions for unrevealed units use historical covariates and fitted turnout changes, clipped into [0,1]. When fewer than 10 municipalities are revealed or train features degenerate, fall back to the preexisting national-swing estimator; report fallback counts. These are online adaptations of E007/E013 model families, not reuse of their fitted full-2026 coefficients.

## Evaluation and epistemic boundaries
Compute paired absolute errors against the fully observed aggregate 2026 first-round turnout for each *same order and coverage*. Summarize mean, p90 and maximum error per scenario, comparison to the historical persistence benchmark, and fallback frequency. Diagnose worst adversarial sequences; never interpret 245 paths as 245 independent elections. No proper 95% forecast coverage is available without calibrated intervals. E008–E010 spatial Moran diagnostics are conceptually useful but remain outside the point-estimator family in this phase.

The regression coefficients are estimated sequentially on revealed parts of the **same 2026 election**; therefore this is an information-reveal simulation, not independent temporal validation across multiple election years. Results from a single election cannot prove prospective generalization. No actual section-level arrival timestamps are used.

## Reproduction
Execute .github/workflows/e015-online-models.yml, which retrieves SHA256-validated E005 and E006 assets and stores results as ephemeral workflow artifacts (14-day retention).

Local command:
```bash
python -m electoral_analysis.arrival_model_integration --panel outputs/e005-results/municipal_results.json --census data/reference/ibge_4714_2022.json --out-dir outputs/e015 --reps 120 --seed 20261026
```

New outputs: metadata.json, scenario_summary.csv and path_errors.csv. Do not overwrite archived E014 results and do not publish numerical claims before full official-data execution and quality review.
