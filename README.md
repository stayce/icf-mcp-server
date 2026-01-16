# ICF MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides access to the WHO International Classification of Functioning, Disability and Health (ICF) via the WHO ICD-API.

## What is ICF?

The ICF is a WHO classification that complements ICD (diagnosis codes) by describing how health conditions affect a person's functioning in daily life. It covers:

- **Body Functions (b)** - Physiological and psychological functions
- **Body Structures (s)** - Anatomical parts of the body
- **Activities and Participation (d)** - Task execution and life involvement
- **Environmental Factors (e)** - Physical, social, and attitudinal environment

## Tools

| Tool | Description |
|------|-------------|
| `icf_lookup` | Look up a specific ICF code (e.g., `b280`, `d450`) |
| `icf_search` | Search by keyword (e.g., "walking difficulty", "pain") |
| `icf_browse_category` | Browse top-level categories: `b`, `s`, `d`, `e` |
| `icf_get_children` | Get subcategories of a code |
| `icf_explain_qualifier` | Explain severity ratings (0-4, 8, 9) |
| `icf_overview` | Full ICF classification overview |

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

- "Look up ICF code b280"
- "Search ICF for walking difficulties"
- "What are the subcategories under d4 (Mobility)?"
- "Explain ICF qualifier 3"
- "Give me an overview of the ICF classification"

## Development

```bash
# Install in development mode
pip install -e .

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

## API Reference

This server uses the [WHO ICD-API](https://icd.who.int/icdapi) which provides programmatic access to both ICD-11 and ICF classifications.

- API Documentation: https://icd.who.int/docs/icd-api/APIDoc-Version2/
- ICF Browser: https://icd.who.int/dev11/l-icf/en

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Acknowledgments

- World Health Organization for the ICD-API
- Anthropic for the Model Context Protocol
