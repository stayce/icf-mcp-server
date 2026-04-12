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
import re
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
- `icf_get_children`: Get subcodes of a code
- `icf_get_parent`: Navigate up to a code's parent category
- `icf_get_siblings`: Find related codes at the same level
- `icf_get_code_chain`: Show the full hierarchy path from root to a code
- `icf_validate_code`: Check if a code is valid
- `icf_build_profile`: Build a functional profile from multiple codes
- `icf_explain_qualifier`: Understand severity ratings

## More Information

ICF official site: https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health
"""


@mcp.tool()
async def icf_get_parent(code: str) -> str:
    """
    Get the parent category of an ICF code to navigate up the hierarchy.

    ICF codes are hierarchical. Use this to move from a specific code up to
    its broader category. For example:
    - d4501 → d450 (Walking)
    - d450 → d45 (Walking and moving)
    - d45 → d4 (Mobility)

    Args:
        code: ICF code to find the parent of (e.g., "d450", "b2801")

    Returns:
        Parent code details and the relationship to the child code.
    """
    client = get_client()

    try:
        entity, parent = await client.get_parent(code)

        if entity is None:
            return f"ICF code '{code}' not found. Please check the code format."

        if parent is None:
            return (
                f"**{entity.code}**: {entity.title}\n\n"
                f"This is a top-level code with no parent category."
            )

        lines = [
            f"**Parent of {entity.code} ({entity.title}):**\n",
            format_entity(parent),
        ]

        if parent.children:
            lines.append(f"\n*{parent.code} has {len(parent.children)} child code(s). "
                         f"Use `icf_get_children` on '{parent.code}' to see all.*")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error getting parent for ICF code {code}: {e}")
        return f"Error getting parent: {str(e)}"


@mcp.tool()
async def icf_get_siblings(code: str) -> str:
    """
    Get sibling codes — other codes at the same level sharing the same parent.

    Useful for finding related or alternative codes. For example, siblings of
    d450 (Walking) include d455 (Moving around) and d460 (Moving around in
    different locations).

    Args:
        code: ICF code to find siblings for (e.g., "d450", "b280")

    Returns:
        List of sibling codes with titles.
    """
    client = get_client()

    try:
        entity, siblings = await client.get_siblings(code)

        if entity is None:
            return f"ICF code '{code}' not found. Please check the code format."

        if not siblings:
            return (
                f"**{entity.code}**: {entity.title}\n\n"
                f"No sibling codes found (this may be the only child of its parent)."
            )

        lines = [
            f"**Siblings of {entity.code} ({entity.title}):**\n",
        ]

        for sibling in siblings:
            lines.append(f"- **{sibling.code}**: {sibling.title}")

        lines.append(f"\n*{len(siblings)} sibling(s) found.*")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error getting siblings for ICF code {code}: {e}")
        return f"Error getting siblings: {str(e)}"


@mcp.tool()
async def icf_validate_code(code: str) -> str:
    """
    Validate an ICF code — check its format and verify it exists in the WHO API.

    Returns a structural breakdown of the code (component, level, chapter)
    and confirms whether it is a valid, recognized ICF code.

    Args:
        code: ICF code to validate (e.g., "b280", "d4501", "xyz")

    Returns:
        Code analysis with format validation and API verification.
    """
    code_clean = code.strip().lower()

    # Basic format check
    pattern = r'^([bsde])(\d{1,4})$'
    match = re.match(pattern, code_clean)

    if not match:
        return (
            f"'{code}' does not match ICF code format.\n\n"
            f"ICF codes consist of:\n"
            f"- A letter prefix: b (Body Functions), s (Body Structures), "
            f"d (Activities and Participation), e (Environmental Factors)\n"
            f"- 1 to 4 digits\n\n"
            f"Examples: b1 (chapter), b280 (category), d4501 (subcategory)"
        )

    component_letter = match.group(1)
    digits = match.group(2)

    components = {
        "b": "Body Functions",
        "s": "Body Structures",
        "d": "Activities and Participation",
        "e": "Environmental Factors",
    }

    levels = {
        1: "Chapter (1st level)",
        2: "Block (2nd level)",
        3: "Category (3rd level)",
        4: "Subcategory (4th level)",
    }

    level = levels.get(len(digits), "Unknown")
    component = components[component_letter]

    lines = [
        f"**Code Analysis: {code_clean}**\n",
        f"- **Component:** {component} ({component_letter})",
        f"- **Level:** {level}",
        f"- **Chapter:** {component_letter}{digits[0]}",
    ]

    # Verify against the WHO API
    client = get_client()
    try:
        entity = await client.get_entity_by_code(code_clean)
        if entity:
            lines.append(f"\n**Valid:** Confirmed in WHO ICD-API.")
            lines.append(f"- **Title:** {entity.title}")
            if entity.definition:
                lines.append(f"- **Definition:** {entity.definition}")
            if entity.children:
                lines.append(f"- **Children:** {len(entity.children)} subcategory code(s)")
        else:
            lines.append(
                f"\n**Not found** in the WHO API. The format is valid but this "
                f"code may not exist in the current release."
            )
    except Exception:
        lines.append(f"\n**Could not verify** against the WHO API.")

    return "\n".join(lines)


@mcp.tool()
async def icf_build_profile(codes: list[str]) -> str:
    """
    Build an ICF functional profile from multiple codes.

    Creates a structured summary organizing multiple ICF codes by component,
    useful for documenting a person's functional status across body functions,
    structures, activities, and environmental factors.

    Args:
        codes: List of ICF codes (e.g., ["b280", "d450", "e120"])

    Returns:
        Structured ICF profile organized by component.
    """
    if not codes:
        return "No codes provided. Pass a list of ICF codes (e.g., [\"b280\", \"d450\"])."

    client = get_client()

    components: dict[str, dict] = {
        "b": {"name": "Body Functions", "items": []},
        "s": {"name": "Body Structures", "items": []},
        "d": {"name": "Activities and Participation", "items": []},
        "e": {"name": "Environmental Factors", "items": []},
    }

    not_found: list[str] = []

    for code in codes:
        code_clean = code.strip().lower()
        try:
            entity = await client.get_entity_by_code(code_clean)
            if entity:
                prefix = code_clean[0]
                if prefix in components:
                    components[prefix]["items"].append(entity)
                else:
                    not_found.append(code)
            else:
                not_found.append(code)
        except Exception:
            not_found.append(code)

    lines = ["**ICF Functional Profile**\n"]

    for comp in components.values():
        if comp["items"]:
            lines.append(f"\n### {comp['name']}\n")
            for entity in comp["items"]:
                lines.append(f"- **{entity.code}**: {entity.title}")
                if entity.definition:
                    lines.append(f"  _{entity.definition}_")

    if not_found:
        lines.append(f"\n**Codes not found:** {', '.join(not_found)}")

    total = sum(len(c["items"]) for c in components.values())
    active = sum(1 for c in components.values() if c["items"])
    lines.append(f"\n---\n*Profile contains {total} code(s) across {active} component(s).*")

    return "\n".join(lines)


@mcp.tool()
async def icf_get_code_chain(code: str) -> str:
    """
    Show the full hierarchical path from the ICF root down to a specific code.

    Displays the complete classification chain as a breadcrumb trail, useful for
    understanding where a code sits in the overall ICF structure. For example,
    d4501 might show: Activities and Participation → Mobility → Walking and
    moving → Walking → Walking long distances.

    Args:
        code: ICF code to trace (e.g., "b2801", "d4501")

    Returns:
        Hierarchical chain from root to the specified code.
    """
    client = get_client()

    try:
        chain = await client.get_code_chain(code)

        if not chain:
            return f"ICF code '{code}' not found. Please check the code format."

        if len(chain) == 1:
            entity = chain[0]
            return f"**{entity.code}**: {entity.title}\n\nThis is a top-level code."

        lines = [f"**Hierarchy for {code}:**\n"]

        for i, entity in enumerate(chain):
            indent = "  " * i
            if i == len(chain) - 1:
                # Final (target) code — show full details
                lines.append(f"{indent}→ **{entity.code}**: {entity.title}")
                if entity.definition:
                    lines.append(f"{indent}  _{entity.definition}_")
            else:
                lines.append(f"{indent}→ {entity.code}: {entity.title}")

        lines.append(f"\n*{len(chain)} level(s) deep.*")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error getting code chain for {code}: {e}")
        return f"Error getting code chain: {str(e)}"


# =============================================================================
# Main entry point
# =============================================================================

def main():
    """Main entry point for the ICF MCP server"""
    logger.info("Starting ICF MCP Server")
    mcp.run()


if __name__ == "__main__":
    main()
