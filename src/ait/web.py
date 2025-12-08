"""FastAPI web server for ait - serves the SvelteKit frontend and API."""

import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mcp.server import Server as McpServer
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.responses import Response

from ait.clients.ontoportal import OntoPortalClient, OntoPortalInstance
from ait.store import RdfFormat, Store

# Meta graph for storing ait configuration (namespace preferences, etc.)
AIT_META_GRAPH = "urn:ait:meta"
AIT_NS = "urn:ait:ontology#"  # Namespace for ait predicates

# Well-known namespace prefixes (curated from prefix.cc and common ontologies)
WELL_KNOWN_PREFIXES: dict[str, str] = {
    # W3C standards
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
    "http://www.w3.org/2002/07/owl#": "owl",
    "http://www.w3.org/2001/XMLSchema#": "xsd",
    "http://www.w3.org/2004/02/skos/core#": "skos",
    "http://www.w3.org/ns/shacl#": "sh",
    "http://www.w3.org/ns/prov#": "prov",
    "http://www.w3.org/ns/dcat#": "dcat",
    "http://www.w3.org/ns/sosa/": "sosa",
    "http://www.w3.org/ns/ssn/": "ssn",
    "http://www.w3.org/ns/org#": "org",
    "http://www.w3.org/ns/adms#": "adms",
    # Dublin Core
    "http://purl.org/dc/terms/": "dct",
    "http://purl.org/dc/elements/1.1/": "dc",
    # Common ontologies
    "http://xmlns.com/foaf/0.1/": "foaf",
    "http://schema.org/": "schema",
    "https://schema.org/": "schema",
    "http://purl.org/vocab/vann/": "vann",
    "http://rdfs.org/ns/void#": "void",
    # Geospatial
    "http://www.opengis.net/ont/geosparql#": "geo",
    "http://www.w3.org/2003/01/geo/wgs84_pos#": "wgs84",
    # Science/units
    "http://qudt.org/schema/qudt/": "qudt",
    "http://qudt.org/vocab/unit/": "unit",
    "http://qudt.org/vocab/quantitykind/": "quantitykind",
    # Life sciences
    "http://purl.obolibrary.org/obo/": "obo",
    "http://purl.bioontology.org/ontology/": "bioportal",
    # ISO standards
    "http://def.isotc211.org/iso19156/2011/SamplingFeature#": "sf",
    "http://def.isotc211.org/iso19156/2011/Observation#": "om",
    "http://def.isotc211.org/iso19156/2011/GeneralFeatureInstance#": "gfi",
    "http://def.isotc211.org/iso19156/2011/SpatialSamplingFeature#": "ssf",
    # DBpedia
    "http://dbpedia.org/ontology/": "dbo",
    "http://dbpedia.org/property/": "dbp",
    "http://dbpedia.org/resource/": "dbr",
    # GLOSIS specific (common pattern)
    "http://w3id.org/glosis/model/": "glosis",
}


def _find_env_file() -> Path | None:
    """Find .env file by walking up from this file's location."""
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Walk up max 5 levels
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None


class Settings(BaseSettings):
    """Application settings loaded from environment/.env file."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bioportal_api_key: str = ""
    agroportal_api_key: str = ""
    ecoportal_api_key: str = ""
    matportal_api_key: str = ""

    def get_api_key(self, instance: OntoPortalInstance) -> str | None:
        """Get the API key for a given OntoPortal instance."""
        key_map = {
            OntoPortalInstance.BIOPORTAL: self.bioportal_api_key,
            OntoPortalInstance.AGROPORTAL: self.agroportal_api_key,
            OntoPortalInstance.ECOPORTAL: self.ecoportal_api_key,
            OntoPortalInstance.MATPORTAL: self.matportal_api_key,
            OntoPortalInstance.SIFR: self.bioportal_api_key,  # SIFR uses same as BioPortal
        }
        key = key_map.get(instance, "")
        return key if key else None


settings = Settings()

# ============================================================================
# MCP Server Setup
# ============================================================================

mcp_server = McpServer("ait")


@mcp_server.list_tools()
async def list_mcp_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="sparql_query",
            description="Execute a SPARQL query against the local RDF store containing cached ontologies",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SPARQL SELECT query",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_cached_ontologies",
            description="List all ontologies cached in the local store",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="describe_class",
            description="Get all triples about a specific class URI from the local store",
            inputSchema={
                "type": "object",
                "properties": {
                    "class_uri": {
                        "type": "string",
                        "description": "The full URI of the class to describe",
                    },
                    "ontology_uri": {
                        "type": "string",
                        "description": "Optional: limit to a specific ontology graph",
                    },
                },
                "required": ["class_uri"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle MCP tool calls."""
    store = get_store()

    match name:
        case "sparql_query":
            try:
                results = store.query(arguments["query"])
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(results[:100], indent=2),
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Query error: {e}")]

        case "list_cached_ontologies":
            graphs = list(store.graphs())
            # Get triple counts for each graph (skip internal meta graph)
            ontologies = []
            for graph_uri in graphs:
                if graph_uri == AIT_META_GRAPH:
                    continue
                count_query = f"SELECT (COUNT(*) as ?count) WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}"
                count_result = store.query(count_query)
                triple_count = int(count_result[0].get("count", 0)) if count_result else 0
                ontologies.append({"uri": graph_uri, "triple_count": triple_count})
            return [
                TextContent(
                    type="text",
                    text=json.dumps(ontologies, indent=2),
                )
            ]

        case "describe_class":
            class_uri = arguments["class_uri"]
            ontology_uri = arguments.get("ontology_uri")

            if ontology_uri:
                query = f"""
                SELECT ?predicate ?object WHERE {{
                    GRAPH <{ontology_uri}> {{
                        <{class_uri}> ?predicate ?object .
                    }}
                }}
                """
            else:
                query = f"""
                SELECT ?graph ?predicate ?object WHERE {{
                    GRAPH ?graph {{
                        <{class_uri}> ?predicate ?object .
                    }}
                }}
                """
            results = store.query(query)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(results[:50], indent=2),
                )
            ]

        case _:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ============================================================================
# MCP Streamable HTTP Routes
# ============================================================================

