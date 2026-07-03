# ICF MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides access to the WHO International Classification of Functioning, Disability and Health (ICF) via the WHO ICD-API — plus a built-in library of standardized clinical assessment instruments (GAD-7, PHQ-9, RADAI-5, SLEDAI-2K, WHODAS 2.0, and more) mapped to ICF codes for Remote Patient Monitoring (RPM) workflows.

## What is ICF?

The ICF is a WHO classification that complements ICD (diagnosis codes) by describing how health conditions affect a person's functioning in daily life. It covers:

- **Body Functions (b)** - Physiological and psychological functions
- **Body Structures (s)** - Anatomical parts of the body
- **Activities and Participation (d)** - Task execution and life involvement
- **Environmental Factors (e)** - Physical, social, and attitudinal environment

## Tools

### ICF Classification (12 tools)

| Tool | Description |
|------|-------------|
| `icf_lookup` | Look up a specific ICF code (e.g., `b280`, `d450`) |
| `icf_search` | Search by keyword (e.g., "walking difficulty", "pain") |
| `icf_browse_category` | Browse categories and sub-chapters: `b`, `d4`, `e3`, etc. |
| `icf_get_children` | Get subcategories of a code |
| `icf_get_parent` | Navigate up to a code's parent category |
| `icf_get_siblings` | Find related codes at the same level |
| `icf_get_code_chain` | Full hierarchy path from root to a code |
| `icf_validate_code` | Validate format, qualifiers, and existence |
| `icf_parse_qualified_code` | Parse qualified codes: `d450.23`, `s730.312`, `e120+3` |
| `icf_build_profile` | Build a functional profile from multiple codes |
| `icf_explain_qualifier` | Component-specific qualifier reference (b/s/d/e) |
| `icf_overview` | Full ICF classification overview |

### Clinical Assessment Instruments (5 tools)

| Tool | Description |
|------|-------------|
| `icf_list_instruments` | Catalog of assessment instruments, filterable by domain |
| `icf_instrument_details` | Full questionnaire: items, options, scoring, ICF mappings |
| `icf_score_instrument` | Score responses → severity, interpretation, ICF qualifier |
| `icf_suggest_instruments` | Match instruments to a condition, ICF code, or domain |
| `icf_instrument_icf_mapping` | How an instrument maps to ICF codes by component |

### Included Instruments

| Instrument | Domain | Items | Use Case |
|-----------|--------|-------|----------|
| **GAD-7** | Mental Health | 7 | Generalized anxiety screening/monitoring |
| **PHQ-9** | Mental Health | 9 | Depression severity |
| **RADAI-5** | Rheumatology | 5 | RA disease activity (patient-reported) |
| **SLEDAI-2K** | Rheumatology | 24 | Lupus disease activity (weighted, 9 organ systems) |
| **HAQ-DI** | Rheumatology | 20 | Functional disability (8 ADL categories) |
| **WHODAS 2.0** | General Function | 12 | WHO disability assessment (ICF-derived) |
| **PROMIS-10** | General Health | 10 | Global physical/mental health |
| **CAT** | Respiratory | 8 | COPD impact |
| **ODI** | Pain/MSK | 10 | Low back pain disability |
| **NRS Pain** | Pain | 1 | Rapid pain intensity |
| **Short FES-I** | Geriatrics | 7 | Fear of falling |

Every instrument includes full item text, response scales, validated scoring algorithms (including SLEDAI-2K organ-system weights and HAQ-DI category scoring), score interpretation ranges, ICF qualifier mappings, and recommended RPM reassessment frequency.

## Prerequisites

1. **WHO ICD-API credentials** (free): Register at https://icd.who.int/icdapi
2. **Python 3.11+**

## Installation

```bash
# Clone the repository
git clone https://github.com/stayce/icf-mcp-server.git
cd icf-mcp-server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

## Configuration

Create a `.env` file with your WHO API credentials:

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Usage with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "icf": {
      "command": "/path/to/icf-mcp-server/.venv/bin/python",
      "args": ["-m", "icf_mcp"],
      "env": {
        "WHO_ICD_CLIENT_ID": "your_client_id",
        "WHO_ICD_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

Restart Claude Desktop to load the server.

## Example Queries

Once configured, you can ask Claude:

**ICF classification:**
- "Look up ICF code b280"
- "Search ICF for walking difficulties"
- "What are the subcategories under d4 (Mobility)?"
- "Parse the qualified code d450.23"
- "Build an ICF profile from b280, d450, and e120"
- "Show the hierarchy chain for b28010"

**Clinical assessment:**
- "What instruments are available for rheumatoid arthritis?"
- "Show me the GAD-7 questionnaire"
- "Score this PHQ-9: 2,2,1,2,1,1,2,0,0"
- "Score a SLEDAI with arthritis, rash, and fever present"
- "Which ICF codes does WHODAS 2.0 map to?"
- "Suggest an instrument for monitoring pain (b280)"

## Remote Patient Monitoring (RPM)

This server is designed to support RPM questionnaire workflows:

1. **Design** — `icf_suggest_instruments` picks validated instruments for a condition; `icf_instrument_details` provides the exact items and response scales for your questionnaire platform
2. **Score** — `icf_score_instrument` converts patient responses into severity levels with clinical interpretation
3. **Code** — Scores map to ICF qualifiers automatically; `icf_build_profile` documents functional status in standard ICF terms
4. **Monitor** — Each instrument includes a recommended RPM reassessment frequency

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
python -m pytest

# Test the client directly
python -c "
import asyncio
from icf_mcp.who_client import WHOICFClient

async def test():
    client = WHOICFClient(client_id='...', client_secret='...')
    results = await client.search('pain')
    print(results)
    await client.close()

asyncio.run(test())
"
```

## Related Projects

- [icd-mcp-cloudflare](https://github.com/stayce/icd-mcp-cloudflare) — WHO ICD-10/ICD-11 MCP server (Cloudflare Workers)
- [icf-mcp-cloudflare](https://github.com/stayce/icf-mcp-cloudflare) — ICF MCP server for Cloudflare Workers

## API Reference

This server uses the [WHO ICD-API](https://icd.who.int/icdapi) which provides programmatic access to both ICD-11 and ICF classifications.

- API Documentation: https://icd.who.int/docs/icd-api/APIDoc-Version2/
- ICF Browser: https://icd.who.int/dev11/l-icf/en

## Disclaimer

Assessment instruments are provided for informational and workflow-support purposes. Scoring and interpretation ranges follow published literature but do not replace clinical judgment. Instrument copyrights belong to their respective authors; verify licensing requirements for commercial use (e.g., HAQ-DI, CAT).

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Acknowledgments

- World Health Organization for the ICD-API and ICF classification
- Anthropic for the Model Context Protocol
- Instrument authors: Spitzer et al. (GAD-7), Kroenke et al. (PHQ-9), Leeb et al. (RADAI-5), Gladman et al. (SLEDAI-2K), Üstün et al. (WHODAS 2.0), Fries et al. (HAQ-DI), Hays et al. (PROMIS), Jones et al. (CAT), Fairbank & Pynsent (ODI), Kempen et al. (Short FES-I)
