# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ICF MCP Server (`icf-mcp-server`) is a Model Context Protocol (MCP) server that provides tools for accessing the WHO International Classification of Functioning, Disability and Health (ICF) classification system via the WHO ICD-API. It enables AI assistants (e.g., Claude) to look up, search, and browse ICF codes through a standardized tool interface.

**Repository:** `stayce/icf-mcp-server` (MIT License)

## Architecture

### Package Layout

```
src/icf_mcp/
├── __init__.py      # Package exports: main, mcp, WHOICFClient, ICFEntity, ICFSearchResult
├── instruments.py   # Clinical assessment instruments with ICF mappings
├── server.py        # FastMCP server with 17 MCP tools + qualifier parsing
└── who_client.py    # Async WHO ICD-API client with OAuth2 auth
```

Uses `src/` layout with Hatchling build system. Entry point: `icf-mcp = "icf_mcp:main"`.

### Three-Module Design

- **`server.py`** — FastMCP server defining 17 tools via `@mcp.tool()` decorators:
  - `icf_lookup(code)` — Look up a specific ICF code (e.g., "b280", "d450")
  - `icf_search(query, max_results=10)` — Search by keywords
  - `icf_browse_category(category)` — Browse categories and sub-chapters ("b", "d4", "e3", etc.)
  - `icf_get_children(code)` — Get subcategories of a code
  - `icf_explain_qualifier(component, qualifier)` — Component-specific qualifier reference (b/s/d/e)
  - `icf_overview()` — Return full ICF classification overview
  - `icf_get_parent(code)` — Navigate up the hierarchy to a code's parent category
  - `icf_get_siblings(code)` — Get codes at the same level (same parent)
  - `icf_validate_code(code)` — Validate code format, qualifiers, and verify existence
  - `icf_parse_qualified_code(code)` — Parse fully qualified codes (d450.23, s730.312, e120+3)
  - `icf_build_profile(codes)` — Build a structured functional profile from multiple codes
  - `icf_get_code_chain(code)` — Show the full hierarchy path from root to a code
  - `icf_list_instruments(domain)` — List available clinical assessment instruments
  - `icf_instrument_details(name)` — Full instrument spec: items, scoring, ICF mappings
  - `icf_score_instrument(name, responses)` — Score responses and get clinical interpretation
  - `icf_suggest_instruments(condition, icf_code, domain)` — Suggest instruments for a condition or ICF code
  - `icf_instrument_icf_mapping(name)` — Show how an instrument maps to ICF codes
- **`instruments.py`** — Clinical assessment instrument definitions with ICF mappings. 11 instruments: GAD-7, PHQ-9, RADAI-5, SLEDAI-2K, WHODAS 2.0, HAQ-DI, PROMIS-10, CAT, ODI, NRS Pain, Short FES-I. Includes scoring logic, score interpretation ranges, and alias resolution.
- **`who_client.py`** — `WHOICFClient` class handling OAuth2 client credentials auth and all HTTP communication with the WHO ICD-API

### Data Flow

```
MCP Client → FastMCP tool → get_client() singleton → WHOICFClient → WHO ICD-API (id.who.int)
```

### Key Patterns

- **Singleton client:** `get_client()` in `server.py` creates and caches a single `WHOICFClient` instance
- **Lazy HTTP client:** `httpx.AsyncClient` is only created on first API call (`_get_http_client()`)
- **Auto token refresh:** 401 responses trigger re-authentication and automatic retry in `_api_request()`
- **Async throughout:** All API operations use `async`/`await` with `httpx.AsyncClient`
- **Graceful errors:** MCP tools catch exceptions and return user-friendly error strings rather than raising
- **Logging to stderr:** All logging goes to stderr (required for STDIO MCP transport)
- **Flexible response parsing:** `_parse_entity()` handles multiple WHO API response formats (strings, dicts, lists)

### Key Data Classes (in `who_client.py`)

- **`ICFEntity`** — Full ICF code details: `code`, `title`, `definition`, `inclusions`, `exclusions`, `parent`, `children`, `uri`
- **`ICFSearchResult`** — Search hit: `code`, `title`, `score`, `uri`

Both have a `to_dict()` method for serialization.

## Development Setup

### Prerequisites