# Session manager handles all MCP session lifecycle
mcp_session_manager = StreamableHTTPSessionManager(
    app=mcp_server,
    stateless=True,  # Each request is independent - simpler for now
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize MCP session manager."""
    async with mcp_session_manager.run():
        yield


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="ait",
    description="Archive of Interconnected Terms",
    lifespan=lifespan
)


class EmptyResponse(Response):
    """Response that doesn't send anything - used when response already sent via ASGI."""

    async def __call__(self, scope, receive, send):
        # Do nothing - response was already sent by handle_request
        pass


@app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
async def mcp_endpoint(request: Request) -> Response:
    """Streamable HTTP endpoint for MCP client connections."""
    await mcp_session_manager.handle_request(
        request.scope, request.receive, request._send  # type: ignore
    )
    return EmptyResponse()


# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global store instance (configured at startup)
_store: Store | None = None
_data_dir: Path = Path.home() / ".ait"


def get_store() -> Store:
    """Get the store instance."""
    global _store
    if _store is None:
        store_path = _data_dir / "store"
        _store = Store(store_path)
    return _store


class OntologyInfo(BaseModel):
    """Information about a cached ontology."""

    uri: str
    label: str | None = None
    triple_count: int = 0


class GraphNode(BaseModel):
    """A node in the ontology graph."""

    id: str
    label: str
    type: str = "class"


class GraphEdge(BaseModel):
    """An edge in the ontology graph."""

    source: str
    target: str
    label: str


class GraphData(BaseModel):
    """Graph data for visualization."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]


class QueryRequest(BaseModel):
    """SPARQL query request."""

    sparql: str
    limit: int = 100


class QueryResponse(BaseModel):
    """SPARQL query response."""

    results: list[dict[str, Any]]
    count: int


class IngestRequest(BaseModel):
    """Request to ingest an ontology from a URL."""

    url: str
    api_key: str | None = None


class IngestResponse(BaseModel):
    """Response from ontology ingestion."""

    uri: str
    label: str
    triple_count: int


class EntityRef(BaseModel):
    """Reference to an entity with display info."""

    uri: str
    label: str
    prefix_iri: str | None = None


class EntityInfo(BaseModel):
    """Detailed information about an OWL entity."""

    uri: str
    label: str | None = None
    prefix_iri: str | None = None  # For display name computation
    comment: str | None = None
    entity_type: str  # Primary type: Class, ObjectProperty, DatatypeProperty, etc.
    all_types: list[EntityRef] = []  # All rdf:types
    is_defined_by: str | None = None
    superclasses: list[EntityRef] = []  # For breadcrumb
    subclasses: list[EntityRef] = []


class PropertyInfo(BaseModel):
    """Information about a property's domains and ranges."""

    uri: str
    label: str | None = None
    property_type: str  # ObjectProperty, DatatypeProperty, AnnotationProperty
    domains: list[dict[str, str]] = []  # Classes that have this property
    ranges: list[dict[str, str]] = []   # Classes/datatypes this property points to


class InheritedPropertyGroup(BaseModel):
    """Properties inherited from an ancestor class."""

    from_class: dict[str, str]  # {uri, label} of the ancestor class
    properties: list["PropertyInfo"] = []  # Properties inherited from this class


class ClassProperties(BaseModel):
    """Properties associated with a class."""

    domain_of: list[PropertyInfo] = []  # Properties where this class is the domain
    inherited: list[InheritedPropertyGroup] = []  # Properties inherited from superclasses
    range_of: list[PropertyInfo] = []   # Properties where this class is the range


class CodeListMember(BaseModel):
    """A member of a code list."""

    uri: str
    label: str
    notation: str | None = None  # skos:notation - the code value
    description: str | None = None


class CodeListInfo(BaseModel):
    """Information about a code list (enumeration)."""

    uri: str
    label: str | None = None
    pattern: str  # "skos_scheme", "owl_oneof", "owl_equivalent_oneof", "skos_collection"
    member_count: int = 0
    members: list[CodeListMember] = []


class HierarchyNode(BaseModel):
    """A node in the class hierarchy tree."""

    uri: str
    label: str
    prefix_iri: str | None = None  # prefixIRI for display name computation
    entity_type: str  # Class, ConceptScheme, Concept
    parent_uris: list[str] = []  # All direct superclasses (for multiple inheritance)
    is_external: bool = False  # True if class is from an external vocabulary
    is_deprecated: bool = False  # True if owl:deprecated true


class NamespaceInfo(BaseModel):
    """Information about a namespace in an ontology."""

    namespace: str
    prefix: str | None = None  # Short prefix like "foaf", "skos", etc.
    class_count: int
    selected: bool = False  # Whether user has selected this as internal


class OntologyConfig(BaseModel):
    """User configuration for an ontology."""

    ontology_uri: str
    selected_namespaces: list[str] = []  # Namespaces user wants to show
    display_name_mode: str = "label"  # "label" or "identifier"
    show_deprecated: bool = False  # Whether to show owl:deprecated entities


# Map web portal URLs to data API URLs
ONTOPORTAL_URL_PATTERNS = [
    # bioportal.bioontology.org/ontologies/ACRONYM -> data.bioontology.org
    (r"https?://bioportal\.bioontology\.org/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.BIOPORTAL),
    (r"https?://data\.bioontology\.org/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.BIOPORTAL),
    # agroportal
    (r"https?://agroportal\.lirmm\.fr/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.AGROPORTAL),
    (r"https?://data\.agroportal\.lirmm\.fr/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.AGROPORTAL),
    # ecoportal
    (r"https?://ecoportal\.lifewatch\.eu/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.ECOPORTAL),
    (r"https?://data\.ecoportal\.lifewatch\.eu/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.ECOPORTAL),
    # matportal
    (r"https?://matportal\.org/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.MATPORTAL),
    (r"https?://data\.matportal\.org/ontologies/([A-Za-z0-9_-]+)", OntoPortalInstance.MATPORTAL),
]


def parse_ontoportal_url(url: str) -> tuple[OntoPortalInstance, str] | None:
    """Parse an OntoPortal URL and return (instance, acronym) or None."""
    for pattern, instance in ONTOPORTAL_URL_PATTERNS:
        match = re.match(pattern, url.strip())
        if match:
            return instance, match.group(1)
    return None


@app.get("/api/ontologies", response_model=list[OntologyInfo])
async def list_ontologies() -> list[OntologyInfo]:
    """List all cached ontologies (named graphs)."""
    store = get_store()
    ontologies = []

    for graph_uri in store.graphs():
        # Skip internal meta graph
        if graph_uri == AIT_META_GRAPH:
            continue
        # Get triple count for this graph
        count_query = f"SELECT (COUNT(*) as ?count) WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}"
        count_result = store.query(count_query)
        triple_count = int(count_result[0].get("count", 0)) if count_result else 0

        # Try to get a label
        label_query = f"""
        SELECT ?label WHERE {{
            GRAPH <{graph_uri}> {{
                <{graph_uri}> <http://www.w3.org/2000/01/rdf-schema#label> ?label .
            }}
        }} LIMIT 1
        """
        label_result = store.query(label_query)
        label = label_result[0].get("label") if label_result else None

        # Fallback: extract name from URI
        if not label:
            label = graph_uri.split("/")[-1].split("#")[-1]

        ontologies.append(
            OntologyInfo(uri=graph_uri, label=label, triple_count=triple_count)
        )

    return ontologies


@app.get("/api/ontologies/{ontology_uri:path}/graph", response_model=GraphData)
async def get_ontology_graph(ontology_uri: str, limit: int = 200) -> GraphData:
    """Get graph visualization data for an ontology."""
    store = get_store()

    # Check if ontology exists
    graphs = list(store.graphs())
    if ontology_uri not in graphs:
        raise HTTPException(status_code=404, detail="Ontology not found")

    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    # Get classes and their relationships
    class_query = f"""
    SELECT DISTINCT ?class ?label ?parent WHERE {{
        GRAPH <{ontology_uri}> {{
            ?class a <http://www.w3.org/2002/07/owl#Class> .
            OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
            OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent }}
        }}
    }} LIMIT {limit}
    """

    results = store.query(class_query)

    for row in results:
        class_uri = row.get("class", "")
        if class_uri and not class_uri.startswith("_:"):
            label = row.get("label") or class_uri.split("/")[-1].split("#")[-1]
            if class_uri not in nodes:
                nodes[class_uri] = GraphNode(id=class_uri, label=label, type="class")

            parent = row.get("parent")
            if parent and not parent.startswith("_:") and parent != class_uri:
                parent_label = parent.split("/")[-1].split("#")[-1]
                if parent not in nodes:
                    nodes[parent] = GraphNode(id=parent, label=parent_label, type="class")
                edges.append(GraphEdge(source=class_uri, target=parent, label="subClassOf"))

    return GraphData(nodes=list(nodes.values()), edges=edges)


@app.post("/api/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest) -> QueryResponse:
    """Execute a SPARQL query against the store."""
    store = get_store()

    try:
        results = store.query(request.sparql)
        limited = results[: request.limit]
        return QueryResponse(results=limited, count=len(results))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ontologies/{ontology_uri:path}/classes")
async def list_classes(ontology_uri: str, limit: int = 100) -> list[dict[str, str | None]]:
    """List classes in an ontology."""
    store = get_store()

    query = f"""
    SELECT DISTINCT ?class ?label ?comment WHERE {{
        GRAPH <{ontology_uri}> {{
            ?class a <http://www.w3.org/2002/07/owl#Class> .
            OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
            OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#comment> ?comment }}
        }}
    }} LIMIT {limit}
    """

    results = store.query(query)
    classes = []
    for row in results:
        class_uri = row.get("class", "")
        if class_uri and not class_uri.startswith("_:"):
            classes.append({
                "uri": class_uri,
                "label": row.get("label") or class_uri.split("/")[-1].split("#")[-1],
                "comment": row.get("comment"),
            })

    return classes


@app.post("/api/ontologies/ingest", response_model=IngestResponse)
async def ingest_ontology(request: IngestRequest) -> IngestResponse:
    """Ingest an ontology from an OntoPortal URL."""
    parsed = parse_ontoportal_url(request.url)
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail="URL not recognized. Supported: BioPortal, AgroPortal, EcoPortal, MatPortal URLs",
        )

    instance, acronym = parsed
    store = get_store()

    # Use provided API key, or fall back to env config
    api_key = request.api_key or settings.get_api_key(instance)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"No API key configured for {instance.name}. Set {instance.name}_API_KEY in .env or provide one in the request.",
        )

    async with OntoPortalClient(instance, api_key=api_key) as client:
        # Get ontology metadata
        try:
            info = await client.get_ontology(acronym)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Ontology not found: {e}")

        # Download the ontology
        try:
            rdf_data = await client.download_ontology(acronym)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download: {e}")

    # Determine graph URI (use ontology IRI or construct from portal)
    graph_uri = f"{instance}/ontologies/{acronym}"

    # Try to load as RDF/XML first (most common), fallback to Turtle
    triple_count = 0
    for fmt in [RdfFormat.XML, RdfFormat.TURTLE, RdfFormat.NTRIPLES]:
        try:
            triple_count = store.load_rdf(rdf_data, format=fmt, graph_name=graph_uri)
            break
        except Exception:
            continue
    else:
        raise HTTPException(status_code=500, detail="Failed to parse ontology RDF")

    # Extract prefixes from the downloaded RDF data
    prefixes = _extract_prefixes_from_rdf(rdf_data)

    # Store extracted prefixes in meta graph
    if prefixes:
        _store_ontology_prefixes(store, graph_uri, prefixes)

    return IngestResponse(
        uri=graph_uri,
        label=info.name or acronym,
        triple_count=triple_count,
    )


@app.post("/api/ontologies/{ontology_uri:path}/refresh", response_model=IngestResponse)
async def refresh_ontology(ontology_uri: str) -> IngestResponse:
    """Clear and re-import an ontology from its original source.

    This will:
    1. Clear the ontology graph
    2. Clear all metadata for this ontology (config, prefixes)
    3. Re-download and re-import from the original source
    """
    # Parse the ontology URI to determine the source
    parsed = parse_ontoportal_url(ontology_uri)
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail="Cannot refresh: ontology URI not recognized as OntoPortal URL",
        )

    instance, acronym = parsed
    store = get_store()

    # Clear the ontology graph
    store.clear(graph_name=ontology_uri)

    # Clear all metadata for this ontology in meta graph
    clear_meta_query = f"""
    DELETE WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> ?p ?o .
        }}
    }}
    """
    try:
        store.update(clear_meta_query)
    except Exception:
        pass  # Meta graph might not exist

    # Get API key
    api_key = settings.get_api_key(instance)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"No API key configured for {instance.name}",
        )

    # Re-download and import
    async with OntoPortalClient(instance, api_key=api_key) as client:
        try:
            info = await client.get_ontology(acronym)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Ontology not found: {e}")

        try:
            rdf_data = await client.download_ontology(acronym)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download: {e}")

    # Load the ontology
    triple_count = 0
    for fmt in [RdfFormat.XML, RdfFormat.TURTLE, RdfFormat.NTRIPLES]:
        try:
            triple_count = store.load_rdf(rdf_data, format=fmt, graph_name=ontology_uri)
            break
        except Exception:
            continue
    else:
        raise HTTPException(status_code=500, detail="Failed to parse ontology RDF")

    # Extract and store prefixes from the downloaded RDF data
    prefixes = _extract_prefixes_from_rdf(rdf_data)
    if prefixes:
        _store_ontology_prefixes(store, ontology_uri, prefixes)

    return IngestResponse(
        uri=ontology_uri,
        label=info.name or acronym,
        triple_count=triple_count,
    )


# ============================================================================
# Namespace Configuration API
# ============================================================================

@app.get("/api/ontologies/{ontology_uri:path}/namespaces", response_model=list[NamespaceInfo])
async def list_namespaces(ontology_uri: str) -> list[NamespaceInfo]:
    """List all namespaces in an ontology with class counts.

    Also indicates which namespaces are currently selected (from stored config).
    Uses prefixes from the original RDF file if available, otherwise falls back
    to well-known prefixes.
    """
    store = get_store()

    # Query for all class namespaces with counts
    query = f"""
    SELECT ?ns (COUNT(?class) as ?count) WHERE {{
        GRAPH <{ontology_uri}> {{
            ?class a <http://www.w3.org/2002/07/owl#Class> .
            FILTER(isIRI(?class))
            BIND(REPLACE(STR(?class), "(.*[#/])[^#/]*$", "$1") AS ?ns)
        }}
    }} GROUP BY ?ns ORDER BY DESC(?count)
    """
    results = store.query(query)

    # Get current config
    config = _get_ontology_config(store, ontology_uri)
    selected_set = set(config.selected_namespaces)

    # Get stored prefixes from the original RDF file
    stored_prefixes = _get_ontology_prefixes(store, ontology_uri)

    def get_prefix(ns: str) -> str | None:
        """Get prefix for namespace - stored first, then well-known fallback."""
        if ns in stored_prefixes:
            return stored_prefixes[ns]
        return _get_prefix_for_namespace(ns)

    namespaces = []
    for row in results:
        ns = row.get("ns")
        count = int(row.get("count", 0))
        if ns and count > 0:
            namespaces.append(NamespaceInfo(
                namespace=ns,
                prefix=get_prefix(ns),
                class_count=count,
                selected=ns in selected_set
            ))

    return namespaces


@app.get("/api/ontologies/{ontology_uri:path}/config", response_model=OntologyConfig)
async def get_ontology_config_endpoint(ontology_uri: str) -> OntologyConfig:
    """Get the stored configuration for an ontology."""
    store = get_store()
    return _get_ontology_config(store, ontology_uri)


@app.put("/api/ontologies/{ontology_uri:path}/config", response_model=OntologyConfig)
async def save_ontology_config(ontology_uri: str, config: OntologyConfig) -> OntologyConfig:
    """Save configuration for an ontology (selected namespaces, display mode, show deprecated)."""
    store = get_store()
    _save_ontology_config(store, ontology_uri, config.selected_namespaces, config.display_name_mode, config.show_deprecated)
    return OntologyConfig(
        ontology_uri=ontology_uri,
        selected_namespaces=config.selected_namespaces,
        display_name_mode=config.display_name_mode,
        show_deprecated=config.show_deprecated
    )


@app.get("/api/ontologies/{ontology_uri:path}/prefixes")
async def get_ontology_prefixes_endpoint(ontology_uri: str) -> dict[str, str]:
    """Get all stored namespace prefixes for an ontology.

    Returns a dict mapping namespace URI to prefix string.
    """
    store = get_store()
    return _get_ontology_prefixes(store, ontology_uri)


def _extract_prefixes_from_rdf(data: bytes) -> dict[str, str]:
    """Extract namespace prefix bindings from RDF data.

    Tries multiple formats (RDF/XML, Turtle, N-Triples) and returns
    a dict mapping namespace URIs to their prefixes.
    """
    from rdflib import Graph as RdfLibGraph

    g = RdfLibGraph()

    # Try parsing in different formats
    for fmt in ["xml", "turtle", "nt"]:
        try:
            g.parse(data=data, format=fmt)
            break
        except Exception:
            continue
    else:
        return {}

    # Extract namespace bindings
    prefixes: dict[str, str] = {}
    for prefix, namespace in g.namespaces():
        if prefix:  # Skip empty prefix
            ns_str = str(namespace)
            prefixes[ns_str] = prefix

    return prefixes


def _store_ontology_prefixes(store: Store, ontology_uri: str, prefixes: dict[str, str]) -> None:
    """Store namespace prefixes for an ontology in the meta graph.

    Args:
        store: The RDF store
        ontology_uri: The ontology graph URI
        prefixes: Dict mapping namespace URI to prefix string
    """
    if not prefixes:
        return

    # First delete any existing prefixes for this ontology
    # Delete old-style (hasPrefix with nodes) and new-style (prefix/X predicates)
    delete_old = f"""
    DELETE WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}hasPrefix> ?bnode .
            ?bnode ?p ?o .
        }}
    }}
    """
    delete_new = f"""
    DELETE WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> ?pred ?ns .
            FILTER(STRSTARTS(STR(?pred), "{AIT_NS}prefix/"))
        }}
    }}
    """
    try:
        store.update(delete_old)
        store.update(delete_new)
    except Exception:
        pass  # Graph might not exist yet

    # Insert prefixes: <ontology> ait:prefix_<PREFIX> "namespace_uri"
    # This encodes the prefix in the predicate and namespace as the literal value
    stored_count = 0
    failed_count = 0
    for namespace, prefix in prefixes.items():
        # URL-encode the prefix for use in predicate IRI
        import urllib.parse
        safe_prefix = urllib.parse.quote(prefix, safe='')
        # Escape namespace for literal
        escaped_ns = namespace.replace("\\", "\\\\").replace('"', '\\"')

        insert_query = f"""
        INSERT DATA {{
            GRAPH <{AIT_META_GRAPH}> {{
                <{ontology_uri}> <{AIT_NS}prefix/{safe_prefix}> "{escaped_ns}" .
            }}
        }}
        """
        try:
            store.update(insert_query)
            stored_count += 1
        except Exception as e:
            failed_count += 1
            print(f"FAILED to store prefix {prefix}: {namespace} - {e}")

    print(f"Stored {stored_count} prefixes, {failed_count} failed")


def _get_ontology_prefixes(store: Store, ontology_uri: str) -> dict[str, str]:
    """Get namespace prefixes for an ontology.

    Combines prefixes from:
    1. Stored prefixes in the meta graph (from RDF source)
    2. Derived from metadata:prefixIRI annotations in the ontology

    Returns dict mapping namespace URI to prefix string.
    """
    import urllib.parse

    prefixes: dict[str, str] = {}

    # 1. Query for stored prefixes in meta graph
    stored_query = f"""
    SELECT ?pred ?namespace WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> ?pred ?namespace .
            FILTER(STRSTARTS(STR(?pred), "{AIT_NS}prefix/"))
        }}
    }}
    """
    stored_results = store.query(stored_query)

    prefix_base = f"{AIT_NS}prefix/"
    for r in stored_results:
        pred = r.get("pred", "")
        namespace = r.get("namespace", "")
        if pred and namespace and pred.startswith(prefix_base):
            encoded_prefix = pred[len(prefix_base):]
            prefix = urllib.parse.unquote(encoded_prefix)
            prefixes[namespace] = prefix

    # 2. Derive prefixes from metadata:prefixIRI annotations
    # These contain values like "glosis_lh:Clay" which we can parse
    prefix_iri_query = f"""
    SELECT DISTINCT ?class ?prefixIRI WHERE {{
        GRAPH <{ontology_uri}> {{
            ?class <http://data.bioontology.org/metadata/prefixIRI> ?prefixIRI .
        }}
    }}
    """
    prefix_iri_results = store.query(prefix_iri_query)

    for r in prefix_iri_results:
        class_uri = r.get("class", "")
        prefix_iri = r.get("prefixIRI", "")
        if class_uri and prefix_iri and ":" in prefix_iri:
            # Parse "prefix:localName" format
            prefix, local_name = prefix_iri.split(":", 1)
            if prefix and local_name:
                # Derive namespace from class URI by removing local name
                # e.g., "http://w3id.org/glosis/model/layerhorizon/Clay" -> "http://w3id.org/glosis/model/layerhorizon/"
                if class_uri.endswith(local_name):
                    namespace = class_uri[:-len(local_name)]
                    # Only add if we don't already have this namespace
                    if namespace and namespace not in prefixes:
                        prefixes[namespace] = prefix

    return prefixes


def _get_ontology_config(store: Store, ontology_uri: str) -> OntologyConfig:
    """Read ontology config from the meta graph."""
    # Get selected namespaces
    ns_query = f"""
    SELECT ?namespace WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}selectedNamespace> ?namespace .
        }}
    }}
    """
    ns_results = store.query(ns_query)
    namespaces = [r.get("namespace") for r in ns_results if r.get("namespace")]

    # Get display name mode
    mode_query = f"""
    SELECT ?mode WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}displayNameMode> ?mode .
        }}
    }}
    """
    mode_results = store.query(mode_query)
    display_mode = mode_results[0].get("mode", "label") if mode_results else "label"

    # Get show_deprecated setting
    deprecated_query = f"""
    SELECT ?show WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}showDeprecated> ?show .
        }}
    }}
    """
    deprecated_results = store.query(deprecated_query)
    show_deprecated = False
    if deprecated_results:
        val = deprecated_results[0].get("show", "false")
        show_deprecated = str(val).lower() == "true"

    return OntologyConfig(
        ontology_uri=ontology_uri,
        selected_namespaces=namespaces,
        display_name_mode=display_mode,
        show_deprecated=show_deprecated
    )


def _save_ontology_config(store: Store, ontology_uri: str, namespaces: list[str], display_name_mode: str = "label", show_deprecated: bool = False) -> None:
    """Save ontology config to the meta graph."""
    # First, delete existing config for this ontology
    delete_ns_query = f"""
    DELETE WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}selectedNamespace> ?ns .
        }}
    }}
    """
    delete_mode_query = f"""
    DELETE WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}displayNameMode> ?mode .
        }}
    }}
    """
    delete_deprecated_query = f"""
    DELETE WHERE {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}showDeprecated> ?show .
        }}
    }}
    """
    try:
        store.update(delete_ns_query)
        store.update(delete_mode_query)
        store.update(delete_deprecated_query)
    except Exception:
        pass  # Graph might not exist yet

    # Insert namespace config
    if namespaces:
        insert_ns_query = f"""
        INSERT DATA {{
            GRAPH <{AIT_META_GRAPH}> {{
                {" ".join(f'<{ontology_uri}> <{AIT_NS}selectedNamespace> <{ns}> .' for ns in namespaces)}
            }}
        }}
        """
        store.update(insert_ns_query)

    # Insert display name mode
    insert_mode_query = f"""
    INSERT DATA {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}displayNameMode> "{display_name_mode}" .
        }}
    }}
    """
    store.update(insert_mode_query)

    # Insert show_deprecated setting
    insert_deprecated_query = f"""
    INSERT DATA {{
        GRAPH <{AIT_META_GRAPH}> {{
            <{ontology_uri}> <{AIT_NS}showDeprecated> "{str(show_deprecated).lower()}" .
        }}
    }}
    """
    store.update(insert_deprecated_query)


# OWL namespace URIs
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty"
OWL_DATATYPE_PROPERTY = "http://www.w3.org/2002/07/owl#DatatypeProperty"
OWL_ANNOTATION_PROPERTY = "http://www.w3.org/2002/07/owl#AnnotationProperty"
OWL_NAMED_INDIVIDUAL = "http://www.w3.org/2002/07/owl#NamedIndividual"
OWL_ONE_OF = "http://www.w3.org/2002/07/owl#oneOf"
OWL_EQUIVALENT_CLASS = "http://www.w3.org/2002/07/owl#equivalentClass"
RDFS_CLASS = "http://www.w3.org/2000/01/rdf-schema#Class"
SKOS_CONCEPT_SCHEME = "http://www.w3.org/2004/02/skos/core#ConceptScheme"
SKOS_CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
SKOS_IN_SCHEME = "http://www.w3.org/2004/02/skos/core#inScheme"
SKOS_MEMBER = "http://www.w3.org/2004/02/skos/core#member"
SKOS_PREF_LABEL = "http://www.w3.org/2004/02/skos/core#prefLabel"
RDF_FIRST = "http://www.w3.org/1999/02/22-rdf-syntax-ns#first"
RDF_REST = "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest"


def _extract_local_name(uri: str) -> str:
    """Extract local name from URI."""
    hash_idx = uri.rfind("#")
    slash_idx = uri.rfind("/")
    idx = max(hash_idx, slash_idx)
    return uri[idx + 1:] if idx >= 0 else uri


def _resolve_blank_node_range(store: Store, graph_uri: str, property_uri: str) -> list[dict[str, str]]:
    """Resolve blank node ranges that contain owl:oneOf restrictions.

    Returns a list of {uri, label} dicts for the actual values in the oneOf list.
    """
    # Query for owl:oneOf first element (most restrictions have a single value)
    query = f"""
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?member ?memberLabel WHERE {{
        GRAPH <{graph_uri}> {{
            <{property_uri}> rdfs:range ?range .
            ?range owl:oneOf ?list .
            ?list rdf:first ?member .
            FILTER(!isBlank(?member))
            OPTIONAL {{ ?member rdfs:label ?memberLabel }}
        }}
    }}
    """
    results = store.query(query)

    resolved = []
    for r in results:
        member_uri = r.get("member")
        if member_uri:
            resolved.append({
                "uri": member_uri,
                "label": r.get("memberLabel") or _extract_local_name(member_uri)
            })
    return resolved


def _detect_entity_type(store: Store, graph_uri: str, entity_uri: str) -> str:
    """Detect the OWL/SKOS type of an entity."""
    type_query = f"""
    SELECT ?type WHERE {{
        GRAPH <{graph_uri}> {{
            <{entity_uri}> a ?type .
        }}
    }}
    """
    results = store.query(type_query)
    types = {r.get("type") for r in results if r.get("type")}

    # Check in order of specificity
    # SKOS types (check first as something can be both Class and ConceptScheme)
    if SKOS_CONCEPT_SCHEME in types:
        return "ConceptScheme"
    if SKOS_CONCEPT in types:
        return "Concept"
    # OWL types
    if OWL_CLASS in types or RDFS_CLASS in types:
        return "Class"
    if OWL_OBJECT_PROPERTY in types:
        return "ObjectProperty"
    if OWL_DATATYPE_PROPERTY in types:
        return "DatatypeProperty"
    if OWL_ANNOTATION_PROPERTY in types:
        return "AnnotationProperty"
    if OWL_NAMED_INDIVIDUAL in types:
        return "NamedIndividual"
    return "Unknown"


def _detect_codelist_pattern(store: Store, graph_uri: str, entity_uri: str) -> str | None:
    """Detect if an entity is a code list and which pattern it uses."""
    # Check for SKOS ConceptScheme
    skos_check = f"""
    ASK {{
        GRAPH <{graph_uri}> {{
            {{ <{entity_uri}> a <{SKOS_CONCEPT_SCHEME}> }}
            UNION
            {{ <{entity_uri}> a ?subtype . ?subtype <http://www.w3.org/2000/01/rdf-schema#subClassOf>+ <{SKOS_CONCEPT_SCHEME}> }}
        }}
    }}
    """
    # We can't do ASK easily, so check for members instead
    skos_members = f"""
    SELECT (COUNT(?member) as ?count) WHERE {{
        GRAPH <{graph_uri}> {{
            ?member <{SKOS_IN_SCHEME}> <{entity_uri}> .
        }}
    }}
    """
    skos_result = store.query(skos_members)
    if skos_result and int(skos_result[0].get("count", 0)) > 0:
        return "skos_scheme"

    # Check for owl:oneOf directly on class
    oneof_check = f"""
    SELECT (COUNT(?member) as ?count) WHERE {{
        GRAPH <{graph_uri}> {{
            <{entity_uri}> <{OWL_ONE_OF}>/<{RDF_REST}>*/<{RDF_FIRST}> ?member .
        }}
    }}
    """
    oneof_result = store.query(oneof_check)
    if oneof_result and int(oneof_result[0].get("count", 0)) > 0:
        return "owl_oneof"

    # Check for owl:equivalentClass with owl:oneOf
    equiv_oneof_check = f"""
    SELECT (COUNT(?member) as ?count) WHERE {{
        GRAPH <{graph_uri}> {{
            <{entity_uri}> <{OWL_EQUIVALENT_CLASS}>/<{OWL_ONE_OF}>/<{RDF_REST}>*/<{RDF_FIRST}> ?member .
        }}
    }}
    """
    equiv_result = store.query(equiv_oneof_check)
    if equiv_result and int(equiv_result[0].get("count", 0)) > 0:
        return "owl_equivalent_oneof"

    # Check for skos:member (for skos:Collection)
    collection_check = f"""
    SELECT (COUNT(?member) as ?count) WHERE {{
        GRAPH <{graph_uri}> {{
            <{entity_uri}> <{SKOS_MEMBER}> ?member .
        }}
    }}
    """
    collection_result = store.query(collection_check)
    if collection_result and int(collection_result[0].get("count", 0)) > 0:
        return "skos_collection"

    return None


@app.get("/api/entity", response_model=EntityInfo)
async def get_entity_info(ontology: str, entity: str) -> EntityInfo:
    """Get detailed information about an OWL entity."""
    store = get_store()

    # Detect entity type
    entity_type = _detect_entity_type(store, ontology, entity)

    # Get basic info
    info_query = f"""
    SELECT ?label ?comment ?isDefinedBy ?prefixIRI WHERE {{
        GRAPH <{ontology}> {{
            OPTIONAL {{ <{entity}> <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
            OPTIONAL {{ <{entity}> <http://www.w3.org/2000/01/rdf-schema#comment> ?comment }}
            OPTIONAL {{ <{entity}> <http://www.w3.org/2000/01/rdf-schema#isDefinedBy> ?isDefinedBy }}
            OPTIONAL {{ <{entity}> <http://data.bioontology.org/metadata/prefixIRI> ?prefixIRI }}
        }}
    }} LIMIT 1
    """
    info_results = store.query(info_query)
    info = info_results[0] if info_results else {}

    # Get superclass chain for breadcrumb (for Classes)
    superclasses: list[EntityRef] = []
    if entity_type == "Class":
        # Walk up the superclass chain
        visited = {entity}
        current = entity
        for _ in range(20):  # Max depth to prevent infinite loops
            parent_query = f"""
            SELECT ?parent ?parentLabel ?parentPrefixIRI WHERE {{
                GRAPH <{ontology}> {{
                    <{current}> <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent .
                    FILTER(isIRI(?parent))
                    OPTIONAL {{ ?parent <http://www.w3.org/2000/01/rdf-schema#label> ?parentLabel }}
                    OPTIONAL {{ ?parent <http://data.bioontology.org/metadata/prefixIRI> ?parentPrefixIRI }}
                }}
            }} LIMIT 1
            """
            parent_results = store.query(parent_query)
            if not parent_results:
                break
            parent_uri = parent_results[0].get("parent")
            if not parent_uri or parent_uri in visited:
                break
            visited.add(parent_uri)
            superclasses.append(EntityRef(
                uri=parent_uri,
                label=parent_results[0].get("parentLabel") or _extract_local_name(parent_uri),
                prefix_iri=parent_results[0].get("parentPrefixIRI")
            ))
            current = parent_uri

    # Get direct subclasses
    subclasses: list[EntityRef] = []
    if entity_type == "Class":
        subclass_query = f"""
        SELECT DISTINCT ?sub ?subLabel ?subPrefixIRI WHERE {{
            GRAPH <{ontology}> {{
                ?sub <http://www.w3.org/2000/01/rdf-schema#subClassOf> <{entity}> .
                FILTER(isIRI(?sub))
                OPTIONAL {{ ?sub <http://www.w3.org/2000/01/rdf-schema#label> ?subLabel }}
                OPTIONAL {{ ?sub <http://data.bioontology.org/metadata/prefixIRI> ?subPrefixIRI }}
            }}
        }} LIMIT 50
        """
        sub_results = store.query(subclass_query)
        for r in sub_results:
            sub_uri = r.get("sub")
            if sub_uri:
                subclasses.append(EntityRef(
                    uri=sub_uri,
                    label=r.get("subLabel") or _extract_local_name(sub_uri),
                    prefix_iri=r.get("subPrefixIRI")
                ))

    # Get all rdf:types for this entity
    all_types: list[EntityRef] = []
    types_query = f"""
    SELECT DISTINCT ?type ?typeLabel ?typePrefixIRI WHERE {{
        GRAPH <{ontology}> {{
            <{entity}> a ?type .
            FILTER(isIRI(?type))
            OPTIONAL {{ ?type <http://www.w3.org/2000/01/rdf-schema#label> ?typeLabel }}
            OPTIONAL {{ ?type <http://data.bioontology.org/metadata/prefixIRI> ?typePrefixIRI }}
        }}
    }}
    """
    types_results = store.query(types_query)
    for r in types_results:
        type_uri = r.get("type")
        if type_uri:
            all_types.append(EntityRef(
                uri=type_uri,
                label=r.get("typeLabel") or _extract_local_name(type_uri),
                prefix_iri=r.get("typePrefixIRI")
            ))
    # Sort by label
    all_types = sorted(all_types, key=lambda x: x.label)

    return EntityInfo(
        uri=entity,
        label=info.get("label") or _extract_local_name(entity),
        prefix_iri=info.get("prefixIRI"),
        comment=info.get("comment"),
        entity_type=entity_type,
        all_types=all_types,
        is_defined_by=info.get("isDefinedBy"),
        superclasses=superclasses,
        subclasses=sorted(subclasses, key=lambda x: x.label)
    )


def _get_properties_for_class(store: Store, ontology: str, class_uri: str) -> dict[str, PropertyInfo]:
    """Get properties where the given class is the domain."""
    domain_query = f"""
    SELECT DISTINCT ?prop ?propLabel ?propType ?range ?rangeLabel WHERE {{
        GRAPH <{ontology}> {{
            ?prop <http://www.w3.org/2000/01/rdf-schema#domain> <{class_uri}> .
            OPTIONAL {{ ?prop <http://www.w3.org/2000/01/rdf-schema#label> ?propLabel }}
            OPTIONAL {{ ?prop a ?propType . FILTER(?propType IN (<{OWL_OBJECT_PROPERTY}>, <{OWL_DATATYPE_PROPERTY}>, <{OWL_ANNOTATION_PROPERTY}>)) }}
            OPTIONAL {{
                ?prop <http://www.w3.org/2000/01/rdf-schema#range> ?range .
                OPTIONAL {{ ?range <http://www.w3.org/2000/01/rdf-schema#label> ?rangeLabel }}
            }}
        }}
    }}
    """
    domain_results = store.query(domain_query)

    props: dict[str, PropertyInfo] = {}
    for r in domain_results:
        prop_uri = r.get("prop")
        if not prop_uri:
            continue
        if prop_uri not in props:
            prop_type_uri = r.get("propType", "")
            prop_type = "ObjectProperty"
            if OWL_DATATYPE_PROPERTY in prop_type_uri:
                prop_type = "DatatypeProperty"
            elif OWL_ANNOTATION_PROPERTY in prop_type_uri:
                prop_type = "AnnotationProperty"

            props[prop_uri] = PropertyInfo(
                uri=prop_uri,
                label=r.get("propLabel") or _extract_local_name(prop_uri),
                property_type=prop_type,
                domains=[{"uri": class_uri, "label": _extract_local_name(class_uri)}],
                ranges=[]
            )
        range_uri = r.get("range")
        if range_uri and not range_uri.startswith("_:"):
            existing_ranges = [rg["uri"] for rg in props[prop_uri].ranges]
            if range_uri not in existing_ranges:
                props[prop_uri].ranges.append({
                    "uri": range_uri,
                    "label": r.get("rangeLabel") or _extract_local_name(range_uri)
                })

    # Resolve blank node ranges (e.g., owl:oneOf restrictions)
    for prop_uri, prop_info in props.items():
        if not prop_info.ranges:
            resolved = _resolve_blank_node_range(store, ontology, prop_uri)
            if resolved:
                prop_info.ranges.extend(resolved)

    return props


def _get_superclass_chain(store: Store, ontology: str, class_uri: str) -> list[dict[str, str]]:
    """Get all superclasses in order from immediate parent to root."""
    superclasses: list[dict[str, str]] = []
    visited = {class_uri}
    current = class_uri

    for _ in range(50):  # Max depth to prevent infinite loops
        parent_query = f"""
        SELECT ?parent ?parentLabel WHERE {{
            GRAPH <{ontology}> {{
                <{current}> <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent .
                FILTER(isIRI(?parent))
                OPTIONAL {{ ?parent <http://www.w3.org/2000/01/rdf-schema#label> ?parentLabel }}
            }}
        }} LIMIT 1
        """
        parent_results = store.query(parent_query)
        if not parent_results:
            break
        parent_uri = parent_results[0].get("parent")
        if not parent_uri or parent_uri in visited:
            break
        if parent_uri in EXCLUDED_CLASSES:
            break
        visited.add(parent_uri)
        superclasses.append({
            "uri": parent_uri,
            "label": parent_results[0].get("parentLabel") or _extract_local_name(parent_uri)
        })
        current = parent_uri

    return superclasses


@app.get("/api/class-properties", response_model=ClassProperties)
async def get_class_properties(ontology: str, class_uri: str) -> ClassProperties:
    """Get properties associated with a class (as domain or range).

    Includes inherited properties from all superclasses in the hierarchy.
    """
    store = get_store()

    # Get direct properties for this class
    domain_props = _get_properties_for_class(store, ontology, class_uri)

    # Get inherited properties from superclass chain
    superclasses = _get_superclass_chain(store, ontology, class_uri)
    inherited_groups: list[InheritedPropertyGroup] = []
    seen_prop_uris = set(domain_props.keys())  # Don't duplicate props already on this class

    for ancestor in superclasses:
        ancestor_props = _get_properties_for_class(store, ontology, ancestor["uri"])
        # Filter out properties we've already seen
        new_props = {uri: prop for uri, prop in ancestor_props.items() if uri not in seen_prop_uris}
        if new_props:
            inherited_groups.append(InheritedPropertyGroup(
                from_class=ancestor,
                properties=sorted(new_props.values(), key=lambda x: x.label or "")
            ))
            seen_prop_uris.update(new_props.keys())

    # Properties where this class is the range (these properties POINT TO this class)
    range_query = f"""
    SELECT DISTINCT ?prop ?propLabel ?propType ?domain ?domainLabel WHERE {{
        GRAPH <{ontology}> {{
            ?prop <http://www.w3.org/2000/01/rdf-schema#range> <{class_uri}> .
            OPTIONAL {{ ?prop <http://www.w3.org/2000/01/rdf-schema#label> ?propLabel }}
            OPTIONAL {{ ?prop a ?propType . FILTER(?propType IN (<{OWL_OBJECT_PROPERTY}>, <{OWL_DATATYPE_PROPERTY}>, <{OWL_ANNOTATION_PROPERTY}>)) }}
            OPTIONAL {{
                ?prop <http://www.w3.org/2000/01/rdf-schema#domain> ?domain .
                OPTIONAL {{ ?domain <http://www.w3.org/2000/01/rdf-schema#label> ?domainLabel }}
            }}
        }}
    }}
    """
    range_results = store.query(range_query)

    # Group by property
    range_props: dict[str, PropertyInfo] = {}
    for r in range_results:
        prop_uri = r.get("prop")
        if not prop_uri:
            continue
        if prop_uri not in range_props:
            prop_type_uri = r.get("propType", "")
            prop_type = "ObjectProperty"
            if OWL_DATATYPE_PROPERTY in prop_type_uri:
                prop_type = "DatatypeProperty"
            elif OWL_ANNOTATION_PROPERTY in prop_type_uri:
                prop_type = "AnnotationProperty"

            range_props[prop_uri] = PropertyInfo(
                uri=prop_uri,
                label=r.get("propLabel") or _extract_local_name(prop_uri),
                property_type=prop_type,
                domains=[],
                ranges=[{"uri": class_uri, "label": _extract_local_name(class_uri)}]
            )
        domain_uri = r.get("domain")
        if domain_uri and not domain_uri.startswith("_:"):
            existing_domains = [d["uri"] for d in range_props[prop_uri].domains]
            if domain_uri not in existing_domains:
                range_props[prop_uri].domains.append({
                    "uri": domain_uri,
                    "label": r.get("domainLabel") or _extract_local_name(domain_uri)
                })

    return ClassProperties(
        domain_of=sorted(domain_props.values(), key=lambda x: x.label or ""),
        inherited=inherited_groups,
        range_of=sorted(range_props.values(), key=lambda x: x.label or "")
    )


@app.get("/api/property", response_model=PropertyInfo)
async def get_property_info(ontology: str, property: str) -> PropertyInfo:
    """Get detailed information about a property including domains and ranges."""
    store = get_store()

    # Detect property type
    entity_type = _detect_entity_type(store, ontology, property)
    prop_type = entity_type if entity_type in ["ObjectProperty", "DatatypeProperty", "AnnotationProperty"] else "ObjectProperty"

    # Get basic info
    info_query = f"""
    SELECT ?label WHERE {{
        GRAPH <{ontology}> {{
            OPTIONAL {{ <{property}> <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
        }}
    }} LIMIT 1
    """
    info_results = store.query(info_query)
    label = info_results[0].get("label") if info_results else None

    # Get domains
    domain_query = f"""
    SELECT DISTINCT ?domain ?domainLabel WHERE {{
        GRAPH <{ontology}> {{
            <{property}> <http://www.w3.org/2000/01/rdf-schema#domain> ?domain .
            FILTER(isIRI(?domain))
            OPTIONAL {{ ?domain <http://www.w3.org/2000/01/rdf-schema#label> ?domainLabel }}
        }}
    }}
    """
    domain_results = store.query(domain_query)
    domains = [
        {"uri": r["domain"], "label": r.get("domainLabel") or _extract_local_name(r["domain"])}
        for r in domain_results if r.get("domain")
    ]

    # Get ranges
    range_query = f"""
    SELECT DISTINCT ?range ?rangeLabel WHERE {{
        GRAPH <{ontology}> {{
            <{property}> <http://www.w3.org/2000/01/rdf-schema#range> ?range .
            FILTER(isIRI(?range))
            OPTIONAL {{ ?range <http://www.w3.org/2000/01/rdf-schema#label> ?rangeLabel }}
        }}
    }}
    """
    range_results = store.query(range_query)
    ranges = [
        {"uri": r["range"], "label": r.get("rangeLabel") or _extract_local_name(r["range"])}
        for r in range_results if r.get("range")
    ]

    return PropertyInfo(
        uri=property,
        label=label or _extract_local_name(property),
        property_type=prop_type,
        domains=domains,
        ranges=ranges
    )


@app.get("/api/codelist", response_model=CodeListInfo | None)
async def get_codelist_info(ontology: str, entity: str) -> CodeListInfo | None:
    """Get code list members if the entity is a code list/enumeration."""
    store = get_store()

    # Detect which pattern this entity uses
    pattern = _detect_codelist_pattern(store, ontology, entity)
    if not pattern:
        return None

    # Get entity label
    label_query = f"""
    SELECT ?label WHERE {{
        GRAPH <{ontology}> {{
            <{entity}> <http://www.w3.org/2000/01/rdf-schema#label> ?label .
        }}
    }} LIMIT 1
    """
    label_result = store.query(label_query)
    entity_label = label_result[0].get("label") if label_result else None

    members: list[CodeListMember] = []

    if pattern == "skos_scheme":
        # Get members via skos:inScheme
        members_query = f"""
        SELECT DISTINCT ?member ?label ?notation ?description WHERE {{
            GRAPH <{ontology}> {{
                ?member <{SKOS_IN_SCHEME}> <{entity}> .
                OPTIONAL {{
                    ?member <{SKOS_PREF_LABEL}> ?label .
                }}
                OPTIONAL {{
                    ?member <http://www.w3.org/2000/01/rdf-schema#label> ?rdfsLabel .
                }}
                OPTIONAL {{
                    ?member <http://www.w3.org/2004/02/skos/core#notation> ?notation .
                }}
                OPTIONAL {{
                    ?member <http://www.w3.org/2004/02/skos/core#definition> ?description .
                }}
                BIND(COALESCE(?label, ?rdfsLabel) AS ?finalLabel)
            }}
        }} ORDER BY ?notation ?label LIMIT 500
        """
        results = store.query(members_query)
        for r in results:
            member_uri = r.get("member")
            if member_uri:
                members.append(CodeListMember(
                    uri=member_uri,
                    label=r.get("label") or r.get("rdfsLabel") or _extract_local_name(member_uri),
                    notation=r.get("notation"),
                    description=r.get("description")
                ))

    elif pattern == "skos_collection":
        # Get members via skos:member
        members_query = f"""
        SELECT DISTINCT ?member ?label ?notation ?description WHERE {{
            GRAPH <{ontology}> {{
                <{entity}> <{SKOS_MEMBER}> ?member .
                OPTIONAL {{ ?member <{SKOS_PREF_LABEL}> ?label }}
                OPTIONAL {{ ?member <http://www.w3.org/2000/01/rdf-schema#label> ?rdfsLabel }}
                OPTIONAL {{ ?member <http://www.w3.org/2004/02/skos/core#notation> ?notation }}
                OPTIONAL {{ ?member <http://www.w3.org/2004/02/skos/core#definition> ?description }}
            }}
        }} ORDER BY ?notation ?label LIMIT 500
        """
        results = store.query(members_query)
        for r in results:
            member_uri = r.get("member")
            if member_uri:
                members.append(CodeListMember(
                    uri=member_uri,
                    label=r.get("label") or r.get("rdfsLabel") or _extract_local_name(member_uri),
                    notation=r.get("notation"),
                    description=r.get("description")
                ))

    elif pattern == "owl_oneof":
        # Get members by traversing rdf:List via property path
        members_query = f"""
        SELECT DISTINCT ?member ?label WHERE {{
            GRAPH <{ontology}> {{
                <{entity}> <{OWL_ONE_OF}>/<{RDF_REST}>*/<{RDF_FIRST}> ?member .
                FILTER(isIRI(?member))
                OPTIONAL {{ ?member <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
            }}
        }} LIMIT 500
        """
        results = store.query(members_query)
        for r in results:
            member_uri = r.get("member")
            if member_uri:
                members.append(CodeListMember(
                    uri=member_uri,
                    label=r.get("label") or _extract_local_name(member_uri),
                    description=None
                ))

    elif pattern == "owl_equivalent_oneof":
        # Get members through equivalentClass -> oneOf -> rdf:List
        members_query = f"""
        SELECT DISTINCT ?member ?label WHERE {{
            GRAPH <{ontology}> {{
                <{entity}> <{OWL_EQUIVALENT_CLASS}>/<{OWL_ONE_OF}>/<{RDF_REST}>*/<{RDF_FIRST}> ?member .
                FILTER(isIRI(?member))
                OPTIONAL {{ ?member <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
            }}
        }} LIMIT 500
        """
        results = store.query(members_query)
        for r in results:
            member_uri = r.get("member")
            if member_uri:
                members.append(CodeListMember(
                    uri=member_uri,
                    label=r.get("label") or _extract_local_name(member_uri),
                    description=None
                ))

    # Sort members by label
    members.sort(key=lambda m: m.label.lower())

    return CodeListInfo(
        uri=entity,
        label=entity_label or _extract_local_name(entity),
        pattern=pattern,
        member_count=len(members),
        members=members
    )


# Well-known URIs to exclude from the tree (they're implicit roots or meta-classes)
EXCLUDED_CLASSES = {
    "http://www.w3.org/2002/07/owl#Thing",
    "http://www.w3.org/2002/07/owl#Nothing",
    "http://www.w3.org/2000/01/rdf-schema#Resource",
    "http://www.w3.org/2000/01/rdf-schema#Class",
    "http://www.w3.org/2002/07/owl#Class",
}

def _extract_namespace(uri: str) -> str:
    """Extract namespace from a URI (everything up to and including last # or /)."""
    hash_idx = uri.rfind("#")
    if hash_idx >= 0:
        return uri[: hash_idx + 1]
    slash_idx = uri.rfind("/")
    if slash_idx >= 0:
        return uri[: slash_idx + 1]
    return uri


def _get_prefix_for_namespace(namespace: str) -> str | None:
    """Get a short prefix for a namespace URI.

    Only returns prefixes from the well-known prefix map (exact matches).
    Does not generate synthetic prefixes from URI structure - those should
    come from stored prefixes extracted from the original RDF file.
    """
    # Only return exact matches from well-known prefixes
    return WELL_KNOWN_PREFIXES.get(namespace)


def _detect_internal_namespaces(class_uris: list[str], threshold: float = 0.05) -> set[str]:
    """Detect internal namespaces by finding common prefixes among classes.

    Uses a two-pass approach:
    1. Find namespace prefixes that contain a significant portion of classes
    2. Also include any namespace that shares a common base with major namespaces

    This handles ontologies like GLOSIS where classes are spread across
    subnamespaces (e.g., glosis/model/layerhorizon/, glosis/model/common/).
    """
    from collections import Counter

    if not class_uris:
        return set()

    # Get all exact namespaces
    all_namespaces = [_extract_namespace(uri) for uri in class_uris]
    namespace_counts = Counter(all_namespaces)
    total = len(class_uris)
    min_count = max(3, int(total * threshold))

    # Find major namespaces (above threshold)
    major_namespaces = {ns for ns, count in namespace_counts.items() if count >= min_count}

    # Find common base prefixes among major namespaces
    # e.g., if we have glosis/model/layerhorizon/ and glosis/model/common/,
    # detect glosis/model/ as a common base
    base_prefixes: set[str] = set()
    for ns in major_namespaces:
        # Try progressively shorter prefixes
        parts = ns.rstrip("/").split("/")
        for i in range(3, len(parts)):  # At least 3 parts (http://domain/path)
            prefix = "/".join(parts[:i]) + "/"
            # Count how many major namespaces share this prefix
            matches = sum(1 for mns in major_namespaces if mns.startswith(prefix))
            if matches >= 2:  # At least 2 major namespaces share this prefix
                base_prefixes.add(prefix)

    # A namespace is internal if:
    # 1. It's a major namespace, OR
    # 2. It starts with a detected base prefix
    internal = set(major_namespaces)
    for ns in namespace_counts.keys():
        if any(ns.startswith(base) for base in base_prefixes):
            internal.add(ns)

    return internal


@app.get("/api/ontologies/{ontology_uri:path}/hierarchy", response_model=list[HierarchyNode])
async def get_class_hierarchy(ontology_uri: str) -> list[HierarchyNode]:
    """Get the full class hierarchy for an ontology.

    Returns all classes with their direct parent URIs, allowing the frontend
    to build the tree structure. Handles multiple inheritance by providing
    all parent URIs for each class.

    External classes (from known external vocabularies) are marked is_external=True
    only if they have no internal descendants. External classes that are ancestors
    of internal classes remain visible in the hierarchy.
    """
    store = get_store()

    # Query for OWL/RDFS classes only (not SKOS concepts)
    query = f"""
    SELECT DISTINCT ?class ?label ?prefixIRI ?parent ?deprecated WHERE {{
        GRAPH <{ontology_uri}> {{
            # Get OWL and RDFS classes
            {{ ?class a <{OWL_CLASS}> . }}
            UNION
            {{ ?class a <{RDFS_CLASS}> . }}

            # Get label
            OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label }}

            # Get prefixIRI (from BioPortal/OntoPortal metadata)
            OPTIONAL {{ ?class <http://data.bioontology.org/metadata/prefixIRI> ?prefixIRI }}

            # Get owl:deprecated status
            OPTIONAL {{ ?class <http://www.w3.org/2002/07/owl#deprecated> ?deprecated }}

            # Get parent via subClassOf
            OPTIONAL {{
                ?class <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent .
                FILTER(isIRI(?parent))
            }}
        }}
    }}
    """
    results = store.query(query)

    # First pass: collect all class URIs
    class_data: list[dict] = []
    for row in results:
        class_uri = row.get("class")
        if not class_uri or class_uri.startswith("_:"):
            continue
        if class_uri in EXCLUDED_CLASSES:
            continue
        class_data.append(row)

    # Get stored namespace config, or fall back to auto-detection
    config = _get_ontology_config(store, ontology_uri)
    if config.selected_namespaces:
        # User has configured namespaces - use those
        internal_namespaces = set(config.selected_namespaces)
    else:
        # No config yet - auto-detect for initial display
        all_class_uris = list({row.get("class") for row in class_data if row.get("class")})
        internal_namespaces = _detect_internal_namespaces(all_class_uris)

    def is_external(uri: str) -> bool:
        """Check if a class is from an external namespace."""
        ns = _extract_namespace(uri)
        return ns not in internal_namespaces

    # Build a map of class URI -> HierarchyNode
    nodes: dict[str, HierarchyNode] = {}
    # Track parent -> children relationships
    children_map: dict[str, list[str]] = {}
    # Track deprecated classes
    deprecated_classes: set[str] = set()

    for row in class_data:
        class_uri = row.get("class")
        if not class_uri:
            continue

        # Check if deprecated
        deprecated_val = row.get("deprecated")
        is_deprecated = str(deprecated_val).lower() == "true" if deprecated_val else False
        if is_deprecated:
            deprecated_classes.add(class_uri)

        if class_uri not in nodes:
            nodes[class_uri] = HierarchyNode(
                uri=class_uri,
                label=row.get("label") or _extract_local_name(class_uri),
                prefix_iri=row.get("prefixIRI"),
                entity_type="Class",
                parent_uris=[],
                is_external=is_external(class_uri),
                is_deprecated=is_deprecated
            )

        # Add parent if present and not excluded
        parent = row.get("parent")
        if parent and parent not in EXCLUDED_CLASSES and not parent.startswith("_:"):
            if parent not in nodes[class_uri].parent_uris:
                nodes[class_uri].parent_uris.append(parent)
            # Track children for ancestor traversal
            if parent not in children_map:
                children_map[parent] = []
            if class_uri not in children_map[parent]:
                children_map[parent].append(class_uri)

    # For external classes, check if they have any internal descendants
    # If so, they should NOT be marked as external (they're useful ancestors)
    def has_internal_descendant(uri: str, visited: set[str]) -> bool:
        """Recursively check if a class has any non-external descendants."""
        if uri in visited:
            return False
        visited.add(uri)

        for child_uri in children_map.get(uri, []):
            child = nodes.get(child_uri)
            if child:
                # If child is internal, we found an internal descendant
                if not is_external(child_uri):
                    return True
                # Otherwise, check child's descendants
                if has_internal_descendant(child_uri, visited):
                    return True
        return False

    # Update is_external: only truly orphaned external classes stay marked
    for uri, node in nodes.items():
        if node.is_external:
            if has_internal_descendant(uri, set()):
                node.is_external = False

    # Filter out deprecated classes unless show_deprecated is enabled
    result_nodes = nodes.values()
    if not config.show_deprecated:
        result_nodes = [n for n in result_nodes if not n.is_deprecated]

    # Sort nodes by label
    return sorted(result_nodes, key=lambda n: n.label.lower())


class CodeListSummary(BaseModel):
    """Summary info about a code list (without members)."""

    uri: str
    label: str
    prefix_iri: str | None = None  # prefixIRI for display name computation
    pattern: str
    member_count: int


@app.get("/api/ontologies/{ontology_uri:path}/codelists", response_model=list[CodeListSummary])
async def list_codelists(ontology_uri: str) -> list[CodeListSummary]:
    """List SKOS concept schemes and collections in an ontology.

    Returns schemes/collections with member counts for the sidebar.
    OWL code list classes (with owl:oneOf) are shown in the class hierarchy instead.
    """
    store = get_store()

    codelists: list[CodeListSummary] = []

    # Pattern 1: SKOS ConceptSchemes with inScheme members
    skos_query = f"""
    SELECT ?scheme ?label (COUNT(DISTINCT ?member) as ?count) WHERE {{
        GRAPH <{ontology_uri}> {{
            ?member <{SKOS_IN_SCHEME}> ?scheme .
            OPTIONAL {{ ?scheme <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
        }}
    }} GROUP BY ?scheme ?label
    """
    skos_results = store.query(skos_query)
    for r in skos_results:
        uri = r.get("scheme")
        if uri and not uri.startswith("_:"):
            codelists.append(CodeListSummary(
                uri=uri,
                label=r.get("label") or _extract_local_name(uri),
                pattern="skos_scheme",
                member_count=int(r.get("count", 0))
            ))

    # Track URIs we've already added
    seen_uris = {cl.uri for cl in codelists}

    # Pattern 2: SKOS Collections with skos:member
    collection_query = f"""
    SELECT ?collection ?label (COUNT(DISTINCT ?member) as ?count) WHERE {{
        GRAPH <{ontology_uri}> {{
            ?collection <{SKOS_MEMBER}> ?member .
            OPTIONAL {{ ?collection <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
        }}
    }} GROUP BY ?collection ?label
    """
    collection_results = store.query(collection_query)
    for r in collection_results:
        uri = r.get("collection")
        if uri and not uri.startswith("_:") and uri not in seen_uris:
            codelists.append(CodeListSummary(
                uri=uri,
                label=r.get("label") or _extract_local_name(uri),
                pattern="skos_collection",
                member_count=int(r.get("count", 0))
            ))
            seen_uris.add(uri)

    # Fetch prefixIRIs for all collected URIs
    if codelists:
        uris_to_check = [cl.uri for cl in codelists]
        prefix_query = f"""
        SELECT ?uri ?prefixIRI WHERE {{
            GRAPH <{ontology_uri}> {{
                VALUES ?uri {{ {' '.join(f'<{u}>' for u in uris_to_check)} }}
                ?uri <http://data.bioontology.org/metadata/prefixIRI> ?prefixIRI .
            }}
        }}
        """
        prefix_results = store.query(prefix_query)
        prefix_map = {r.get("uri"): r.get("prefixIRI") for r in prefix_results if r.get("uri")}

        # Set prefix_iri field (let frontend compute display name)
        for cl in codelists:
            cl.prefix_iri = prefix_map.get(cl.uri)

    # Sort by label
    return sorted(codelists, key=lambda cl: cl.label.lower())


def configure(data_dir: Path) -> None:
    """Configure the web server."""
    global _data_dir, _store
    _data_dir = data_dir
    _store = None  # Reset store to use new path
