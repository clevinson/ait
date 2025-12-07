# GLOSIS Ontology Analysis

> Analysis date: 2024-12 | Source: AgroPortal

## Overview

GLOSIS (Global Soil Information System) is a soil science ontology that demonstrates a **hybrid OWL+SKOS pattern** for modeling domain knowledge with enumerated code lists.

**Key stats:**
- Total triples: 23,352
- Graph URI: `https://data.agroportal.lirmm.fr/ontologies/GLOSIS`

## Classification System Usage

### Type Counts

| Classification System | Type | Count |
|----------------------|------|-------|
| **OWL** | owl:NamedIndividual | 1,492 |
| | owl:Class | 729 |
| | owl:ObjectProperty | 58 |
| | owl:AnnotationProperty | 36 |
| | owl:DatatypeProperty | 19 |
| **SKOS** | skos:Concept | 1,212 |
| | skos:ConceptScheme | 122 |
| **RDFS** | rdfs:Class | 1 |

### Namespace Usage by rdf:type

| Namespace | Distinct Types | Total Usages |
|-----------|----------------|--------------|
| OWL (w3.org/2002/07/owl#) | 9 | 3,194 |
| SKOS (w3.org/2004/02/skos/core#) | 2 | 1,334 |
| GLOSIS codelists (w3id.org/glosis/model/codelists/) | 91 | 937 |
| GLOSIS procedure (w3id.org/glosis/model/procedure/) | 27 | 275 |
| DBpedia ontology | 2 | 148 |
| SOSA (sensors/observations) | 1 | 137 |
| QUDT (units) | 2 | 33 |
| FOAF | 1 | 4 |
| VOAF | 1 | 2 |
| DCAT | 1 | 1 |

## Multi-Typing Pattern Analysis

### The Key Overlap: NamedIndividual + Concept

| Category | Count |
|----------|-------|
| owl:NamedIndividual only | 280 |
| **Both NamedIndividual + Concept** | **1,212** |
| skos:Concept only | 0 |

**Finding: 100% of SKOS Concepts are dual-typed as owl:NamedIndividual.**

This is intentional design:
- `owl:NamedIndividual` enables OWL reasoning and instance relationships
- `skos:Concept` enables vocabulary navigation, labels, and SKOS hierarchy

### No Class/ConceptScheme Overlap

| Overlap | Count |
|---------|-------|
| owl:Class + skos:ConceptScheme | 0 |

Classes and ConceptSchemes are kept strictly separate in GLOSIS.

## Architectural Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                     GLOSIS Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐         ┌─────────────────────────┐        │
│  │   OWL Classes   │         │   SKOS ConceptSchemes   │        │
│  │     (729)       │         │        (122)            │        │
│  │                 │         │  (enumeration buckets)  │        │
│  └────────┬────────┘         └────────────┬────────────┘        │
│           │                               │                      │
│           │ rdf:type (instances)          │ skos:inScheme        │
│           ▼                               ▼                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │         owl:NamedIndividual + skos:Concept          │        │
│  │                     (1,212)                          │        │
│  │                                                      │        │
│  │  Also typed with domain-specific classes:           │        │
│  │  - PhysioChemicalPropertyCode (91)                  │        │
│  │  - LithologyValueCode (88)                          │        │
│  │  - CropClassValueCode (57)                          │        │
│  │  - LandUseClassValueCode (50)                       │        │
│  │  - etc.                                             │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                  │
│  ┌─────────────────┐                                            │
│  │ NamedIndividual │  280 individuals not in SKOS               │
│  │     only        │  (procedures, other instances)             │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Domain-Specific Type Examples

The top domain-specific classes (from glosis namespace) used as rdf:type:

| Class | Instance Count | Category |
|-------|----------------|----------|
| PhysioChemicalPropertyCode | 91 | Code list |
| LithologyValueCode | 88 | Code list |
| CropClassValueCode | 57 | Code list |
| LandUseClassValueCode | 50 | Code list |
| HumanInfluenceClassValueCode | 35 | Code list |
| PHProcedure | 29 | Procedure |
| VegetationClassValueCode | 29 | Code list |
| TotalCarbonateEquivalentProcedure | 28 | Procedure |
| ExtractableElementsProcedure | 25 | Procedure |
| PSAProcedure | 25 | Procedure |

## Implications for ait UI

### What GLOSIS Teaches Us

1. **Multi-type is common**: Entities often have 3+ types (NamedIndividual + Concept + domain class)
2. **ConceptSchemes organize enumerations**: 122 concept schemes act as "buckets" for code list values
3. **OWL Classes define structure**: The 729 classes define the domain model shape
4. **Properties connect things**: 58 object properties + 19 data properties define relationships
5. **Procedures are individuals**: The 280 non-SKOS individuals are mostly procedure definitions

### UI Improvements Needed

1. **Show all types**: When viewing an entity, show ALL its rdf:types, not just primary
2. **Ontology-level summary**: Show "This ontology uses: OWL, SKOS" badges in sidebar
3. **Classification filter**: Allow filtering tree to "SKOS only" or "OWL only" view
4. **Better code list context**: Show which ConceptScheme a Concept belongs to
5. **Domain type visibility**: Show domain-specific types (like `LithologyValueCode`) prominently

## SPARQL Queries Used

### Count by type
```sparql
SELECT ?type (COUNT(DISTINCT ?entity) AS ?count)
WHERE {
  GRAPH <https://data.agroportal.lirmm.fr/ontologies/GLOSIS> {
    ?entity a ?type .
    FILTER(?type IN (owl:Class, owl:NamedIndividual, skos:Concept, ...))
  }
}
GROUP BY ?type
```

### Find multi-typed entities
```sparql
SELECT ?entity (GROUP_CONCAT(DISTINCT STRAFTER(STR(?type), "#"); separator=", ") AS ?types)
WHERE {
  GRAPH <...> {
    ?entity a owl:NamedIndividual .
    ?entity a skos:Concept .
    ?entity a ?type .
  }
}
GROUP BY ?entity
```

### Namespace usage
```sparql
SELECT ?namespace (COUNT(DISTINCT ?type) AS ?type_count) (COUNT(?s) AS ?usage_count)
WHERE {
  GRAPH <...> {
    ?s a ?type .
    BIND(STRBEFORE(STR(?type), "#") AS ?namespace)
  }
}
GROUP BY ?namespace
```