- Python >= 3.11
- WHO ICD-API credentials (register at https://icd.who.int/icdapi)

### Installation

```bash
# Clone and set up virtual environment
git clone https://github.com/stayce/icf-mcp-server.git
cd icf-mcp-server
python -m venv venv
source venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Environment Variables

Copy `.env.example` to `.env` and fill in credentials:

```bash
WHO_ICD_CLIENT_ID="your_client_id"       # Required
WHO_ICD_CLIENT_SECRET="your_client_secret" # Required
WHO_ICD_RELEASE="2025-01"                  # Optional (default: "2025-01")
WHO_ICD_LANGUAGE="en"                      # Optional (default: "en")
```

The server uses `python-dotenv` to load `.env` files automatically.

### Running the Server

```bash
# Via module
python -m icf_mcp

# Via entry point (after pip install)
icf-mcp
```

The server runs over STDIO transport (standard MCP pattern).

## Testing

```bash
# Run tests
pytest

# Async tests are auto-detected (asyncio_mode = "auto" in pyproject.toml)
```

Dev dependencies: `pytest>=7.0.0`, `pytest-asyncio>=0.21.0`. No test files exist yet — tests should go in a `tests/` directory at the project root.

## Dependencies

| Package | Role |
|---------|------|
| `httpx>=0.25.0` | Async HTTP client for WHO API |
| `mcp>=1.0.0` | Model Context Protocol SDK (provides `FastMCP`) |
| `python-dotenv>=1.0.0` | Load `.env` files for credentials |
| `pydantic` | Data validation (transitive via `mcp`) |

## WHO ICD-API Integration Details

### Authentication

OAuth2 client credentials flow against `https://icdaccessmanagement.who.int/connect/token` with scope `icdapi_access`.

### API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/icd/release/11/{release}/icf` | ICF root |
| `/icd/release/11/{release}/icf/codeinfo/{code}` | Code lookup → returns `stemId` |
| `/icd/release/11/{release}/icf/search?q=...` | Full-text search with flexisearch |
| `/icd/release/11/{release}/icf/{entity_path}` | Entity details by URI |

### Request Headers

All API requests include: `Authorization: Bearer {token}`, `Accept: application/json`, `Accept-Language: {language}`, `API-Version: v2`.

## ICF Code Structure

ICF codes use single-letter prefixes indicating component:
- `b` = Body Functions (chapters b1-b8)
- `s` = Body Structures (chapters s1-s8)
- `d` = Activities and Participation (chapters d1-d9)
- `e` = Environmental Factors (chapters e1-e5)

Codes are hierarchical: `b2` (chapter) → `b280` (3-digit) → `b2800` (4-digit).

### Qualifiers

Each component has a different qualifier system:

**Body Functions (b)** — 1 qualifier: extent of impairment
- Format: `b{code}.{extent}` (e.g., `b280.2` = moderate pain impairment)

**Body Structures (s)** — 3 qualifiers: extent, nature of change, location
- Format: `s{code}.{extent}{nature}{location}` (e.g., `s730.312` = severe, total absence, right)
- Nature of change: 0=no change, 1=total absence, 2=partial absence, 3=additional part, 4=aberrant dimensions, 5=discontinuity, 6=deviating position, 7=qualitative changes
- Location: 0=multiple regions, 1=right, 2=left, 3=both sides, 4=front, 5=back, 6=proximal, 7=distal

**Activities & Participation (d)** — 2 qualifiers: performance, capacity
- Format: `d{code}.{performance}{capacity}` (e.g., `d450.23` = moderate performance, severe capacity)
- Performance = what a person does in current environment
- Capacity = what a person can do in standardized environment

**Environmental Factors (e)** — 1 qualifier: barrier or facilitator
- Barriers: `e{code}.{value}` (e.g., `e120.2` = moderate barrier)
- Facilitators: `e{code}+{value}` (e.g., `e120+3` = substantial facilitator)

**Generic severity scale** (used across all components): 0=none (0-4%), 1=mild (5-24%), 2=moderate (25-49%), 3=severe (50-95%), 4=complete (96-100%), 8=not specified, 9=not applicable

## Conventions

- **No CI/CD pipelines** configured yet — no `.github/workflows/` directory
- **No linter/formatter config** — no ruff, flake8, mypy, or black configuration
- **Build system:** Hatchling (`pyproject.toml` only — no `setup.py` or `setup.cfg`)
- **Python version:** 3.11+ (uses `X | Y` union syntax, dataclasses)
- **Version:** Tracked in both `pyproject.toml` and `src/icf_mcp/__init__.py` (`__version__`) — keep in sync, and add a `CHANGELOG.md` entry per release
- **Error handling in tools:** Return descriptive error strings, don't let exceptions propagate to MCP clients
- **Logging:** Use `logging` module, output to stderr, INFO level by default
