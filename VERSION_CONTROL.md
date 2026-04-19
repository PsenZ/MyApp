# Version Control

## Current Version

- Version: `2.1.0`
- Date: `2026-04-20`
- Status: Added bilingual public frontend page

## Versioning Rules

- `MAJOR`: signal model, state schema, report contract, or risk model changes that may affect trading decisions.
- `MINOR`: new data source, indicator, report section, backtest metric, or configuration option.
- `PATCH`: bug fix, test improvement, copy update, or operational hardening with no decision-model change.

## Changelog

### 2.1.0

- Added a static public-facing frontend page under `frontend/`.
- Added English-first bilingual language switching for English and Chinese.
- Added a blue-black cyber finance visual style with full-bleed market imagery.
- Added an interactive sample trade plan for `NVDA`, `MSFT`, and `SMH`.
- Updated README with frontend usage and deployment notes.

### 2.0.0

- Refactored the single-file script into modules for config, data, indicators, market regime, signals, risk, reporting, email, state, runner, and backtesting.
- Added `SYMBOLS` stock-pool support while keeping `python report.py` as the compatible entrypoint.
- Added market filters using `SPY`, `QQQ`, `SMH`, and `^VIX`.
- Added component scoring and signal types: breakout entry, pullback add, hold watch, risk reduce, and wait.
- Added trade plans with entry zone, stop, targets, R multiple, position percentage, max-loss percentage, trigger, and cancel conditions.
- Added state schema version `2` with per-symbol alert records and legacy state migration.
- Added cache-aware data fetching and graceful degradation for missing Yahoo/RSS/options data.
- Added unit, reporting, state, data, and backtest test coverage.
