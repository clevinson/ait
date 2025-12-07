"""Client for NERC Vocabulary Server (NVS) - SKOS-based vocabularies."""

import httpx
from pydantic import BaseModel, Field


class Collection(BaseModel):
    """A SKOS collection from NVS."""

    uri: str
    identifier: str
    title: str
    description: str | None = None
    version: str | None = None
    modified: str | None = None


class Concept(BaseModel):
    """A SKOS concept from NVS."""

    uri: str
    pref_label: str = Field(alias="prefLabel")
    definition: str | None = None
    alt_labels: list[str] = Field(default_factory=list, alias="altLabels")
    broader: list[str] = Field(default_factory=list)
    narrower: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    deprecated: bool = False

    model_config = {"populate_by_name": True}


class NvsClient:
    """Client for NERC Vocabulary Server REST API."""

    BASE_URL = "https://vocab.nerc.ac.uk"

    def __init__(self, base_url: str | None = None):
        """Initialize the client.

        Args:
            base_url: Base URL of the NVS instance. Defaults to NERC's public server.
        """
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
        )

    async def list_collections(self) -> list[Collection]:
        """List all vocabulary collections."""
        response = await self._client.get(
            "/collection/",
            headers={"Accept": "application/ld+json"},
        )
        response.raise_for_status()
        data = response.json()

        collections = []
        members = data.get("member", [])
        for item in members:
            collections.append(
                Collection(
                    uri=item.get("@id", ""),
                    identifier=item.get("identifier", ""),
                    title=item.get("title", ""),
                    description=item.get("description"),
                    version=item.get("version"),
                    modified=item.get("modified"),
                )
            )
        return collections

    async def get_collection(self, identifier: str) -> Collection:
        """Get metadata for a specific collection.

        Args:
            identifier: Collection identifier (e.g., "P01", "L22").
        """
        response = await self._client.get(
            f"/collection/{identifier}/current/",
            headers={"Accept": "application/ld+json"},
        )
        response.raise_for_status()
        data = response.json()

        return Collection(
            uri=data.get("@id", ""),
            identifier=data.get("identifier", identifier),
            title=data.get("title", ""),
            description=data.get("description"),
            version=data.get("version"),
            modified=data.get("modified"),
        )

    async def get_concepts(self, collection: str) -> list[Concept]:
        """Get all concepts in a collection.

        Args:
            collection: Collection identifier.
        """
        response = await self._client.get(
            f"/collection/{collection}/current/",
            headers={"Accept": "application/ld+json"},
        )
        response.raise_for_status()
        data = response.json()

        concepts = []
        members = data.get("member", [])
        for item in members:
            concepts.append(self._parse_concept(item))
        return concepts

    async def get_concept(self, collection: str, concept_id: str) -> Concept:
        """Get a specific concept.

        Args:
            collection: Collection identifier.
            concept_id: Concept identifier within the collection.
        """
        response = await self._client.get(
            f"/collection/{collection}/current/{concept_id}/",
            headers={"Accept": "application/ld+json"},
        )
        response.raise_for_status()
        return self._parse_concept(response.json())

    async def search(self, query: str, collection: str | None = None) -> list[Concept]:
        """Search for concepts.

        Args:
            query: Search string.
            collection: Optional collection to search within.
        """
        params = {"searchstr": query}
        if collection:
            params["collection"] = collection

        response = await self._client.get(
            "/sparql/sparql",
            params={
                "query": self._search_sparql(query, collection),
                "output": "json",
            },
        )
        response.raise_for_status()
        data = response.json()

        concepts = []
        for binding in data.get("results", {}).get("bindings", []):
            concepts.append(
                Concept(
                    uri=binding.get("concept", {}).get("value", ""),
                    prefLabel=binding.get("prefLabel", {}).get("value", ""),
                    definition=binding.get("definition", {}).get("value"),
                )
            )
        return concepts

    def _search_sparql(self, query: str, collection: str | None = None) -> str:
        """Generate SPARQL query for search."""
        collection_filter = ""
        if collection:
            collection_filter = f"""
            ?concept skos:inScheme <{self.base_url}/collection/{collection}/current/> .
            """

        return f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?concept ?prefLabel ?definition
        WHERE {{
            ?concept a skos:Concept .
            ?concept skos:prefLabel ?prefLabel .
            OPTIONAL {{ ?concept skos:definition ?definition }}
            {collection_filter}
            FILTER(CONTAINS(LCASE(?prefLabel), LCASE("{query}")))
        }}
        LIMIT 100
        """

    def _parse_concept(self, data: dict) -> Concept:
        """Parse concept from JSON-LD."""
        alt_labels = data.get("altLabel", [])
        if isinstance(alt_labels, str):
            alt_labels = [alt_labels]

        broader = data.get("broader", [])
        if isinstance(broader, str):
            broader = [broader]
        elif isinstance(broader, list):
            broader = [b.get("@id", b) if isinstance(b, dict) else b for b in broader]

        narrower = data.get("narrower", [])
        if isinstance(narrower, str):
            narrower = [narrower]
        elif isinstance(narrower, list):
            narrower = [n.get("@id", n) if isinstance(n, dict) else n for n in narrower]

        related = data.get("related", [])
        if isinstance(related, str):
            related = [related]
        elif isinstance(related, list):
            related = [r.get("@id", r) if isinstance(r, dict) else r for r in related]

        return Concept(
            uri=data.get("@id", ""),
            prefLabel=data.get("prefLabel", ""),
            definition=data.get("definition"),
            altLabels=alt_labels,
            broader=broader,
            narrower=narrower,
            related=related,
            deprecated=data.get("deprecated", False),
        )

    async def download_collection(self, collection: str, format: str = "rdf") -> bytes:
        """Download a collection as RDF.

        Args:
            collection: Collection identifier.
            format: Format (rdf, ttl).

        Returns:
            Raw bytes of the vocabulary file.
        """
        accept = "application/rdf+xml" if format == "rdf" else "text/turtle"
        response = await self._client.get(
            f"/collection/{collection}/current/",
            headers={"Accept": accept},
        )
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "NvsClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
