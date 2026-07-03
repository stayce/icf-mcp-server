"""
WHO ICD-API Client for ICF (International Classification of Functioning, Disability and Health)

This module handles authentication and API calls to the WHO ICD-API to access ICF data.
API Documentation: https://icd.who.int/docs/icd-api/APIDoc-Version2/
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# WHO ICD-API endpoints
TOKEN_ENDPOINT = "https://icdaccessmanagement.who.int/connect/token"
API_BASE_URL = "https://id.who.int"

# ICF linearization name in the API
ICF_LINEARIZATION = "icf"

# Default API version
DEFAULT_RELEASE = "2025-01"

# ICF component letter → component name
CATEGORY_NAMES = {
    "b": "Body Functions",
    "s": "Body Structures",
    "d": "Activities and Participation",
    "e": "Environmental Factors",
}


@dataclass
class ICFEntity:
    """Represents an ICF entity (code, category, or item)"""
    code: str
    title: str
    definition: str | None = None
    inclusions: list[str] | None = None
    exclusions: list[str] | None = None
    parent: str | None = None
    children: list[str] | None = None
    uri: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "definition": self.definition,
            "inclusions": self.inclusions,
            "exclusions": self.exclusions,
            "parent": self.parent,
            "children": self.children,
            "uri": self.uri,
        }


@dataclass 
class ICFSearchResult:
    """Represents a search result from the ICF API"""
    code: str
    title: str
    score: float
    uri: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "score": self.score,
            "uri": self.uri,
        }


class WHOICFClient:
    """
    Client for the WHO ICD-API to access ICF data.
    
    Requires registration at https://icd.who.int/icdapi to obtain
    client_id and client_secret credentials.
    """
    
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        release: str = DEFAULT_RELEASE,
        language: str = "en",
    ):
        """
        Initialize the WHO ICF API client.
        
        Args:
            client_id: WHO ICD-API client ID (from https://icd.who.int/icdapi)
            client_secret: WHO ICD-API client secret
            release: API release version (e.g., "2025-01")
            language: Language code (e.g., "en", "es", "fr")
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.release = release
        self.language = language
        self._access_token: str | None = None
        self._http_client: httpx.AsyncClient | None = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def _ensure_token(self) -> str:
        """Ensure we have a valid access token"""
        if self._access_token is None:
            await self._authenticate()
        return self._access_token  # type: ignore
    
    async def _authenticate(self) -> None:
        """Authenticate with the WHO ICD-API using OAuth2 client credentials"""
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "WHO ICD-API credentials required. "
                "Register at https://icd.who.int/icdapi to obtain credentials."
            )
        
        client = await self._get_http_client()
        
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "icdapi_access",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
        
        data = response.json()
        self._access_token = data["access_token"]
        logger.info("Successfully authenticated with WHO ICD-API")
    
    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "Accept-Language": self.language,
            "API-Version": "v2",
        }
    
    async def _api_request(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make an authenticated API request"""
        await self._ensure_token()
        client = await self._get_http_client()
        
        url = f"{API_BASE_URL}{endpoint}"
        
        response = await client.get(url, headers=self._get_headers(), params=params)
        
        if response.status_code == 401:
            # Token expired, re-authenticate
            self._access_token = None
            await self._ensure_token()
            response = await client.get(url, headers=self._get_headers(), params=params)
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def get_icf_root(self) -> dict[str, Any]:
        """Get the root of the ICF classification"""
        endpoint = f"/icd/release/11/{self.release}/{ICF_LINEARIZATION}"
        return await self._api_request(endpoint)
    
    async def get_entity_by_code(self, code: str) -> ICFEntity | None:
        """
        Get an ICF entity by its code.

        Args:
            code: ICF code (e.g., "b280" for sensation of pain)

        Returns:
            ICFEntity or None if not found
        """
        # First use codeinfo to get the stemId for this code
        codeinfo_endpoint = f"/icd/release/11/{self.release}/{ICF_LINEARIZATION}/codeinfo/{code}"

        try:
            codeinfo = await self._api_request(codeinfo_endpoint)
            stem_id = codeinfo.get("stemId")
            if not stem_id:
                logger.warning(f"No stemId found for ICF code {code}")
                return None

            # Fetch the full entity using the stemId
            return await self.get_entity_by_uri(stem_id)
        except Exception as e:
            logger.warning(f"Failed to get ICF entity {code}: {e}")
            return None
    
    async def get_entity_by_uri(self, uri: str) -> ICFEntity | None:
        """
        Get an ICF entity by its URI.
        
        Args:
            uri: Full URI of the entity
            
        Returns:
            ICFEntity or None if not found
        """
        # Convert URI to endpoint path
        if uri.startswith("http://"):
            uri = uri.replace("http://", "https://")
        
        endpoint = uri.replace(API_BASE_URL, "")
        
        try:
            data = await self._api_request(endpoint)
            return self._parse_entity(data)
        except Exception as e:
            logger.warning(f"Failed to get ICF entity by URI {uri}: {e}")
            return None
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        flat_results: bool = True,
    ) -> list[ICFSearchResult]:
        """
        Search the ICF classification.
        
        Args:
            query: Search query text
            max_results: Maximum number of results to return
            flat_results: If True, return flat list; if False, include hierarchy
            
        Returns:
            List of search results
        """
        endpoint = f"/icd/release/11/{self.release}/{ICF_LINEARIZATION}/search"
        params = {
            "q": query,
            "useFlexisearch": "true",
            "flatResults": str(flat_results).lower(),
            "highlightingEnabled": "false",
        }
        
        data = await self._api_request(endpoint, params)
        
        results = []
        for item in data.get("destinationEntities", [])[:max_results]:
            results.append(ICFSearchResult(
                code=item.get("theCode", ""),
                title=item.get("title", ""),
                score=item.get("score", 0.0),
                uri=item.get("id", ""),
            ))
        
        return results
    
    async def get_children(self, code: str) -> list[ICFEntity]:
        """
        Get child entities of an ICF code.
        
        Args:
            code: Parent ICF code
            
        Returns:
            List of child entities
        """
        entity = await self.get_entity_by_code(code)
        if not entity or not entity.children:
            return []

        fetched = await asyncio.gather(
            *(self.get_entity_by_uri(uri) for uri in entity.children)
        )
        return [child for child in fetched if child]
    
    async def browse_category(self, category: str) -> dict[str, Any]:
        """
        Browse an ICF category or sub-chapter.

        Accepts top-level components (b, s, d, e) or sub-chapters (b1, d4, e3, etc.).

        Args:
            category: Category code — single letter (b, s, d, e) or sub-chapter (b1, d4, etc.)

        Returns:
            Dictionary with category info and children/results
        """
        cat = category.strip().lower()

        # Check if this is a sub-chapter (e.g., "b1", "d4", "e3")
        sub_match = re.match(r'^([bsde])(\d{1,3})$', cat)

        if sub_match:
            # Sub-chapter browsing — use entity lookup + children
            component_name = CATEGORY_NAMES[sub_match.group(1)]

            entity = await self.get_entity_by_code(cat)
            if not entity:
                raise ValueError(
                    f"Sub-chapter '{cat}' not found in the WHO API. "
                    f"Try a top-level category ({', '.join(CATEGORY_NAMES.keys())}) "
                    f"or a valid sub-chapter code."
                )

            children = []
            if entity.children:
                fetched = await asyncio.gather(
                    *(self.get_entity_by_uri(uri) for uri in entity.children)
                )
                children = [c for c in fetched if c]

            return {
                "category": cat,
                "name": f"{entity.title} ({component_name})",
                "description": entity.definition or f"Sub-chapter {cat} under {component_name}.",
                "results": [
                    {"code": c.code, "title": c.title, "score": 0.0, "uri": c.uri or ""}
                    for c in children
                ],
            }

        if cat not in CATEGORY_NAMES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Use a component letter ({', '.join(CATEGORY_NAMES.keys())}) "
                f"or a sub-chapter code (e.g., b1, d4, e3)."
            )

        # Top-level category browsing — use search
        results = await self.search(CATEGORY_NAMES[cat], max_results=20)

        return {
            "category": cat,
            "name": CATEGORY_NAMES[cat],
            "description": self._get_category_description(cat),
            "results": [r.to_dict() for r in results],
        }
    
    def _get_category_description(self, category: str) -> str:
        """Get description for an ICF category"""
        descriptions = {
            "b": (
                "Body Functions are the physiological functions of body systems "
                "(including psychological functions). Codes range from b1 to b8."
            ),
            "s": (
                "Body Structures are anatomical parts of the body such as organs, "
                "limbs and their components. Codes range from s1 to s8."
            ),
            "d": (
                "Activities and Participation covers the execution of tasks and "
                "involvement in life situations. Codes range from d1 to d9."
            ),
            "e": (
                "Environmental Factors make up the physical, social and attitudinal "
                "environment in which people live. Codes range from e1 to e5."
            ),
        }
        return descriptions.get(category, "")
    
    def _parse_entity(self, data: dict[str, Any]) -> ICFEntity:
        """Parse API response into an ICFEntity"""
        # Extract code from the response
        code = data.get("code", data.get("theCode", ""))
        
        # Get title - handle different response formats
        title = data.get("title", {})
        if isinstance(title, dict):
            title = title.get("@value", str(title))
        
        # Get definition
        definition = data.get("definition", {})
        if isinstance(definition, dict):
            definition = definition.get("@value", None)
        
        # Get inclusions
        inclusions = None
        if "inclusion" in data:
            inc_data = data["inclusion"]
            if isinstance(inc_data, list):
                inclusions = [
                    i.get("label", {}).get("@value", str(i)) 
                    if isinstance(i, dict) else str(i)
                    for i in inc_data
                ]
        
        # Get exclusions
        exclusions = None
        if "exclusion" in data:
            exc_data = data["exclusion"]
            if isinstance(exc_data, list):
                exclusions = [
                    e.get("label", {}).get("@value", str(e))
                    if isinstance(e, dict) else str(e)
                    for e in exc_data
                ]
        
        # Get parent
        parent = None
        if "parent" in data:
            parent_data = data["parent"]
            if isinstance(parent_data, list) and len(parent_data) > 0:
                parent = parent_data[0]
            elif isinstance(parent_data, str):
                parent = parent_data
        
        # Get children
        children = data.get("child", None)
        if isinstance(children, str):
            children = [children]
        
        return ICFEntity(
            code=code,
            title=title,
            definition=definition,
            inclusions=inclusions,
            exclusions=exclusions,
            parent=parent,
            children=children,
            uri=data.get("@id", data.get("id", None)),
        )
    
    async def get_parent(self, code: str) -> tuple[ICFEntity | None, ICFEntity | None]:
        """
        Get an ICF entity and its parent.

        Args:
            code: ICF code (e.g., "b280")

        Returns:
            Tuple of (entity, parent_entity). Either may be None.
        """
        entity = await self.get_entity_by_code(code)
        if not entity or not entity.parent:
            return entity, None

        parent = await self.get_entity_by_uri(entity.parent)
        return entity, parent

    async def get_siblings(self, code: str) -> tuple[ICFEntity | None, list[ICFEntity]]:
        """
        Get sibling entities of an ICF code (other children of the same parent).

        Args:
            code: ICF code (e.g., "b280")

        Returns:
            Tuple of (entity, list_of_siblings). Entity may be None.
        """
        entity = await self.get_entity_by_code(code)
        if not entity or not entity.parent:
            return entity, []

        parent = await self.get_entity_by_uri(entity.parent)
        if not parent or not parent.children:
            return entity, []

        sibling_uris = [uri for uri in parent.children if uri != entity.uri]
        fetched = await asyncio.gather(
            *(self.get_entity_by_uri(uri) for uri in sibling_uris)
        )
        siblings = [child for child in fetched if child and child.code != entity.code]

        return entity, siblings

    async def get_code_chain(self, code: str) -> list[ICFEntity]:
        """
        Get the full hierarchy chain from root down to a specific code.

        Args:
            code: ICF code (e.g., "b2800")

        Returns:
            List of entities from root to the code, ordered root-first.
        """
        entity = await self.get_entity_by_code(code)
        if not entity:
            return []

        chain = [entity]
        current = entity
        max_depth = 10  # Safety limit to prevent infinite loops

        while current.parent and max_depth > 0:
            parent = await self.get_entity_by_uri(current.parent)
            if not parent:
                break
            chain.append(parent)
            current = parent
            max_depth -= 1

        chain.reverse()  # Root first
        return chain

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
