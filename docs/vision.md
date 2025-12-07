# ait - Project Vision

> **ait** (Archive of Interconnected Terms): A local-first tool for ontology exploration, connecting external knowledge graphs to personal data schemas.

## Purpose

ait serves multiple purposes for Cory's ontology work:

### 1. Personal Exploration
- Browse and understand different ontologies from various sources
- Analyze how ontologies use different RDF classification systems (OWL, SKOS, RDFS)
- Compare modeling patterns across ontologies
- Inform decisions about which ontologies to leverage in LinkML projects

### 2. Local-First MCP Server
- Pull ontologies into a local graph database (pyoxigraph)
- Expose ontology data to Claude Code via MCP tools
- Run SPARQL queries locally without depending on external servers
- Cache ontologies for offline access and fast querying

### 3. Clear Browsing UI
- Visual exploration of class hierarchies and relationships
- Navigate between related concepts
- Understand property domains and ranges
- View enumerated code lists and their members

### 4. Future: LinkML Integration
- Connect ontology terms to personal datasets and data schemas
- Map external vocabulary terms to LinkML schema elements
- Use established ontologies to enhance schema semantics

### 5. Future: Ontology Editing/Publishing
- Edit and manage OWL ontologies locally
- Edit and manage SKOS vocabularies
- Publish to repositories like AgroPortal

## Design Principles

### Local-First
> "Ontology work is often local-first, and users shouldn't need to depend on big servers being spun up."

- All data stored locally in `~/.ait/store`
- No cloud dependencies for core functionality
- Fast, offline-capable queries
- User owns their data

### OBO Foundry Alignment
> "I really like OBO Foundry and probably want to leverage their recommendations / guidelines as much as possible."

- Follow OBO Foundry best practices where applicable
- OBO Academy as a resource for ontology design patterns
- Consider OBO principles when evaluating ontologies
- Prefer OBO-compliant ontologies when available

### Multi-Schema Awareness
Real-world ontologies mix multiple classification systems:
- **OWL**: Classes, properties, individuals, restrictions
- **SKOS**: Concepts, concept schemes, collections, semantic relations
- **RDFS**: Basic class/property hierarchies
- **Domain-specific**: Custom types within ontology namespaces

ait should make these relationships visible, not hide them.

### Aesthetic Sensibility
Design influences (from CLAUDE.md):
- Kraznahorkai, WG Sebald, Tarkovsky (contemplative, layered)
- Deleuze & Guattari rhizomatic thinking (interconnected, non-hierarchical)
- Sea Ranch, Roberto Burle Marx (clean, natural, intentional)
- "Lagend" concept (goods recovered from depth)

The UI should feel thoughtful, not cluttered. Information density where useful, whitespace where needed.

## Target Ontology Sources

### Currently Supported
- **OntoPortal instances**: BioPortal, AgroPortal, EcoPortal, MatPortal
  - Via REST API with authentication
  - Download full ontology RDF

### Planned
- **NERC Vocabulary Server (NVS)**: Marine/oceanographic SKOS vocabularies
  - Already has client code in `ait/clients/nvs.py`
  - SKOS-focused collections

- **OBO Foundry**: Biomedical ontologies
  - Direct OWL file downloads
  - Well-documented patterns

- **Direct URL import**: Any RDF file accessible via URL
  - Support RDF/XML, Turtle, N-Triples formats

## Technical Stack

- **Backend**: Python 3.11+, Poetry, FastAPI
- **Storage**: pyoxigraph (embedded RDF store)
- **Frontend**: SvelteKit (in `web/` directory)
- **AI Integration**: MCP server for Claude Code
- **CLI**: Typer

## Key Workflows

### 1. Import and Explore
```
User finds ontology on AgroPortal
  → Pastes URL into ait
  → ait downloads and caches locally
  → User browses class hierarchy
  → User examines properties and code lists
  → Claude helps with SPARQL queries via MCP
```

### 2. Analyze Ontology Patterns
```
User imports ontology
  → ait detects classification systems used (OWL, SKOS, etc.)
  → User sees type distribution summary
  → User filters to view specific classification system
  → User understands modeling patterns
```

### 3. Future: Connect to LinkML
```
User has LinkML schema
  → User finds relevant ontology term in ait
  → User maps schema slot to ontology property
  → Schema gains semantic richness
  → Data becomes more interoperable
```

## Non-Goals (For Now)

- Full ontology authoring (use Protégé for that)
- Reasoning/inference (just data exploration)
- Multi-user collaboration
- Cloud hosting
- Large-scale data integration

## Name Origin

**ait** (also spelled "eyot"): a small river island

Also an acronym: **A**rchive of **I**nterconnected **T**erms

The metaphor: ontology terms are like small islands in a river of data, connected by relationships but each with their own identity.
