# FDE Data Artifacts

Data hierarchy used by the engine and notebooks.

## 1. Layout

- `raw/`
  - Vendor / exchange dumps as delivered.
  - **Never modified** in place.
- `staging/`
  - Intermediate cleaned tables (e.g. symbol normalization, timezone fix).
- `features/`
  - Final factor / feature matrices that feed directly into personas.
  - Example: `equities_intraday.parquet`, `macro_daily.parquet`.
- `backtests/`
  - Scenario-ready data slices for the engine.
  - Example: `sp500_2018_2024_intraday.parquet`.
- `reference/`
  - Universe lists, symbol mappings, calendars, meta JSON, etc.

## 2. Minimal Contracts

Engine expects:

- Feature tables that can be reshaped into a `MarketState`
- Stable symbol identifiers across all tables
- A clear date / time column (usually UTC)

See `architecture/data/data_contracts.md` for logical schema.
