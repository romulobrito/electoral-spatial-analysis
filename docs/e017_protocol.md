# E017 — Gate calibration and diagnostic plots

E016 suppresses most online models during early revelation. E017 compares two **fixed** engineering alternatives to the E016 strict guard while retaining E014/E015/E016 unchanged. Candidate configurations: moderate (minimum 6 UFs, Kish ESS 15, hidden electorate out-of-support <=60%, maximum regression mixture 50%); permissive (minimum 4 UFs, Kish ESS 10, maximum OOS 85%, maximum mixture 35%). E016 strict and the E014 UF-smoothed reference remain candidates.

For each of the two random arrival scenarios, the first 60 permutations constitute the **development set** and the remaining 60 permutations the **evaluation set** (120 each in total). Policy selection on development uses stages up to 10% electorate coverage: MAE + 0.25 times P95 absolute error + 0.5 times the excess worst-case error over the UF baseline worst case plus 1 pp. No scores from the heldout arrival permutations influence policy selection. Five previously discussed deterministic/adversarial orders remain descriptive and are not independent heldouts.

**Caveat:** both subsets use **the exact same 2026 election and municipal outcomes**. Heldout permutations are a test of order-sampling robustness, NOT a true temporal holdout or independent confirmation. Report E017 differences as exploratory.

No new predictor uses hidden 2026 turnout. Covariate support checks may use historical features of unseen municipalities; the true 2026 turnout is consulted only for scoring. All methods predict neutral **aggregate first-round turnout**, not candidate vote shares.

Reproduce the official-source experiment with the E017 GitHub workflow. The workflow also produces PNG figures of MAE vs. coverage, fallback frequency and error tails. Exact artifact file names and GitHub Actions run are retained for audit.
