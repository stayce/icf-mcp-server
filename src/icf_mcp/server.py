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
from typing import Any

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
    Browse an ICF category or sub-chapter to explore available codes.

    Accepts top-level components or sub-chapter codes:
    - "b", "s", "d", "e": Top-level components
    - "b1": Mental functions chapter
    - "b2": Sensory functions and pain
    - "d4": Mobility chapter
    - "e1": Products and technology
    - Any valid sub-chapter code (e.g., "b1", "s7", "d45", "e3")

    Args:
        category: Component letter (b, s, d, e) or sub-chapter code (b1, d4, etc.)

    Returns:
        Overview of the category/sub-chapter with child codes.
    """
    client = get_client()

    try:
        result = await client.browse_category(category)

        lines = [
            f"**ICF Category: {result['name']}** (codes starting with '{result['category']}')",
            "",
            result["description"],
            "",
        ]

        if result["results"]:
            lines.append("**Codes in this category:**")
            for item in result["results"][:20]:
                lines.append(f"  - **{item['code']}**: {item['title']}")
        else:
            lines.append("*No child codes found — this may be a leaf-level code.*")

        lines.append(f"\nUse `icf_get_children` to drill deeper, or `icf_lookup` for full details.")

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
async def icf_explain_qualifier(component: str = "generic", qualifier: int | None = None) -> str:
    """
    Explain ICF qualifier systems. Each ICF component uses different qualifiers.

    ICF qualifier types vary by component:
    - Body Functions (b): 1 qualifier — extent of impairment (0-4)
    - Body Structures (s): 3 qualifiers — extent, nature of change, location
    - Activities & Participation (d): 2 qualifiers — performance, capacity
    - Environmental Factors (e): 1 qualifier — barrier (0-4) or facilitator (+0 to +4)

    Args:
        component: Component to explain qualifiers for. One of:
            "generic" (default severity scale), "b" (body functions),
            "s" (body structures), "d" (activities & participation),
            "e" (environmental factors)
        qualifier: Optional specific qualifier value to explain (0-9).
            If omitted, shows all qualifiers for the component.

    Returns:
        Explanation of qualifier system for the specified component.
    """
    # Generic severity scale (used as the 1st qualifier across b, s, d)
    generic_scale = {
        0: ("No problem", "0-4%", "None, absent, negligible"),
        1: ("Mild problem", "5-24%", "Slight, low"),
        2: ("Moderate problem", "25-49%", "Medium, fair"),
        3: ("Severe problem", "50-95%", "High, extreme"),
        4: ("Complete problem", "96-100%", "Total"),
        8: ("Not specified", "N/A", "Insufficient information to specify"),
        9: ("Not applicable", "N/A", "Inappropriate to apply"),
    }

    comp = component.strip().lower()

    if comp == "generic" or comp == "b":
        label = "Body Functions (b) — Extent of Impairment" if comp == "b" else "Generic Severity Scale"
        if qualifier is not None:
            if qualifier not in generic_scale:
                return f"Invalid qualifier value '{qualifier}'. Valid: 0-4, 8, 9."
            level, pct, desc = generic_scale[qualifier]
            example = f"b280.{qualifier}" if comp == "b" else f"d450.{qualifier}"
            return (
                f"**{label} — Qualifier {qualifier}: {level}**\n\n"
                f"- **Percentage range:** {pct}\n"
                f"- **Description:** {desc}\n\n"
                f"Example: {example} means '{level.lower()}'."
            )
        lines = [f"**{label}**\n"]
        for val, (level, pct, desc) in generic_scale.items():
            lines.append(f"- **{val}**: {level} ({pct}) — {desc}")
        if comp == "b":
            lines.append("\nBody Functions use a single qualifier: b280.**2** = moderate impairment.")
        return "\n".join(lines)

    if comp == "s":
        nature_of_change = {
            0: "No change in structure",
            1: "Total absence",
            2: "Partial absence",
            3: "Additional part",
            4: "Aberrant dimensions",
            5: "Discontinuity",
            6: "Deviating position",
            7: "Qualitative changes in structure",
            8: "Not specified",
            9: "Not applicable",
        }
        location = {
            0: "More than one region",
            1: "Right",
            2: "Left",
            3: "Both sides",
            4: "Front",
            5: "Back",
            6: "Proximal",
            7: "Distal",
            8: "Not specified",
            9: "Not applicable",
        }
        lines = [
            "**Body Structures (s) — 3 Qualifiers**\n",
            "Body Structure codes use three qualifiers: `s{code}.{extent}{nature}{location}`\n",
            "Example: **s730.312** = structure of lower extremity, severe impairment (3),",
            "total absence (1), right side (2)\n",
            "### 1st Qualifier: Extent of Impairment\n",
        ]
        for val, (level, pct, desc) in generic_scale.items():
            lines.append(f"- **{val}**: {level} ({pct})")
        lines.append("\n### 2nd Qualifier: Nature of Change\n")
        for val, desc in nature_of_change.items():
            lines.append(f"- **{val}**: {desc}")
        lines.append("\n### 3rd Qualifier: Location\n")
        for val, desc in location.items():
            lines.append(f"- **{val}**: {desc}")
        return "\n".join(lines)

    if comp == "d":
        lines = [
            "**Activities & Participation (d) — 2 Qualifiers**\n",
            "Activity/Participation codes use two qualifiers: `d{code}.{performance}{capacity}`\n",
            "- **Performance**: what a person *does* in their current environment",
            "- **Capacity**: what a person *can do* in a standardized environment\n",
            "Example: **d450.23** = walking, moderate difficulty in performance (2),",
            "severe limitation in capacity (3)\n",
            "### Both qualifiers use the standard severity scale:\n",
        ]
        for val, (level, pct, desc) in generic_scale.items():
            lines.append(f"- **{val}**: {level} ({pct})")
        return "\n".join(lines)

    if comp == "e":
        barrier_scale = {
            0: ("No barrier", "0-4%"),
            1: ("Mild barrier", "5-24%"),
            2: ("Moderate barrier", "25-49%"),
            3: ("Severe barrier", "50-95%"),
            4: ("Complete barrier", "96-100%"),
        }
        facilitator_scale = {
            0: ("No facilitator", "0-4%"),
            1: ("Mild facilitator", "5-24%"),
            2: ("Moderate facilitator", "25-49%"),
            3: ("Substantial facilitator", "50-95%"),
            4: ("Complete facilitator", "96-100%"),
        }
        lines = [
            "**Environmental Factors (e) — 1 Qualifier (Barrier or Facilitator)**\n",
            "Environmental codes use a single qualifier with two directions:\n",
            "- **Barriers** use a dot: `e{code}.{value}` (e.g., e120.2 = moderate barrier)",
            "- **Facilitators** use a plus: `e{code}+{value}` (e.g., e120+3 = substantial facilitator)\n",
            "### Barrier Scale (negative influence)\n",
        ]
        for val, (level, pct) in barrier_scale.items():
            lines.append(f"- **.{val}**: {level} ({pct})")
        lines.append("\n### Facilitator Scale (positive influence)\n")
        for val, (level, pct) in facilitator_scale.items():
            lines.append(f"- **+{val}**: {level} ({pct})")
        lines.append("\n- **8**: Not specified")
        lines.append("- **9**: Not applicable")
        return "\n".join(lines)

    return (
        f"Unknown component '{component}'. Valid values:\n"
        f"- `generic`: Standard severity scale (default)\n"
        f"- `b`: Body Functions (1 qualifier)\n"
        f"- `s`: Body Structures (3 qualifiers)\n"
        f"- `d`: Activities & Participation (2 qualifiers)\n"
        f"- `e`: Environmental Factors (barrier/facilitator)"
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

Each component has its own qualifier system:

**Body Functions (b):** 1 qualifier — extent of impairment (0-4)
  Example: b280.2 = moderate pain impairment

**Body Structures (s):** 3 qualifiers — extent, nature of change, location
  Example: s730.312 = severe extent, total absence, right side

**Activities & Participation (d):** 2 qualifiers — performance, capacity
  Example: d450.23 = moderate performance difficulty, severe capacity limitation

**Environmental Factors (e):** barriers (.) or facilitators (+)
  Example: e120.2 = moderate barrier; e120+3 = substantial facilitator

Generic severity scale (0-4): 0=none, 1=mild, 2=moderate, 3=severe, 4=complete

## Tools Available

- `icf_lookup`: Get details for a specific code
- `icf_search`: Find codes by keyword
- `icf_browse_category`: Explore a category or sub-chapter (b, d4, e3, etc.)
- `icf_get_children`: Get subcodes of a code
- `icf_get_parent`: Navigate up to a code's parent category
- `icf_get_siblings`: Find related codes at the same level
- `icf_get_code_chain`: Show the full hierarchy path from root to a code
- `icf_validate_code`: Validate a code with qualifier support
- `icf_parse_qualified_code`: Parse qualified codes (d450.23, s730.312, e120+3)
- `icf_build_profile`: Build a functional profile from multiple codes
- `icf_explain_qualifier`: Component-specific qualifier reference

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


# =============================================================================
# Qualifier parsing helpers
# =============================================================================

# Component names
_COMPONENTS = {
    "b": "Body Functions",
    "s": "Body Structures",
    "d": "Activities and Participation",
    "e": "Environmental Factors",
}

# Hierarchy level names
_LEVELS = {
    1: "Chapter (1st level)",
    2: "Block (2nd level)",
    3: "Category (3rd level)",
    4: "Subcategory (4th level)",
}

# Generic severity scale (used by b, s-1st, d-performance, d-capacity)
_GENERIC_SCALE = {
    0: "No problem (0-4%)",
    1: "Mild problem (5-24%)",
    2: "Moderate problem (25-49%)",
    3: "Severe problem (50-95%)",
    4: "Complete problem (96-100%)",
    8: "Not specified",
    9: "Not applicable",
}

# Body Structures — 2nd qualifier: nature of change
_NATURE_OF_CHANGE = {
    0: "No change in structure",
    1: "Total absence",
    2: "Partial absence",
    3: "Additional part",
    4: "Aberrant dimensions",
    5: "Discontinuity",
    6: "Deviating position",
    7: "Qualitative changes in structure",
    8: "Not specified",
    9: "Not applicable",
}

# Body Structures — 3rd qualifier: location
_LOCATION = {
    0: "More than one region",
    1: "Right",
    2: "Left",
    3: "Both sides",
    4: "Front",
    5: "Back",
    6: "Proximal",
    7: "Distal",
    8: "Not specified",
    9: "Not applicable",
}

# Environmental Factors — barrier scale
_BARRIER_SCALE = {
    0: "No barrier (0-4%)",
    1: "Mild barrier (5-24%)",
    2: "Moderate barrier (25-49%)",
    3: "Severe barrier (50-95%)",
    4: "Complete barrier (96-100%)",
    8: "Not specified",
    9: "Not applicable",
}

# Environmental Factors — facilitator scale
_FACILITATOR_SCALE = {
    0: "No facilitator (0-4%)",
    1: "Mild facilitator (5-24%)",
    2: "Moderate facilitator (25-49%)",
    3: "Substantial facilitator (50-95%)",
    4: "Complete facilitator (96-100%)",
    8: "Not specified",
    9: "Not applicable",
}


def _parse_icf_code(raw: str) -> dict[str, Any]:
    """
    Parse a raw ICF code string (with or without qualifiers) into its components.

    Supports formats:
        b280, d450.2, d450.23, s730.312, e120.2, e120+3

    Returns a dict with keys:
        base_code, component, component_name, digits, level,
        qualifier_str, separator, is_facilitator, qualifiers (list of dicts),
        error (str or None)
    """
    raw = raw.strip()

    # Full pattern: component + digits + optional separator + qualifier digits
    # Separators: "." for barriers/impairments, "+" for facilitators
    pattern = r'^([bBsSdDeE])(\d{1,4})(?:([.+])(\d+))?$'
    match = re.match(pattern, raw)

    if not match:
        return {"error": (
            f"'{raw}' does not match ICF code format.\n\n"
            f"**Base code:** `[bsde]` + 1-4 digits (e.g., b280, d450)\n"
            f"**With qualifiers:** code + `.` or `+` + qualifier digits\n"
            f"  - b280.2 (body function, moderate impairment)\n"
            f"  - d450.23 (activity, performance=2, capacity=3)\n"
            f"  - s730.312 (structure, extent=3, nature=1, location=2)\n"
            f"  - e120.2 (environment, moderate barrier)\n"
            f"  - e120+3 (environment, substantial facilitator)"
        )}

    component = match.group(1).lower()
    digits = match.group(2)
    separator = match.group(3)  # "." or "+" or None
    qualifier_str = match.group(4)  # "2", "23", "312", or None

    base_code = f"{component}{digits}"
    component_name = _COMPONENTS[component]
    level = _LEVELS.get(len(digits), "Unknown")
    is_facilitator = separator == "+"

    result: dict[str, Any] = {
        "base_code": base_code,
        "component": component,
        "component_name": component_name,
        "digits": digits,
        "level": level,
        "qualifier_str": qualifier_str,
        "separator": separator,
        "is_facilitator": is_facilitator,
        "qualifiers": [],
        "error": None,
    }

    if not qualifier_str:
        return result

    # Parse qualifiers based on component
    qdigits = [int(d) for d in qualifier_str]

    if component == "b":
        # Body Functions: 1 qualifier (extent of impairment)
        if len(qdigits) > 1:
            result["error"] = (
                f"Body Functions (b) use 1 qualifier: extent of impairment. "
                f"Got {len(qdigits)} digits ('{qualifier_str}')."
            )
            return result
        result["qualifiers"] = [
            {"name": "Extent of impairment", "value": qdigits[0],
             "meaning": _GENERIC_SCALE.get(qdigits[0], "Unknown")}
        ]

    elif component == "s":
        # Body Structures: up to 3 qualifiers
        if len(qdigits) > 3:
            result["error"] = (
                f"Body Structures (s) use up to 3 qualifiers. "
                f"Got {len(qdigits)} digits ('{qualifier_str}')."
            )
            return result
        scales = [
            ("Extent of impairment", _GENERIC_SCALE),
            ("Nature of change", _NATURE_OF_CHANGE),
            ("Location", _LOCATION),
        ]
        for i, val in enumerate(qdigits):
            name, scale = scales[i]
            result["qualifiers"].append({
                "name": name, "value": val,
                "meaning": scale.get(val, "Unknown"),
            })

    elif component == "d":
        # Activities & Participation: up to 2 qualifiers
        if len(qdigits) > 2:
            result["error"] = (
                f"Activities & Participation (d) use up to 2 qualifiers. "
                f"Got {len(qdigits)} digits ('{qualifier_str}')."
            )
            return result
        names = ["Performance", "Capacity"]
        for i, val in enumerate(qdigits):
            result["qualifiers"].append({
                "name": names[i], "value": val,
                "meaning": _GENERIC_SCALE.get(val, "Unknown"),
            })

    elif component == "e":
        # Environmental Factors: 1 qualifier (barrier or facilitator)
        if len(qdigits) > 1:
            result["error"] = (
                f"Environmental Factors (e) use 1 qualifier. "
                f"Got {len(qdigits)} digits ('{qualifier_str}')."
            )
            return result
        scale = _FACILITATOR_SCALE if is_facilitator else _BARRIER_SCALE
        label = "Facilitator" if is_facilitator else "Barrier"
        result["qualifiers"] = [
            {"name": label, "value": qdigits[0],
             "meaning": scale.get(qdigits[0], "Unknown")}
        ]

    return result


@mcp.tool()
async def icf_validate_code(code: str) -> str:
    """
    Validate an ICF code — check format, qualifiers, and verify it exists.

    Supports both base codes and fully qualified codes with qualifiers:
    - Base: "b280", "d4501"
    - Qualified: "b280.2", "d450.23", "s730.312", "e120+3"

    Args:
        code: ICF code to validate (e.g., "b280", "d450.23", "s730.312")

    Returns:
        Code analysis with format validation, qualifier breakdown, and API verification.
    """
    parsed = _parse_icf_code(code)

    if parsed.get("error") and "base_code" not in parsed:
        return parsed["error"]

    base_code = parsed["base_code"]
    component = parsed["component"]
    component_name = parsed["component_name"]
    level = parsed["level"]
    digits = parsed["digits"]

    lines = [
        f"**Code Analysis: {code.strip()}**\n",
        f"- **Base code:** {base_code}",
        f"- **Component:** {component_name} ({component})",
        f"- **Level:** {level}",
        f"- **Chapter:** {component}{digits[0]}",
    ]

    # Show qualifier breakdown
    if parsed.get("error"):
        lines.append(f"\n**Qualifier error:** {parsed['error']}")
    elif parsed["qualifiers"]:
        lines.append("\n**Qualifiers:**")
        for q in parsed["qualifiers"]:
            lines.append(f"- **{q['name']}:** {q['value']} — {q['meaning']}")

    # Verify base code against the WHO API
    client = get_client()
    try:
        entity = await client.get_entity_by_code(base_code)
        if entity:
            lines.append(f"\n**Valid:** Base code confirmed in WHO ICD-API.")
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
async def icf_parse_qualified_code(code: str) -> str:
    """
    Parse a fully qualified ICF code and explain each qualifier component.

    Qualified ICF codes encode severity/characteristics after the base code:
    - b280.2 → Body Functions: moderate impairment
    - d450.23 → Activities: performance=moderate, capacity=severe
    - s730.312 → Structures: severe extent, total absence, right side
    - e120.2 → Environment: moderate barrier
    - e120+3 → Environment: substantial facilitator

    Args:
        code: Fully qualified ICF code (e.g., "d450.23", "s730.312", "e120+3")

    Returns:
        Detailed breakdown of the code and all qualifier values.
    """
    parsed = _parse_icf_code(code)

    if parsed.get("error") and "base_code" not in parsed:
        return parsed["error"]

    base_code = parsed["base_code"]
    component_name = parsed["component_name"]

    lines = [f"**Parsed: {code.strip()}**\n"]

    # Look up the base code
    client = get_client()
    try:
        entity = await client.get_entity_by_code(base_code)
        if entity:
            lines.append(f"**{base_code}**: {entity.title}")
            if entity.definition:
                lines.append(f"_{entity.definition}_\n")
            else:
                lines.append("")
        else:
            lines.append(f"**{base_code}**: *(not found in WHO API)*\n")
    except Exception:
        lines.append(f"**{base_code}**: *(could not verify)*\n")

    lines.append(f"**Component:** {component_name}")

    if parsed.get("error"):
        lines.append(f"\n**Qualifier error:** {parsed['error']}")
    elif parsed["qualifiers"]:
        lines.append(f"\n**Qualifiers:**\n")
        for q in parsed["qualifiers"]:
            lines.append(f"- **{q['name']}** (value {q['value']}): {q['meaning']}")
    else:
        lines.append("\n*No qualifiers specified. Use `icf_explain_qualifier` "
                     f"with component=\"{parsed['component']}\" to see available qualifiers.*")

    # Show the expected qualifier pattern for this component
    patterns = {
        "b": "b{code}.{extent}",
        "s": "s{code}.{extent}{nature}{location}",
        "d": "d{code}.{performance}{capacity}",
        "e": "e{code}.{barrier}  or  e{code}+{facilitator}",
    }
    lines.append(f"\n**Qualifier format for {component_name}:** `{patterns[parsed['component']]}`")

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
