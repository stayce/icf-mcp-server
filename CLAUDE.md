# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ICF MCP Server - A Model Context Protocol (MCP) server that provides tools for accessing the WHO International Classification of Functioning, Disability and Health (ICF) classification system via the WHO ICD-API.

## Architecture

**Package structure:** `src/icf_mcp/`

**Two-module design:**
- `server.py` - FastMCP server with 6 tools exposed to MCP clients (icf_lookup, icf_search, icf_browse_category, icf_get_children, icf_explain_qualifier, icf_overview)
- `who_client.py` - Async HTTP client (`WHOICFClient`) for WHO ICD-API with OAuth2 client credentials authentication

**Data flow:** MCP tool → `get_client()` singleton → `WHOICFClient` → WHO ICD-API (id.who.int)

**Key dataclasses:** `ICFEntity` (code details with definition/inclusions/exclusions), `ICFSearchResult` (search results with score)

## Running the Server

```bash
# Required environment variables
export WHO_ICD_CLIENT_ID="your_client_id"
export WHO_ICD_CLIENT_SECRET="your_client_secret"

# Optional environment variables
export WHO_ICD_RELEASE="2025-01"   # API release version
export WHO_ICD_LANGUAGE="en"       # Language code

# Run via module
python -m icf_mcp
```

Register for API credentials at: https://icd.who.int/icdapi

## Dependencies

- `httpx` - Async HTTP client
- `pydantic` - Data validation (FastMCP dependency)
- `mcp` - Model Context Protocol SDK (FastMCP)

## ICF Code Structure

ICF codes use single-letter prefixes indicating category:
- `b` = Body Functions (b1-b8)
- `s` = Body Structures (s1-s8)
- `d` = Activities and Participation (d1-d9)
- `e` = Environmental Factors (e1-e5)

Qualifiers (0-4, 8, 9) rate severity of impairment.
