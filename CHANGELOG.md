# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.0.9] - 2026-11-08

### Added

- ARM: support packing multiple functions into one shared assembly file via `ArmAssemblyWriter`
- ARM: add `Function.prelude_asm` for injecting raw assembly text

### Fixed

- ARM: fix pre-existing bug in constants array handling
- ARM writer: feature-mismatch validation across packed functions, alignment aggregation, ARMCC epilogue handling, and a bug where packing functions with constants/literal pools could leave executable code placed in a data section

### Changed

- CI: harden security-scan workflow — bandit + pip-audit (replacing deprecated `safety`), pinned tool versions, upload reports on failure too
- CI: remove duplicate PyPI publish path; add a safe `workflow_dispatch` TestPyPI dry-run path for testing the release pipeline without touching production PyPI
- Bump `urllib3` 2.7.0 -> 2.8.0
- Bump `certifi` 2026.4.22 -> 2026.10.18

### Tests

- ARM: add tests for UXTH

## [0.0.8] - 2026-07-19

### Added

- [arm-m] Adds UXTH instruction

## [0.0.7] - 2026-06-16

### Added

- Adds support for generating assembly kernels that can be included to Rust projects.

