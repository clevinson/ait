#!/usr/bin/env python3
"""MCP server for SPARQL queries against NERC Vocabulary Server (NVS).

NVS hosts SKOS vocabularies for oceanographic and environmental sciences,
including SeaDataNet parameters, BODC vocabularies, and more.

Usage:
    python nvs_sparql_server.py

Add to Claude Code MCP config:
    {
      "mcpServers": {
        "nvs": {
          "command": "python",
          "args": ["nvs_sparql_server.py"],
          "cwd": "/path/to/this/script"
        }
      }
    }

Endpoint: http://vocab.nerc.ac.uk/sparql/sparql
Docs: http://vocab.nerc.ac.uk/sparql/
"""

import json
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

NVS_SPARQL_ENDPOINT = "http://vocab.nerc.ac.uk/sparql/sparql"
NVS_BASE_URL = "http://vocab.nerc.ac.uk"

# Optional: local store integration (requires pyoxigraph)
STORE_PATH = Path.home() / ".ait" / "store"

server = Server("nvs-sparql")


async def execute_sparql(
    query: str,
    accept: str = "application/sparql-results+json",
) -> httpx.Response:
    """Execute a SPARQL query against the NVS endpoint.

    Args:
        query: SPARQL query string
        accept: Media type for response. Options:
            - application/sparql-results+json (SELECT/ASK)
            - text/csv (SELECT)
            - text/tab-separated-values (SELECT)
            - text/turtle (CONSTRUCT/DESCRIBE)
            - application/rdf+xml (CONSTRUCT/DESCRIBE)
            - application/ld+json (CONSTRUCT/DESCRIBE)
            - text/n3 (CONSTRUCT/DESCRIBE)
            - application/n-triples (CONSTRUCT/DESCRIBE)
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            NVS_SPARQL_ENDPOINT,
            params={"query": query},
            headers={"Accept": accept},
        )
        response.raise_for_status()
        return response


def format_sparql_json(data: dict, max_results: int = 100) -> str:
    """Format SPARQL JSON results as simplified JSON."""
    results = data.get("results", {}).get("bindings", [])
    simplified = []
    for binding in results[:max_results]:
        row = {}
        for key, val in binding.items():
            row[key] = val.get("value", "")
        simplified.append(row)

    total = len(results)
    shown = len(simplified)
    output = json.dumps(simplified, indent=2)

    if total > shown:
        output += f"\n\n... and {total - shown} more results (truncated)"
    return output


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="nvs_sparql",
            description=(
                "Execute a SPARQL query against the NERC Vocabulary Server (NVS). "
                "NVS contains SKOS vocabularies for oceanographic and environmental terms. "
                "Supports SELECT, ASK, CONSTRUCT, and DESCRIBE queries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SPARQL query. Common prefixes: skos: <http://www.w3.org/2004/02/skos/core#>, dc: <http://purl.org/dc/terms/>",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv", "tsv", "turtle", "rdfxml", "jsonld", "ntriples"],
                        "description": "Response format. Default: json for SELECT, turtle for CONSTRUCT",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="nvs_list_collections",
            description="List all SKOS Collections (vocabularies) in NVS with their URIs and titles",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max collections to return (default: 300)",
                    },
                },
            },
        ),
        Tool(
            name="nvs_list_concept_schemes",
            description="List all SKOS Concept Schemes (thesauri) in NVS",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="nvs_collection_info",
            description="Get detailed information about a specific NVS collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "Collection identifier (e.g., 'P01', 'L22', 'S25', 'C19')",
                    },
                },
                "required": ["collection_id"],
            },
        ),
        Tool(
            name="nvs_search_concepts",
            description="Search for SKOS concepts by label across NVS vocabularies",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "Search term to find in concept labels",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Optional: Collection ID to limit search (e.g., 'P01')",
                    },
                    "exact": {
                        "type": "boolean",
                        "description": "If true, match exact label (default: false, substring match)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 50)",
                    },
                },
                "required": ["term"],
            },
        ),
        Tool(
            name="nvs_get_concept",
            description="Get full details of a specific concept by URI",
            inputSchema={
                "type": "object",
                "properties": {
                    "uri": {
                        "type": "string",
                        "description": "Full URI of the concept",
                    },
                },
                "required": ["uri"],
            },
        ),
        Tool(
            name="nvs_concept_hierarchy",
            description="Get broader/narrower hierarchy for a concept",
            inputSchema={
                "type": "object",
                "properties": {
                    "uri": {
                        "type": "string",
                        "description": "Concept URI",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["broader", "narrower", "both"],
                        "description": "Hierarchy direction (default: both)",
                    },
                },
                "required": ["uri"],
            },
        ),
        Tool(
            name="nvs_download_collection",
            description=(
                "Download an NVS collection as RDF for local caching. "
                "Returns the RDF content which can be loaded into a local triplestore."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "Collection ID (e.g., 'P01', 'L22')",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["turtle", "rdfxml", "jsonld", "ntriples"],
                        "description": "RDF format (default: turtle)",
                    },
                },
                "required": ["collection_id"],
            },
        ),
        Tool(
            name="nvs_count_stats",
            description="Get statistics about NVS: counts of collections, concepts, etc.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


def get_accept_header(format_name: str | None, is_construct: bool = False) -> str:
    """Map format name to Accept header."""
    formats = {
        "json": "application/sparql-results+json",
        "csv": "text/csv",
        "tsv": "text/tab-separated-values",
        "turtle": "text/turtle",
        "rdfxml": "application/rdf+xml",
        "jsonld": "application/ld+json",
        "n3": "text/n3",
        "ntriples": "application/n-triples",
    }
    if format_name and format_name in formats:
        return formats[format_name]
    # Default based on query type
    return "text/turtle" if is_construct else "application/sparql-results+json"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    match name:
        case "nvs_sparql":
            query = arguments["query"]
            query_upper = query.upper()
            is_construct = "CONSTRUCT" in query_upper or "DESCRIBE" in query_upper
            fmt = arguments.get("format")
            accept = get_accept_header(fmt, is_construct)

            try:
                response = await execute_sparql(query, accept)

                if accept == "application/sparql-results+json":
                    data = response.json()
                    bindings = data.get("results", {}).get("bindings", [])
                    result_text = format_sparql_json(data)
                    return [
                        TextContent(
                            type="text",
                            text=f"Found {len(bindings)} results:\n{result_text}",
                        )
                    ]
                else:
                    # Return raw RDF/CSV/TSV
                    return [
                        TextContent(
                            type="text",
                            text=response.text[:50000],  # Truncate large responses
                        )
                    ]
            except httpx.HTTPStatusError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"SPARQL query failed: {e.response.status_code}\n{e.response.text[:1000]}",
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case "nvs_list_collections":
            limit = arguments.get("limit", 300)
            query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/terms/>

SELECT ?collection ?identifier ?title ?description
WHERE {{
    ?collection a skos:Collection .
    OPTIONAL {{ ?collection dc:identifier ?identifier }}
    OPTIONAL {{ ?collection dc:title ?title }}
    OPTIONAL {{ ?collection dc:description ?description }}
}}
ORDER BY ?identifier
LIMIT {limit}
"""
            try:
                response = await execute_sparql(query)
                data = response.json()
                result_text = format_sparql_json(data, max_results=limit)
                count = len(data.get("results", {}).get("bindings", []))
                return [
                    TextContent(
                        type="text",
                        text=f"Found {count} collections:\n{result_text}",
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case "nvs_list_concept_schemes":
            query = """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?scheme ?prefLabel
WHERE {
    ?scheme a skos:ConceptScheme ;
            skos:prefLabel ?prefLabel .
}
ORDER BY ?prefLabel
"""
            try:
                response = await execute_sparql(query)
                data = response.json()
                result_text = format_sparql_json(data)
                count = len(data.get("results", {}).get("bindings", []))
                return [
                    TextContent(
                        type="text",
                        text=f"Found {count} concept schemes:\n{result_text}",
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case "nvs_collection_info":
            collection_id = arguments["collection_id"]
            query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/terms/>

SELECT ?property ?value
WHERE {{
    ?collection a skos:Collection ;
                dc:identifier "{collection_id}" ;
                ?property ?value .
}}
"""
            try:
                response = await execute_sparql(query)
                data = response.json()
                result_text = format_sparql_json(data)

                # Also get concept count
                count_query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/terms/>

SELECT (COUNT(?concept) AS ?conceptCount)
WHERE {{
    ?collection a skos:Collection ;
                dc:identifier "{collection_id}" ;
                skos:member ?concept .
}}
"""
                count_response = await execute_sparql(count_query)
                count_data = count_response.json()
                concept_count = count_data.get("results", {}).get("bindings", [{}])[0].get("conceptCount", {}).get("value", "?")

                return [
                    TextContent(
                        type="text",
                        text=f"Collection {collection_id} ({concept_count} concepts):\n{result_text}",
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case "nvs_search_concepts":
            term = arguments["term"]
            collection = arguments.get("collection")
            exact = arguments.get("exact", False)
            limit = arguments.get("limit", 50)

            # Build filter
            if exact:
                label_filter = f'FILTER(LCASE(STR(?prefLabel)) = LCASE("{term}"))'
            else:
                label_filter = f'FILTER(CONTAINS(LCASE(STR(?prefLabel)), LCASE("{term}")))'

            collection_filter = ""
            if collection:
                collection_filter = f"""
    ?concept skos:inScheme ?scheme .
    FILTER(CONTAINS(STR(?scheme), "/collection/{collection}/"))
"""

            query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?prefLabel ?definition ?altLabel
WHERE {{
    ?concept a skos:Concept ;
             skos:prefLabel ?prefLabel .
    OPTIONAL {{ ?concept skos:definition ?definition }}
    OPTIONAL {{ ?concept skos:altLabel ?altLabel }}
    {collection_filter}
    {label_filter}
}}
LIMIT {limit}
"""
            try:
                response = await execute_sparql(query)
                data = response.json()
                result_text = format_sparql_json(data)
                count = len(data.get("results", {}).get("bindings", []))
                return [
                    TextContent(
                        type="text",
                        text=f"Found {count} concepts matching '{term}':\n{result_text}",
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case "nvs_get_concept":
            uri = arguments["uri"]
            query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?property ?value
WHERE {{
    <{uri}> ?property ?value .
}}
"""
            try:
                response = await execute_sparql(query)
                data = response.json()
                result_text = format_sparql_json(data, max_results=200)
                return [
                    TextContent(
                        type="text",
                        text=f"Concept {uri}:\n{result_text}",
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case "nvs_concept_hierarchy":
            uri = arguments["uri"]
            direction = arguments.get("direction", "both")

            queries = []
            if direction in ("broader", "both"):
                queries.append(("Broader concepts", f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?broader ?broaderLabel
WHERE {{
    <{uri}> skos:broader ?broader .
    OPTIONAL {{ ?broader skos:prefLabel ?broaderLabel }}
}}
"""))
            if direction in ("narrower", "both"):
                queries.append(("Narrower concepts", f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?narrower ?narrowerLabel
WHERE {{
    <{uri}> skos:narrower ?narrower .
    OPTIONAL {{ ?narrower skos:prefLabel ?narrowerLabel }}
}}
"""))

            results = []
            try:
                for label, query in queries:
                    response = await execute_sparql(query)
                    data = response.json()
                    bindings = data.get("results", {}).get("bindings", [])
                    result_text = format_sparql_json(data)
                    results.append(f"{label} ({len(bindings)}):\n{result_text}")

                return [
                    TextContent(
                        type="text",
                        text="\n\n".join(results),
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case "nvs_download_collection":
            collection_id = arguments["collection_id"]
            fmt = arguments.get("format", "turtle")

            # Map format to accept header
            format_headers = {
                "turtle": "text/turtle",
                "rdfxml": "application/rdf+xml",
                "jsonld": "application/ld+json",
                "ntriples": "application/n-triples",
            }
            accept = format_headers.get(fmt, "text/turtle")

            # Use CONSTRUCT to get all triples for the collection
            query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/terms/>

CONSTRUCT {{
    ?s ?p ?o .
}}
WHERE {{
    {{
        ?collection a skos:Collection ;
                    dc:identifier "{collection_id}" .
        ?collection ?p ?o .
        BIND(?collection AS ?s)
    }}
    UNION
    {{
        ?collection a skos:Collection ;
                    dc:identifier "{collection_id}" ;
                    skos:member ?concept .
        ?concept ?p ?o .
        BIND(?concept AS ?s)
    }}
}}
"""
            try:
                response = await execute_sparql(query, accept)
                content = response.text

                # Provide info about the download
                size_kb = len(content) / 1024
                lines = content.count("\n")

                summary = f"Downloaded collection {collection_id} ({size_kb:.1f} KB, ~{lines} lines)\n"
                summary += f"Format: {fmt}\n"
                summary += f"Graph URI suggestion: urn:nvs:collection:{collection_id}\n\n"

                # Truncate if too large for display
                if len(content) > 100000:
                    summary += f"Content (first 100KB of {size_kb:.1f} KB):\n"
                    summary += content[:100000]
                    summary += "\n\n... [truncated]"
                else:
                    summary += "Content:\n"
                    summary += content

                return [TextContent(type="text", text=summary)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error downloading collection: {e}")]

        case "nvs_count_stats":
            queries = {
                "collections": """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT (COUNT(?c) AS ?count) WHERE { ?c a skos:Collection }
""",
                "concepts": """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT (COUNT(?c) AS ?count) WHERE { ?c a skos:Concept }
""",
                "conceptSchemes": """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT (COUNT(?c) AS ?count) WHERE { ?c a skos:ConceptScheme }
""",
            }

            stats = {}
            try:
                for stat_name, query in queries.items():
                    response = await execute_sparql(query)
                    data = response.json()
                    bindings = data.get("results", {}).get("bindings", [])
                    if bindings:
                        stats[stat_name] = bindings[0].get("count", {}).get("value", "?")

                return [
                    TextContent(
                        type="text",
                        text=f"NVS Statistics:\n{json.dumps(stats, indent=2)}",
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        case _:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
