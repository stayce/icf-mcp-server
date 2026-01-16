"""
ICF MCP Server - International Classification of Functioning, Disability and Health

This MCP server provides tools for looking up and searching ICF codes,
browsing ICF categories, and understanding functional health classifications.

The ICF is a WHO classification that complements ICD (diagnosis codes) by
describing how health conditions affect a person's functioning in daily life.
"""

import asyncio
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .who_client import WHOICFClient, ICFEntity

# Configure logging to stderr (important for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP(
    "ICF Classification Server",
    dependencies=["httpx", "pydantic"],
)

# Global client instance (initialized on first use)
_client: WHOICFClient | None = None


def get_client() -> WHOICFClient:
    """Get or create the WHO ICF API client"""
    global _client
    if _client is None:
        client_id = os.environ.get("WHO_ICD_CLIENT_ID")
        client_secret = os.environ.get("WHO_ICD_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            logger.warning(
                "WHO ICD-API credentials not set. "
                "Set WHO_ICD_CLIENT_ID and WHO_ICD_CLIENT_SECRET environment variables. "
                "Register at https://icd.who.int/icdapi to obtain credentials."
            )
        
        _client = WHOICFClient(
            client_id=client_id,
            client_secret=client_secret,
            release=os.environ.get("WHO_ICD_RELEASE", "2025-01"),
            language=os.environ.get("WHO_ICD_LANGUAGE", "en"),
        )
    
    return _client


def format_entity(entity: ICFEntity) -> str:
    """Format an ICF entity for display"""
    lines = [
        f"**{entity.code}**: {entity.title}",
    ]
    
    if entity.definition:
        lines.append(f"\n**Definition:** {entity.definition}")
    
    if entity.inclusions:
        lines.append("\n**Includes:**")
        for inc in entity.inclusions:
            lines.append(f"  - {inc}")
    
    if entity.exclusions:
        lines.append("\n**Excludes:**")
        for exc in entity.exclusions:
            lines.append(f"  - {exc}")
    
    return "\n".join(lines)


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool()
async def icf_lookup(code: str) -> str:
    """
    Look up an ICF code and get its full details.
    
    The ICF (International Classification of Functioning, Disability and Health)
    codes describe how health conditions affect functioning. Code prefixes:
    - b: Body Functions (e.g., b280 = sensation of pain)
    - s: Body Structures (e.g., s750 = structure of lower extremity)
    - d: Activities and Participation (e.g., d450 = walking)
    - e: Environmental Factors (e.g., e120 = assistive products for mobility)
    
    Args:
        code: The ICF code to look up (e.g., "b280", "d450")
        
    Returns:
        Detailed information about the ICF code including definition,
        inclusions, and exclusions.
    """
    client = get_client()
    
    try:
        entity = await client.get_entity_by_code(code)
        
        if entity is None:
            return f"ICF code '{code}' not found. Please check the code format."
        
        return format_entity(entity)
        
    except Exception as e:
        logger.error(f"Error looking up ICF code {code}: {e}")
        return f"Error looking up ICF code: {str(e)}"


@mcp.tool()
async def icf_search(query: str, max_results: int = 10) -> str:
    """
    Search the ICF classification by keywords or description.
    
    Use this to find ICF codes when you know what functional area you're
    looking for but don't know the specific code. For example:
    - "walking" to find mobility-related codes
    - "pain" to find pain-related body function codes
    - "memory" to find cognitive function codes
    
    Args:
        query: Search terms (e.g., "walking difficulty", "memory problems")
        max_results: Maximum number of results to return (default 10)
        
    Returns:
        List of matching ICF codes with titles and relevance scores.
    """
    client = get_client()
    
    try:
        results = await client.search(query, max_results=max_results)
        
        if not results:
            return f"No ICF codes found for '{query}'. Try different search terms."
        
        lines = [f"**ICF Search Results for '{query}':**\n"]
        
        for i, result in enumerate(results, 1):
            lines.append(f"{i}. **{result.code}**: {result.title}")
        
        lines.append(f"\nUse `icf_lookup` with any code above for full details.")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error searching ICF for '{query}': {e}")
        return f"Error searching ICF: {str(e)}"


@mcp.tool()
async def icf_browse_category(category: str) -> str:
    """
    Browse a top-level ICF category to explore available codes.
    
    ICF has four main categories:
    - "b": Body Functions - physiological and psychological functions
    - "s": Body Structures - anatomical parts of the body
    - "d": Activities and Participation - task execution and life involvement
    - "e": Environmental Factors - physical, social, attitudinal environment
    
    Args:
        category: Single letter category code (b, s, d, or e)
        
    Returns:
        Overview of the category with example codes and chapters.
    """
    client = get_client()
    
    try:
        result = await client.browse_category(category)
        
        lines = [
            f"**ICF Category: {result['name']}** (codes starting with '{result['category']}')",
            "",
            result["description"],
            "",
            "**Sample codes in this category:**",
        ]
        
        for item in result["results"][:10]:
            lines.append(f"  - **{item['code']}**: {item['title']}")
        
        lines.append(f"\nUse `icf_search` or `icf_lookup` for more specific codes.")
        
        return "\n".join(lines)
        
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.error(f"Error browsing ICF category '{category}': {e}")
        return f"Error browsing category: {str(e)}"


