"""MCP server for ontology tools."""

import json
from pathlib import Path

from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel

from ait.clients.nvs import NvsClient
from ait.clients.ontoportal import OntoPortalClient, OntoPortalInstance
from ait.store import RdfFormat, Store


class ServerConfig(BaseModel):
    """Configuration for the MCP server."""

    data_dir: Path = Path.home() / ".ait"
    bioportal_api_key: str | None = None
    default_ontoportal: OntoPortalInstance = OntoPortalInstance.BIOPORTAL


# Global state
_config: ServerConfig | None = None
_store: Store | None = None

server = Server("ait")


def get_store() -> Store:
    """Get or create the local RDF store."""
    global _store
    if _store is None:
        config = _config or ServerConfig()
        store_path = config.data_dir / "store"
        _store = Store(store_path)
    return _store


def configure(config: ServerConfig) -> None:
    """Configure the server."""
    global _config
    _config = config
    config.data_dir.mkdir(parents=True, exist_ok=True)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_ontoportal",
            description="Search for terms across ontologies in an OntoPortal repository (BioPortal, AgroPortal, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "ontologies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ontology acronyms to search (e.g., ['GO', 'ENVO']). Empty = all.",
                    },
                    "instance": {
                        "type": "string",
                        "enum": [e.value for e in OntoPortalInstance],
                        "description": "OntoPortal instance to search",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_ontoportal_ontologies",
            description="List all ontologies available in an OntoPortal repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance": {
                        "type": "string",
                        "enum": [e.value for e in OntoPortalInstance],
                        "description": "OntoPortal instance",
                    },
                },
            },
        ),
        Tool(
            name="get_ontology_class",
            description="Get details about a specific class/term from an ontology",
            inputSchema={
                "type": "object",
                "properties": {
                    "ontology": {
                        "type": "string",
                        "description": "Ontology acronym (e.g., 'GO', 'ENVO')",
                    },
                    "class_id": {
                        "type": "string",
                        "description": "Class IRI or identifier",
                    },
                    "instance": {
                        "type": "string",
                        "enum": [e.value for e in OntoPortalInstance],
                        "description": "OntoPortal instance",
                    },
                },
                "required": ["ontology", "class_id"],
            },
        ),
        Tool(
            name="search_nvs",
            description="Search NERC Vocabulary Server for SKOS concepts (oceanographic/environmental terms)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Collection identifier to search within (e.g., 'P01', 'L22')",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_nvs_collections",
            description="List all vocabulary collections in NVS",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="cache_ontology",
            description="Download and cache an ontology locally for faster access and offline use",
            inputSchema={
                "type": "object",
                "properties": {
                    "ontology": {
                        "type": "string",
                        "description": "Ontology acronym",
                    },
                    "instance": {
                        "type": "string",
                        "enum": [e.value for e in OntoPortalInstance],
                        "description": "OntoPortal instance",
                    },
                },
                "required": ["ontology"],
            },
        ),
        Tool(
            name="sparql_query",
            description="Execute a SPARQL query against the local RDF store",
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
            name="list_cached",
            description="List all ontologies/vocabularies cached locally",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    config = _config or ServerConfig()

    match name:
        case "search_ontoportal":
            instance = arguments.get("instance", config.default_ontoportal)
            async with OntoPortalClient(instance, config.bioportal_api_key) as client:
                results = await client.search(
                    arguments["query"],
                    ontologies=arguments.get("ontologies"),
                )
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            [r.model_dump(by_alias=True) for r in results[:20]],
                            indent=2,
                        ),
                    )
                ]

        case "list_ontoportal_ontologies":
            instance = arguments.get("instance", config.default_ontoportal)
            async with OntoPortalClient(instance, config.bioportal_api_key) as client:
                ontologies = await client.list_ontologies()
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            [{"acronym": o.acronym, "name": o.name} for o in ontologies],
                            indent=2,
                        ),
                    )
                ]

        case "get_ontology_class":
            instance = arguments.get("instance", config.default_ontoportal)
            async with OntoPortalClient(instance, config.bioportal_api_key) as client:
                cls = await client.get_class(arguments["ontology"], arguments["class_id"])
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(cls.model_dump(by_alias=True), indent=2),
                    )
                ]

        case "search_nvs":
            async with NvsClient() as client:
                results = await client.search(
                    arguments["query"],
                    collection=arguments.get("collection"),
                )
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            [r.model_dump(by_alias=True) for r in results[:20]],
                            indent=2,
                        ),
                    )
                ]

        case "list_nvs_collections":
            async with NvsClient() as client:
                collections = await client.list_collections()
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            [{"identifier": c.identifier, "title": c.title} for c in collections],
                            indent=2,
                        ),
                    )
                ]

        case "cache_ontology":
            instance = arguments.get("instance", config.default_ontoportal)
            ontology = arguments["ontology"]
            async with OntoPortalClient(instance, config.bioportal_api_key) as client:
                data = await client.download_ontology(ontology)
                store = get_store()
                graph_name = f"urn:ontoportal:{instance}:{ontology}"
                count = store.load_rdf(data, RdfFormat.XML, graph_name)
                return [
                    TextContent(
                        type="text",
                        text=f"Cached {ontology}: loaded {count} triples into local store",
                    )
                ]

        case "sparql_query":
            store = get_store()
            results = store.query(arguments["query"])
            return [
                TextContent(
                    type="text",
                    text=json.dumps(results[:100], indent=2),
                )
            ]

        case "list_cached":
            store = get_store()
            graphs = list(store.graphs())
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"graphs": graphs, "total_triples": len(store)},
                        indent=2,
                    ),
                )
            ]

        case _:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def run_stdio() -> None:
    """Run the server using stdio transport."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
