# Target Vocabularies for Testing

> Vocabularies to import for testing ait's multi-schema support

## NERC Vocabulary Server (NVS) - Pure SKOS

NVS provides SKOS vocabularies for oceanographic and marine science. These are pure SKOS (no OWL classes), making them ideal test cases for SKOS-specific features.

### L22 - SeaVoX Device Catalogue
- **URL**: https://vocab.nerc.ac.uk/collection/L22/current/
- **Purpose**: Controlled vocabulary for device/instrument categories
- **Pattern**: SKOS Collection with Concepts

### L06 - SeaVoX Platform Categories
- **URL**: https://vocab.nerc.ac.uk/collection/L06/current/
- **Purpose**: Platform types (ships, buoys, floats, gliders, etc.)
- **Pattern**: SKOS Collection with Concepts

### L05 - SeaDataNet Device Categories
- **URL**: https://vocab.nerc.ac.uk/collection/L05/current/
- **Purpose**: Instrument and sensor categories
- **Pattern**: SKOS Collection with Concepts

## Hybrid OWL+SKOS (Already Imported)

### GLOSIS
- **Source**: AgroPortal
- **URL**: https://agroportal.lirmm.fr/ontologies/GLOSIS
- **Pattern**: OWL classes + SKOS ConceptSchemes for code lists
- **See**: docs/analysis/glosis-ontology-analysis.md

## Pure OWL (To Import)

### ENVO - Environment Ontology
- **Source**: OBO Foundry
- **URL**: http://purl.obolibrary.org/obo/envo.owl
- **Pattern**: Pure OWL, OBO Foundry conventions
- **Why**: Good contrast to SKOS vocabs, follows OBO best practices

---

## Ontology Sources

### OLS4 (EBI Ontology Lookup Service)
- **MCP Server**: https://www.ebi.ac.uk/ols4/api/mcp
- **Web UI**: https://www.ebi.ac.uk/ols4/
- **Coverage**: 250+ ontologies including OBO Foundry, EFO, and domain-specific ontologies
- **Note**: Added as MCP server in `.mcp.json` - can query directly via Claude

### OntoPortal Instances (via ait API)
- BioPortal, AgroPortal, EcoPortal, MatPortal
- Requires API keys in `.env`

### NERC Vocabulary Server (via ait client)
- Pure SKOS vocabularies
- Client in `ait/clients/nvs.py`

---

## NVS Integration Notes

The existing `ait/clients/nvs.py` has a client for NVS API. Key endpoints:

```
GET /collection/{id}/current/    - Get collection metadata
GET /collection/{id}/current/?_profile=nvs&_mediatype=application/rdf+xml  - Get RDF
```

NVS uses:
- `skos:Collection` for vocabulary collections
- `skos:Concept` for terms
- `skos:member` to link collection to concepts
- `skos:prefLabel`, `skos:altLabel`, `skos:definition` for labels
- `skos:broader`, `skos:narrower` for hierarchy (where applicable)
