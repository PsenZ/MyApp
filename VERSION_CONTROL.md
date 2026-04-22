# Version Control

## Current Version

- Version: `2.3.0`
- Date: `2026-04-20`
- Status: Upgraded strategy engine and US watchlist

## Versioning Rules

- `MAJOR`: signal model, state schema, report contract, or risk model changes that may affect trading decisions.
- `MINOR`: new data source, indicator, report section, backtest metric, or configuration option.
- `PATCH`: bug fix, test improvement, copy update, or operational hardening with no decision-model change.

## Changelog

### 2.3.0

- Upgraded the scoring engine with stricter trend-following rules inspired by bull-trend, shrink-pullback, and volume-breakout evaluation ideas.
- Added MA5/MA10/MA20 alignment, anti-chase deviation checks, shrink-volume pullback preference, heavy-volume breakout confirmation, sector resonance, and stronger negative-news veto logic.
- Updated the active US watchlist to `NVDA,TSLA,AAPL,AMD,MU,QQQ,SMH`.
- Kept daily brief delivery more reliable by widening the schedule window and allowing same-day catch-up sending.
- Added dual timezone display for Sydney and US Eastern in reports and alerts.

### 2.2.0

- Renamed the project from `ShortReport` to `VeyraQuant`.
- Renamed the Python package from `shortreport` to `veyraquant`.
- Updated public-facing docs, frontend branding, workflow compile paths, and tests.

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
