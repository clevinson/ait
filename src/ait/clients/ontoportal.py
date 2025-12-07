"""Client for OntoPortal-style ontology repositories (BioPortal, AgroPortal, etc.)."""

from enum import StrEnum

import httpx
from pydantic import BaseModel, Field


class OntoPortalInstance(StrEnum):
    """Known OntoPortal instances."""

    BIOPORTAL = "https://data.bioontology.org"
    AGROPORTAL = "https://data.agroportal.lirmm.fr"
    ECOPORTAL = "https://data.ecoportal.lifewatch.eu"
    MATPORTAL = "https://data.matportal.org"
    SIFR = "https://data.bioportal.lirmm.fr"


class OntologyInfo(BaseModel):
    """Basic ontology metadata from OntoPortal."""

    acronym: str
    name: str
    ontology_type: str | None = Field(default=None, alias="ontologyType")
    description: str | None = None
    creation_date: str | None = Field(default=None, alias="creationDate")
    version: str | None = None

    model_config = {"populate_by_name": True}


class OntologyClass(BaseModel):
    """A class/term from an ontology."""

    id: str = Field(alias="@id")
    label: str | None = Field(default=None, alias="prefLabel")
    definition: list[str] | None = None
    synonyms: list[str] | None = Field(default=None, alias="synonym")
    parents: list[str] | None = Field(default=None, alias="subClassOf")
    obsolete: bool = False

    model_config = {"populate_by_name": True}


class SearchResult(BaseModel):
    """A search result from OntoPortal."""

    id: str = Field(alias="@id")
    label: str | None = Field(default=None, alias="prefLabel")
    definition: list[str] | None = None
    ontology: str | None = Field(default=None, alias="links")
    match_type: str | None = Field(default=None, alias="matchType")

    model_config = {"populate_by_name": True}


class OntoPortalClient:
    """Client for OntoPortal REST API."""

    def __init__(
        self,
        base_url: str | OntoPortalInstance = OntoPortalInstance.BIOPORTAL,
        api_key: str | None = None,
    ):
        """Initialize the client.

        Args:
            base_url: Base URL of the OntoPortal instance.
            api_key: API key for authentication (required for most operations).
        """
        self.base_url = str(base_url).rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers(),
            timeout=30.0,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"apikey token={self.api_key}"
        return headers

    async def list_ontologies(self) -> list[OntologyInfo]:
        """List all ontologies in the repository."""
        response = await self._client.get("/ontologies")
        response.raise_for_status()
        return [OntologyInfo.model_validate(item) for item in response.json()]

    async def get_ontology(self, acronym: str) -> OntologyInfo:
        """Get metadata for a specific ontology."""
        response = await self._client.get(f"/ontologies/{acronym}")
        response.raise_for_status()
        return OntologyInfo.model_validate(response.json())

    async def get_class(self, ontology: str, class_id: str) -> OntologyClass:
        """Get a specific class from an ontology.

        Args:
            ontology: Ontology acronym (e.g., "GO", "ENVO").
            class_id: Full class IRI (URL-encoded if needed).
        """
        encoded_id = httpx.URL(class_id).raw_path.decode() if "://" in class_id else class_id
        response = await self._client.get(
            f"/ontologies/{ontology}/classes/{encoded_id}",
            params={"display": "prefLabel,definition,synonym,subClassOf,obsolete"},
        )
        response.raise_for_status()
        return OntologyClass.model_validate(response.json())

    async def get_roots(self, ontology: str) -> list[OntologyClass]:
        """Get root classes of an ontology."""
        response = await self._client.get(f"/ontologies/{ontology}/classes/roots")
        response.raise_for_status()
        return [OntologyClass.model_validate(item) for item in response.json()]

    async def get_children(self, ontology: str, class_id: str) -> list[OntologyClass]:
        """Get child classes of a class."""
        encoded_id = httpx.URL(class_id).raw_path.decode() if "://" in class_id else class_id
        response = await self._client.get(f"/ontologies/{ontology}/classes/{encoded_id}/children")
        response.raise_for_status()
        return [OntologyClass.model_validate(item) for item in response.json()]

    async def search(
        self,
        query: str,
        ontologies: list[str] | None = None,
        exact_match: bool = False,
        include_obsolete: bool = False,
    ) -> list[SearchResult]:
        """Search for terms across ontologies.

        Args:
            query: Search string.
            ontologies: List of ontology acronyms to search (None = all).
            exact_match: Only return exact matches.
            include_obsolete: Include obsolete terms.
        """
        params: dict[str, str | bool] = {
            "q": query,
            "require_exact_match": exact_match,
            "include_obsolete": include_obsolete,
        }
        if ontologies:
            params["ontologies"] = ",".join(ontologies)

        response = await self._client.get("/search", params=params)
        response.raise_for_status()
        data = response.json()
        collection = data.get("collection", [])
        return [SearchResult.model_validate(item) for item in collection]

    async def download_ontology(self, acronym: str, format: str = "rdf") -> bytes:
        """Download an ontology file.

        Args:
            acronym: Ontology acronym.
            format: Download format (rdf, csv, etc.).

        Returns:
            Raw bytes of the ontology file.
        """
        response = await self._client.get(
            f"/ontologies/{acronym}/download",
            params={"download_format": format},
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "OntoPortalClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
