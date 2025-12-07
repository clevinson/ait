# ait - Archive of Interconnected Terms

A local-first MCP server for ontology work. The name "ait" means a small river island (synonym of "eyot"), and serves as an acronym for **A**rchive of **I**nterconnected **T**erms.

## Project Context

This is a toy project for Cory to explore local-first ontology management. The theory is that ontology work is often local-first, and users shouldn't need to depend on big servers being spun up.

### Design Inspirations
- Kraznahorkai, WG Sebald, Tarkovsky (aesthetic sensibility)
- Deleuze & Guattari rhizomatic thinking
- Sea Ranch, Roberto Burle Marx (design/landscape)
- "Lagend" (Cory's previous project) - goods on seabed attached to a buoy for later recovery

## Architecture

**Stack:** Python 3.11+ with Poetry

**Core Components:**
- `src/ait/store.py` - Local RDF store using pyoxigraph (embedded, persistent)
- `src/ait/clients/ontoportal.py` - Client for BioPortal/AgroPortal/etc (OntoPortal API)
- `src/ait/clients/nvs.py` - Client for NERC Vocabulary Server (SKOS vocabularies)
- `src/ait/server.py` - MCP server exposing ontology tools to Claude Code
- `src/ait/cli.py` - Typer CLI (serve, status, query, clear commands)

**Design Decisions:**
- Strong typing throughout - use `StrEnum` for constrained string types (see `RdfFormat`, `OntoPortalInstance`)
- Pydantic models for all API responses
- Async clients with context manager support
- Local store persists to `~/.ait/store` by default

## MCP Tools Exposed

- `search_ontoportal` - Search terms across OntoPortal repositories
- `list_ontoportal_ontologies` - List available ontologies
- `get_ontology_class` - Get class details
- `search_nvs` - Search SKOS concepts in NVS
- `list_nvs_collections` - List NVS collections
- `cache_ontology` - Download & cache ontology locally
- `sparql_query` - Query local RDF store
- `list_cached` - Show cached ontologies

## What's Built

```
src/ait/
├── __init__.py
├── cli.py              # Typer CLI
├── server.py           # MCP server
├── store.py            # pyoxigraph wrapper with RdfFormat enum
└── clients/
    ├── __init__.py
    ├── ontoportal.py   # OntoPortal API client (BioPortal, AgroPortal, etc)
    └── nvs.py          # NERC Vocabulary Server client
```

CLI is working: `poetry run ait --help`

## Next Steps (Where We Left Off)

We were about to add a **web UI** for browsing ontologies:

1. **Add FastAPI REST API** to ait (reusing existing store/clients)
   - Need to add `fastapi>=0.115.0` and `uvicorn>=0.32.0` to dependencies

2. **Create SvelteKit frontend** in `web/` directory
   - Monorepo structure (frontend bundled with ait)
   - Python will serve the built frontend in production

3. **Views to build:**
   - Ontology list view (cached + available from portals)
   - Term browser (hierarchical navigation)
   - Eventually: full-functioning web components for local management

## Running the Project

```bash
# Install dependencies
poetry install

# Check CLI
poetry run ait --help

# Show local store status
poetry run ait status

# Start MCP server (for Claude Code)
poetry run ait serve
```

## Claude Code Integration

Add to MCP config:
```json
{
  "mcpServers": {
    "ait": {
      "command": "poetry",
      "args": ["run", "ait", "serve"],
      "cwd": "/Users/cory/Code/ait"
    }
  }
}
```
