# Changelog

All notable changes to Predixen Intelligence OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]
<!-- Add new features here. They will be included in the next publish notification. -->

## [1.1.0] - 2026-01-28

### Added
- **Decision Advisor Agent**: New AI agent that transforms questions into actionable, simulation-backed recommendations
  - Automatically detects decision-oriented queries like "How can I extend runway?"
  - Maps decisions to financial levers with feasibility ratings
  - Runs Monte Carlo simulations showing P10/P50/P90 outcomes
  - Provides risk analysis with sensitivity tables
  - Delivers opinionated recommendations with confidence levels

### Changed
- Updated Copilot to route decision queries to the new Decision Advisor Agent
- Enhanced multi-agent system with DECISION_ADVISOR agent type

## [1.0.0] - 2026-01-20

### Added
- Initial release of Predixen Intelligence OS
- Multi-agent AI copilot (CFO, Market, Strategy agents)
- Monte Carlo simulation engine
- Truth Scan for financial metrics analysis
- Scenario versioning and comparison
- Sensitivity analysis with tornado charts
- Document ingestion (CSV, Excel, PDF)
- Admin dashboard with RBAC
