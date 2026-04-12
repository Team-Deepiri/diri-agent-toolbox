# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `parse_json_or_text(response)` in `diri_agent_toolbox.http` (and re-exported from package root) for consistent JSON-or-text body parsing.

### Changed

- README: explicit traceability to **Deepiri Repo Division Doc** (Agent Tools section).
- CI: **mypy** check on `src`.
- Dev dependencies: `types-aiofiles` for mypy.

### Fixed

- Mypy: avoid static import of optional `langchain_core` in `langchain_adapter`; clarify file size helper typing in `files.py`.

## [0.1.0] — 2025

Initial published package: HTTP, data, files, calendar, CRM, `ToolRunner`, optional LangChain bridge.
