# Improvement Plan: RDF Classification System Visibility

> Goal: Make it clear what classification systems (OWL, SKOS, RDFS, etc.) are at play when browsing ontologies, without visual duplication.

## Problem Statement

Currently, ait shows entities through an OWL-centric lens:
- ClassTree shows owl:Class hierarchy only
- TypeBadge shows single primary type
- No indication of what classification systems an ontology uses
- Multi-typed entities (e.g., both NamedIndividual and Concept) lose information

Users exploring vocabularies that are primarily SKOS (like NVS) or hybrid OWL+SKOS (like GLOSIS) can't easily understand the modeling approach.

## Design Principles

1. **OWL as default frame**: Most ontologies use OWL, keep it as primary view
2. **Additive tagging**: Show SKOS/other systems as badges, not replacement views
3. **No duplication**: Don't show same entity twice in different trees
4. **Progressive disclosure**: Summary at top, details on demand
5. **Filterable**: Allow focusing on specific classification systems

## Proposed Changes

### Phase 1: Ontology-Level Awareness

#### 1.1 Classification System Badges in OntologyList

Add badges showing what systems an ontology uses:

```
┌──────────────────────────┐
│  Ontologies              │
├──────────────────────────┤
│  GLOSIS                  │
│  23k triples  [OWL][SKOS]│
├──────────────────────────┤
│  ENVO                    │
│  45k triples  [OWL]      │
├──────────────────────────┤
│  P01 (NVS)               │
│  12k triples  [SKOS]     │
└──────────────────────────┘
```

**Implementation:**
- New API endpoint: `GET /api/ontologies/{uri}/classification-summary`
- Returns: `{ owl: true, skos: true, rdfs: false, domain_types: [...] }`
- Frontend: Small colored badges in OntologyList items

#### 1.2 Ontology Summary Panel

When selecting an ontology (before selecting any entity), show a summary:

```
┌─────────────────────────────────────────┐
│ GLOSIS                                  │
│ Global Soil Information System          │
├─────────────────────────────────────────┤
│ Classification Systems                  │
│ ┌─────┐ ┌──────┐                       │
│ │ OWL │ │ SKOS │                       │
│ └─────┘ └──────┘                       │
├─────────────────────────────────────────┤
│ Type Distribution                       │
│                                         │
│ OWL Classes ████████████████ 729       │
│ SKOS ConceptSchemes ██████ 122          │
│ Named Individuals ████████████████ 1492│
│ SKOS Concepts ██████████████ 1212      │
│ Object Properties ██ 58                 │
│ Data Properties █ 19                    │
│ Annotation Props █ 36                   │
└─────────────────────────────────────────┘
```

### Phase 2: Entity-Level Multi-Type Visibility

#### 2.1 Multi-Type Badges

When an entity has multiple significant types, show all of them:

Current:
```
[INDIVIDUAL] http://w3id.org/.../LithologyValueCode-IA1
```

Proposed:
```
[INDIVIDUAL] [CONCEPT] [LithologyValueCode]
http://w3id.org/.../LithologyValueCode-IA1
```

**Rules:**
- Always show OWL type badge (Class, Individual, Property)
- Add SKOS badge if also skos:Concept or skos:ConceptScheme
- Show up to 1 domain-specific type badge (from ontology namespace)
- Tooltip shows all types on hover

#### 2.2 "Also a" Section in DetailPanel

In the right-hand DetailPanel, add a section showing all types:

```
┌─────────────────┐
│ Details         │
├─────────────────┤
│ TYPES           │
│ • owl:NamedIndividual
│ • skos:Concept  │
│ • glosis:LithologyValueCode
├─────────────────┤
│ DEFINED IN      │
│ ...             │
└─────────────────┘
```

### Phase 3: Filtered Views

#### 3.1 Classification System Filter

Add a filter control to ClassTree sidebar:

