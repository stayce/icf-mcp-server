"""
ICF MCP Server - International Classification of Functioning, Disability and Health

A Model Context Protocol (MCP) server that provides tools for accessing
the WHO ICF classification system.
"""

from .server import main, mcp
from .who_client import WHOICFClient, ICFEntity, ICFSearchResult

__version__ = "0.1.0"
__all__ = [
    "main",
    "mcp", 
    "WHOICFClient",
    "ICFEntity",
    "ICFSearchResult",
]
