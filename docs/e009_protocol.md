# E009 — State-conditioned spatial residual autocorrelation

## Question and relationship to E008

E008 found Moran's I around 0.40–0.50 for geographically adjacent municipalities' retrospective turnout residuals, but its *global* shuffles might conflate **between-UF differences** with **within-UF local dependence**. E009 removes cross-state boundary edges, centers the residual series within each UF and computes a **different**, conditional statistic on within-UF neighbor graphs. E008 and E009 point estimates are **not** directly comparable because weights, node sets and centering differ.

## Inputs and quality gates

Recreate E007 held-out residuals using hashes for E005 TSE first-round aggregate turnout panel and E006 official IBGE Census 2022 data. Assert the exact E007 MAEs. Download original 2022 IBGE municipal boundaries (EPSG:4674, SHA256 pinned). The 2022/2026 TSE-to-IBGE municipality join is **already frozen inside the E005 panel and its SHA256**; do not download a newer live crosswalk to change validated historical municipality codes. Preserve each municipality's UF and the known Amazonas-denominator exception.

From E008's queen/rook adjacency, keep only edges whose **two endpoints are in the same UF**. All cross-UF edges are counted and excluded. Recalculate isolates after excluding such edges; DF and other disconnected municipalities can be excluded **only from this contiguity statistic**, without dropping them from the original E005/E006 electorally reconciled panel.

Center each held-out residual model separately by its **connected-node mean within UF**, compute row-normalized Moran I over connected nodes, and report the corresponding in-UF graph sizes. For connected nodes \\(i\\), define
\\[
z_i=e_i-\\bar e_{\\mathrm{UF}(i)},\\qquad
I_{\\mathrm{cond}}=\\frac{\\sum_i z_i\\left(\\sum_{j\\in N_{\\mathrm{UF}}(i)} z_j/|N_{\\mathrm{UF}}(i)|\\right)}{\\sum_i z_i^2}.
\\]

The conventional \\(-1/(N-1)\\) expectation of global randomization **does not automatically apply** after UF demeaning and within-UF shuffles. Use the **empirical permutation mean** to define a two-sided tail; provide both empirical mean and 95% null interval.

## Conditional null and protocol

For each of baseline, E006 ridge and E007 training-only regional correction, under **both** queen and rook within-UF graphs:

- Preserve the observed state-centered residual values, municipality membership, graph topology and geographic weights.
- Shuffle residual values **within each UF only**, never across UFs, using 499 Monte Carlo permutations and seed 2718. Recompute Moran I after each draw. Report two-sided empirical-center-tail p and directional right-tail p with plus-one corrections.
- Report how many edges crossing states were excluded, within-state edges, connected municipalities, isolates, and all-UF group counts.
- Do not interpret six exploratory correlated tests as confirmatory family-wise evidence; no causal identification or electoral preference inference is possible.

### Scope and interpretation

This protocol tests spatial organization of **aggregate turnout prediction errors** within states. It cannot measure voter neighborhoods, personal choices, candidate votes, persuasion potential or future electoral support. Even a significant conditioned Moran I may result from spatially varying omitted variables. The regional correction was proposed after E006, so none of these same-period results is an independent out-of-time validation.

## Reproduction

GitHub workflow `.github/workflows/e009-state-conditioned.yml` pins the E005 electoral panel, E006 Census snapshot and IBGE 2022 official geometry and publishes versioned conditional Moran JSON/CSV and SVG. On 2026-10-18, the live TSE crosswalk hash had changed relative to E004; its re-download was removed from E009 because the exact old mapping is already verified in E005. A separate explicit source-version migration is required to update that mapping. Keep compact results in Git; archive source geometry only by SHA256 and official URL.