```
┌────────────────────────┐
│ View: [All ▼]          │
│   ○ All                │
│   ○ OWL Classes        │
│   ○ SKOS Concepts      │
│   ○ SKOS Schemes       │
│   ○ Individuals        │
└────────────────────────┘
```

**Behavior:**
- "All" (default): Current behavior, shows OWL class tree + code lists
- "OWL Classes": Only owl:Class hierarchy
- "SKOS Concepts": Shows skos:Concept hierarchy (via skos:broader/narrower)
- "SKOS Schemes": Shows skos:ConceptScheme list with member counts
- "Individuals": Flat list of owl:NamedIndividual (paginated)

#### 3.2 SKOS Hierarchy View

When "SKOS Concepts" filter is active, build tree from:
- `skos:broader` / `skos:narrower` relationships
- Group by `skos:inScheme` as top-level

```
┌────────────────────────┐
│ SKOS Concepts          │
├────────────────────────┤
│ ▼ LithologyValueScheme │
│   ├─ Ignite rocks      │
│   │  ├─ Granite        │
│   │  └─ Basalt         │
│   └─ Sedimentary rocks │
│      ├─ Sandstone      │
│      └─ Limestone      │
└────────────────────────┘
```

### Phase 4: Cross-Reference Links

#### 4.1 "Part of Scheme" for Concepts

When viewing a skos:Concept, show which scheme(s) it belongs to:

```
┌─────────────────────────────────────┐
│ [CONCEPT] Granite                   │
│                                     │
│ In scheme: LithologyValueScheme →   │
│                                     │
│ Broader: Igneous rocks →            │
│ Narrower: • Pink granite →          │
│          • Gray granite →           │
└─────────────────────────────────────┘
```

#### 4.2 "Instances" Count for Classes

For owl:Class entities, show instance count:

```
┌─────────────────────────────────────┐
│ [CLASS] LithologyValueCode          │
│                                     │
│ 88 instances (also typed as skos:Concept)
│                                     │
│ Subclasses: ...                     │
│ Properties: ...                     │
└─────────────────────────────────────┘
```

## API Changes Required

### New Endpoints

```
GET /api/ontologies/{uri}/classification-summary
Response: {
  systems: {
    owl: boolean,
    skos: boolean,
    rdfs: boolean
  },
  counts: {
    owl_class: number,
    owl_object_property: number,
    owl_datatype_property: number,
    owl_annotation_property: number,
    owl_named_individual: number,
    skos_concept: number,
    skos_concept_scheme: number,
    skos_collection: number,
    rdfs_class: number
  },
  overlaps: {
    individual_and_concept: number,
    class_and_concept_scheme: number
  }
}
```

```
GET /api/ontologies/{uri}/skos-hierarchy
Response: HierarchyNode[] (same shape as class hierarchy, but built from SKOS relations)
```

```
GET /api/entity (enhanced)
Response: {
  ...existing fields...,
  all_types: string[],  // All rdf:type values
  in_schemes: EntityRef[],  // skos:inScheme targets
  instance_count: number | null  // For classes
}
```

## Component Changes

| Component | Change |
|-----------|--------|
| OntologyList | Add classification system badges |
| OntologyExplorer | Add filter dropdown, summary view |
| ClassTree | Support filtered mode, SKOS hierarchy mode |
| TypeBadge | Support multiple badges, domain type badge |
| EntityFocusView | Show scheme membership, instance counts |
| DetailPanel | Add "Types" section showing all rdf:types |

## Migration Path

1. **Phase 1** can be done independently - additive changes only
2. **Phase 2** requires API enhancement but doesn't break existing UI
3. **Phase 3** is the biggest change - new tree-building logic for SKOS
4. **Phase 4** enhances detail views with cross-references

## Testing with Different Ontologies

After each phase, test with:
- **GLOSIS** (hybrid OWL+SKOS)
- **NVS vocabulary** (pure SKOS)
- **OBO ontology like ENVO** (pure OWL, OBO patterns)
- **Simple test ontology** (minimal, known structure)
