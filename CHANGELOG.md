# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-03

Major expansion from 6 to 17 tools. ([#1](https://github.com/stayce/icf-mcp-server/pull/1))

### Added

**Hierarchy navigation**
- `icf_get_parent` — navigate up to a code's parent category
- `icf_get_siblings` — related codes at the same level (same parent)
- `icf_get_code_chain` — full breadcrumb from root to a code
- Sub-chapter browsing: `icf_browse_category` now accepts sub-chapter codes
  (`b1`, `d4`, `e3`, …) in addition to top-level components

**Qualifiers and code parsing**
- `icf_explain_qualifier` reworked with component-specific qualifier systems:
  Body Functions (extent), Body Structures (extent/nature/location),
  Activities & Participation (performance/capacity), Environmental Factors
  (barrier `.` / facilitator `+` notation)
- `icf_parse_qualified_code` — parse fully qualified codes such as
  `d450.23`, `s730.312`, `e120+3`
- `icf_validate_code` — format and qualifier validation with WHO API
  verification
- `icf_build_profile` — structured functional profile from multiple codes

**Clinical assessment instruments** (new `instruments.py` module)
- 11 standardized instruments with full item text, response scales, validated
  scoring, score interpretation, ICF code mappings, and recommended RPM
  reassessment frequency: GAD-7, PHQ-9, RADAI-5, SLEDAI-2K (organ-system
  weighted), WHODAS 2.0, HAQ-DI (category scoring), PROMIS-10 (item-9 pain
  recoding, GPH/GMH subscores), CAT, ODI (percentage), NRS Pain, Short FES-I
- `icf_list_instruments` — catalog with domain filtering
- `icf_instrument_details` — full questionnaire specification
- `icf_score_instrument` — score responses with clinical interpretation and
  ICF qualifier mapping
- `icf_suggest_instruments` — match instruments to a condition, ICF code, or
  domain
- `icf_instrument_icf_mapping` — instrument-to-ICF mappings by component

### Changed
- Entity fetches for children, siblings, and profiles now run concurrently
  (`asyncio.gather`) instead of sequentially
- Qualifier scales and component-name maps consolidated to single
  module-level sources of truth
- Instrument scoring dispatch uses a `scorer` field on each instrument
  instead of id-based branching
- README overhauled: full tool reference, instrument matrix, RPM workflow
  guide

## [0.1.0] - 2026-01-16

Initial release.

### Added
- FastMCP server over STDIO with 6 tools: `icf_lookup`, `icf_search`,
  `icf_browse_category`, `icf_get_children`, `icf_explain_qualifier`,
  `icf_overview`
- `WHOICFClient` — async WHO ICD-API client with OAuth2 client-credentials
  authentication and automatic token refresh

[0.2.0]: https://github.com/stayce/icf-mcp-server/releases/tag/v0.2.0
[0.1.0]: https://github.com/stayce/icf-mcp-server/commit/2d2103d
