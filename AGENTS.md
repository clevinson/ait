# ait - Archive of Interconnected Terms

A local-first MCP server for ontology work. The name "ait" means a small river island (synonym of "eyot"), and serves as an acronym for **A**rchive of **I**nterconnected **T**erms.

## bd Usage (IMPORTANT - Read First)

**bd is Claude's external memory.** Use it proactively without being prompted.

### When to Use bd

1. **Starting a session**: Run `bd list` to see current state
2. **Completing work**: Run `bd close <id>` immediately when done
3. **Starting new work**: Run `bd create` to track what you're doing
4. **Mid-work notes**: Run `bd comment <id> "progress note"` to serialize state
5. **Blocking issues**: Run `bd dep add <id> --blocked-by <other-id>` to track dependencies
6. **Resuming work**: Run `bd show <id>` and `bd comments <id>` to restore context

### bd Commands Quick Reference

```bash
bd list                         # See all open/in-progress issues
bd show <id>                    # Full details on an issue
bd comments <id>                # View comments/progress notes
bd comment <id> "note"          # Add progress note
bd create "title" -d "desc"     # Create new issue
bd update <id> --status in_progress  # Start working
bd close <id>                   # Mark complete
bd dep add <id> --blocked-by <other>  # Track dependencies
```

### State Serialization Pattern

When leaving work mid-task, always comment with:
- What was completed
- What remains
- Any blockers or decisions needed
- Key files/locations to remember

Example:
```bash
bd comment ait-1h5 "Completed: tokens.css, app.css. Remaining: update components to use tokens. Key files: web/src/lib/components/*.svelte"
```

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
- `src/ait/server.py` - HTTP-based MCP server exposing ontology tools
- `src/ait/cli.py` - Typer CLI (serve, status, query, clear commands)
- `src/ait/web.py` - FastAPI REST API for web UI

**Web UI:** `web/` directory - SvelteKit frontend for exploring ontologies

**Standalone Tools:**
- `nvs_sparql_server.py` - Standalone MCP server for NVS SPARQL queries (separate from ait app, for SKOS exploration)

**Design Decisions:**
- Strong typing throughout - use `StrEnum` for constrained string types (see `RdfFormat`, `OntoPortalInstance`)
- Pydantic models for all API responses
- Async clients with context manager support
- Local store persists to `~/.ait/store` by default

## MCP Servers

### ait MCP Server (HTTP-based)
Uses HTTP transport. See `.mcp.json` for current config.

### nvs MCP Server (standalone SKOS explorer)
File: `nvs_sparql_server.py`
Tools: `nvs_sparql`, `nvs_list_collections`, `nvs_list_concept_schemes`, `nvs_collection_info`, `nvs_search_concepts`, `nvs_get_concept`, `nvs_concept_hierarchy`, `nvs_download_collection`, `nvs_count_stats`

## Running the Project

```bash
# Install dependencies
poetry install

# Check CLI
poetry run ait --help

# Show local store status
poetry run ait status

# Start web UI (FastAPI + SvelteKit dev)
poetry run ait web  # or: cd web && npm run dev
```

## Claude Code Integration

See `.mcp.json` for current MCP server configuration.
