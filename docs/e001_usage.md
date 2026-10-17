# E001: reproducible ingestion and municipal turnout audit

This first version uses Python's standard library; the downloader limits the source host to HTTPS `cdn.tse.jus.br`, rejects redirects to other hosts, bounds payload size, and refuses overwrites. ZIP members are inventoried and read without extracting paths to disk.

`audit-turnout` expects a **detail-by-section** ZIP with presidential election columns, including section, round, municipality (TSE), and `QT_APTOS`, `QT_COMPARECIMENTO`, `QT_ABSTENCOES`. It deduplicates exact repeated section counts, rejects contradictions, filters non-presidential cargos, and aggregates by municipality and round. Actual 2022/2026 schemas and special cases must be inspected before production use.

Raw archives and large JSON outputs belong in local `data/` and `outputs/` (ignored by Git); compact, documented summaries can be committed later. Existing manifests/outputs are never overwritten silently.

The auditor is intentionally conservative: if required columns are absent, if multiple CSV members are ambiguous, or if totals conflict, execution **fails** rather than guesses. Polling place is not equated with residential neighborhood. No individual-level vote inference is supported.
