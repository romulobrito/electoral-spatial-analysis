# Electoral Spatial Analysis

Reproducible scientific study of **aggregate** Brazilian electoral geography, historical changes and participation using official sources (TSE and IBGE).

**Status:** research infrastructure initialized; no electoral records have yet been downloaded or modeled. No empirical accuracy claims are made.

## Local setup

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check src tests
```

See `docs/protocol.md` for the scientific protocol, assumptions, safeguards and roadmap. Data ingestion starts with official resource inventory and checksum validation; `src/electoral_analysis/etl.py` currently supplies foundational utilities rather than a full download pipeline.

The project does not infer individual political preferences, target electoral persuasion audiences or optimize messaging for political conversion.
