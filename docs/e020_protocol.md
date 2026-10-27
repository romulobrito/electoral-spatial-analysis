# E020 — Municipality EA20 incremental replay

A municipality uses the official TSE five-digit municipality code and a two-letter UF. Do **not** treat municipality code as IBGE seven-digit identifier without the independently verified EA12 crosswalk.

Verified TSE publication reference:
https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

Municipal files are path-scoped by UF and EA20 municipality identifier. The parser rejects wrong `ele`, `tpabr`, `cdabr`, missing presidential contest, future generation timestamps and inconsistent progress counts.

This E020 module is an **offline event replay adapter**, not an active network collector or an independently verified genuine October 2026 arrival sequence. Raw bytes are read from paths supplied by an event journal; in production, use immutable content-addressed objects collected by E019-style trusted ingest.

States are cumulative by (election, UF, municipality), so later versions **replace** older ones rather than being added. National and state cumulative snapshots must never be mixed into that municipality sum. The observed partial turnout ratio is not a nationally unbiased projection, and the denominator `total_sections_in_observed_municipalities` does not represent all Brazilian sections. Municipality snapshots alone do not recover precinct-level arrival timestamps.

**Pending:** trusted EA12 municipality crosswalk, individual municipal official raw snapshot acquisition and authentication, synchronization with E017 municipal-level online regression, and independent-year validation. None of these pending parts are claimed complete.

Graph output uses clearly marked synthetic cumulative municipal events.
