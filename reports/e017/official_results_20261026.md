# E017 — Gate calibration and plots: official-dataset replay

Date: 2026-10-26. Scope: neutral aggregate **first-round municipal turnout**. **No presidential vote forecast or causal claim.**

## Provenance and execution
- GitHub Actions [successful run #40396825731](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40396825731), dataset artifacts E005 (TSE) and E006 (IBGE) with SHA256 validation.
- E017 artifact [12685324186](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40396825731/artifacts/12685324186), containing metadata, 30,870 per-path stage/model records, group summary, and **12 PNG/SVG plots**.
- 5,569 municipalities; 245 artificial complete-municipality reveal orders; nine electorate-coverage thresholds; 14 methods (E014–E017).
- First 60 permutations of each stochastic scenario: development; remaining 60 of each: evaluation. Five deterministic sequences: descriptive stress only.

## Model selection on development orders only
Predeclared development criterion: mean absolute error plus 0.25 times the 95th percentile absolute error plus a penalty for maximum error exceeding the UF-smoothed baseline maximum by more than 1 pp. Five early coverage levels 0.25%, 1%, 2.5%, 5%, 10%.

The selected family/configuration is **e017_permissive_quadratic** (score 0.8673); moderate quadratic score 0.8688; UF-smoothed swing 0.8848. Selection performed **without using evaluation-order scores**.

### Evaluation (120 previously withheld random reveal orders)
The following summaries pool 60 uniform and 60 UF-balanced orders, equally weighted. Error units are percentage points (pp).

| Coverage of registered electorate | UF-smoothed swing MAE | E016 guarded quadratic MAE | E017 selected permissive quadratic MAE | Selected fallback frequency |
| --- | ---: | ---: | ---: | ---: |
| 2.5% | 0.4699 | 0.4678 | **0.4633** | 65.8% |
| 10% | 0.3069 | 0.3035 | **0.2985** | 20.8% |
| 25% | 0.2059 | 0.1977 | **0.1609** | 0% |

In these particular heldout order/stage slices, the maximum absolute error of the selected method did not exceed the UF benchmark: 1.5827 pp at 2.5%, 1.3584 pp at 10%, and **0.4974 versus 0.6205 pp** at 25%.

### Five prespecified deterministic orders (descriptive stress, not holdout)
The permissive quadratic model falls back to UF-smoothed swing in all five deterministic sequences at 2.5% coverage (MAE across five paths 1.9619 pp, maximum 4.2430 pp). At 25% coverage, it achieves mean error 1.1827 versus UF benchmark 1.2843 pp and maximum 1.3393 versus 1.8317 pp. This remains a *descriptive* development-set-family result.

## Interpretation
- E016 excessive early fallback is reduced by more permissive gates while preserving train-only clipped swing and conservative regression blending.
- The 0.25% and 1% extreme reveal regimes still need guard inspection before any operational extrapolation.
- Held-out permutations are independent **orders**, not independent **electoral results**: all 245 use the same 2026 municipal turnout values. This is **not temporal generalization** to unseen election years.
- Never interpret the 120 heldout permutations as independent elections; uncertainty intervals over them would measure conditional order variation, not future-year uncertainty. No predictive interval calibration is established.
- The selected policy is exploratory. Do not merge as a production election-night model.

## Figures
GitHub Actions artifact contains `figures/development_mae.png`, `figures/evaluation_mae.png`, `figures/evaluation_fallback.png`, `figures/evaluation_tail.png`, and their SVG counterparts. The images use simulated electorate-coverage—not authentic TSE reporting timestamps.

## Next empirical hurdle
Validate the chosen E017 rule on at least one **independent election year** with consistent historical features and unaltered model parameters, and assess additional synthetic arrival mechanisms not used in policy development.