@mcp.tool()
async def icf_get_children(code: str) -> str:
    """
    Get the child codes (subcategories) of an ICF code.
    
    ICF codes are hierarchical. For example:
    - d4 (Mobility) contains d410-d499
    - d45 (Walking and moving) contains d450-d459
    - d450 (Walking) is a specific activity
    
    Use this to drill down into more specific codes.
    
    Args:
        code: Parent ICF code to get children for
        
    Returns:
        List of child codes under the specified parent.
    """
    client = get_client()
    
    try:
        children = await client.get_children(code)
        
        if not children:
            return f"No child codes found for '{code}'. This may be a leaf-level code."
        
        lines = [f"**Child codes under {code}:**\n"]
        
        for child in children:
            lines.append(f"- **{child.code}**: {child.title}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting children for ICF code {code}: {e}")
        return f"Error getting child codes: {str(e)}"


@mcp.tool()
async def icf_explain_qualifier(qualifier: int) -> str:
    """
    Explain ICF qualifier values used to rate severity of impairment.
    
    ICF uses qualifiers (0-4, 8, 9) to indicate the magnitude of a problem:
    
    Args:
        qualifier: The qualifier value (0-4, 8, or 9)
        
    Returns:
        Explanation of what the qualifier value means.
    """
    qualifiers = {
        0: ("No problem", "0-4%", "None, absent, negligible"),
        1: ("Mild problem", "5-24%", "Slight, low"),
        2: ("Moderate problem", "25-49%", "Medium, fair"),
        3: ("Severe problem", "50-95%", "High, extreme"),
        4: ("Complete problem", "96-100%", "Total"),
        8: ("Not specified", "N/A", "Insufficient information to specify severity"),
        9: ("Not applicable", "N/A", "Inappropriate to apply this code"),
    }
    
    if qualifier not in qualifiers:
        return (
            f"Invalid qualifier '{qualifier}'. "
            f"Valid values are: 0 (no problem), 1 (mild), 2 (moderate), "
            f"3 (severe), 4 (complete), 8 (not specified), 9 (not applicable)"
        )
    
    level, percentage, description = qualifiers[qualifier]
    
    return (
        f"**ICF Qualifier {qualifier}: {level}**\n\n"
        f"- **Percentage range:** {percentage}\n"
        f"- **Description:** {description}\n\n"
        f"Example: d450.{qualifier} means '{level.lower()}' difficulty with walking."
    )


@mcp.tool()
async def icf_overview() -> str:
    """
    Get an overview of the ICF classification system.
    
    Returns:
        General information about ICF, its structure, and how to use it.
    """
    return """
**International Classification of Functioning, Disability and Health (ICF)**

The ICF is a WHO classification that provides a standard language and framework 
for describing health and health-related states. It complements ICD (diagnosis 
codes) by describing how conditions affect a person's functioning.

## Structure

ICF has four main components:

### 1. Body Functions (b)
Physiological functions of body systems, including psychological functions.
- b1: Mental functions (consciousness, orientation, sleep, emotion)
- b2: Sensory functions and pain
- b3: Voice and speech functions
- b4: Functions of cardiovascular, respiratory systems
- b5: Functions of digestive, metabolic, endocrine systems
- b6: Genitourinary and reproductive functions
- b7: Neuromusculoskeletal and movement functions
- b8: Functions of skin and related structures

### 2. Body Structures (s)
Anatomical parts of the body.
- s1: Structures of nervous system
- s2: Eye, ear and related structures
- s3: Structures of voice and speech
- s4: Structures of cardiovascular, respiratory systems
- s5: Structures of digestive, metabolic, endocrine systems
- s6: Structures of genitourinary and reproductive systems
- s7: Structures of movement
- s8: Skin and related structures

### 3. Activities and Participation (d)
Execution of tasks and involvement in life situations.
- d1: Learning and applying knowledge
- d2: General tasks and demands
- d3: Communication
- d4: Mobility
- d5: Self-care
- d6: Domestic life
- d7: Interpersonal interactions
- d8: Major life areas (education, work, economic)
- d9: Community, social and civic life

### 4. Environmental Factors (e)
Physical, social and attitudinal environment.
- e1: Products and technology
- e2: Natural environment
- e3: Support and relationships
- e4: Attitudes
- e5: Services, systems and policies

## Qualifiers

Severity is rated on a scale:
- 0: No problem (0-4%)
- 1: Mild problem (5-24%)
- 2: Moderate problem (25-49%)
- 3: Severe problem (50-95%)
- 4: Complete problem (96-100%)

## Tools Available

- `icf_lookup`: Get details for a specific code
- `icf_search`: Find codes by keyword
- `icf_browse_category`: Explore a category
- `icf_get_children`: Get subcodes
- `icf_explain_qualifier`: Understand severity ratings

## More Information

ICF official site: https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health
"""


# =============================================================================
# Main entry point
# =============================================================================

def main():
    """Main entry point for the ICF MCP server"""
    logger.info("Starting ICF MCP Server")
    mcp.run()


if __name__ == "__main__":
    main()
