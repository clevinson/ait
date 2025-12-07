# ait UI Information Architecture

> Last updated: 2024-12 | Based on current implementation

## Overview

The ait web UI is a three-panel layout for browsing ontologies, with a tab-based system for viewing multiple ontologies simultaneously.

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              ait - Archive of Interconnected Terms       │
├──────────────┬──────────────────────────────────────────────────────────┤
│              │  Tab Bar: [GLOSIS ×] [ENVO ×] ...                        │
│  Ontology    ├──────────┬───────────────────────────────┬───────────────┤
│  List        │  Class   │     Entity Focus View         │   Detail      │
│  Sidebar     │  Tree    │                               │   Panel       │
│              │  +       │  - Type badge + IRI link      │               │
│  - GLOSIS    │  Code    │  - Breadcrumb hierarchy       │  - Defined in │
│    23k trips │  Lists   │  - Description                │  - Annotations│
│              │          │  - Properties / Subclasses    │  - Full IRI   │
│              │          │  - Code list members          │               │
├──────────────┴──────────┴───────────────────────────────┴───────────────┤
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

```
+page.svelte
├── OntologyList.svelte        # Left sidebar - lists all cached ontologies
│   └── Shows: label, triple_count
│
└── TabPanel.svelte            # Main content area
    ├── Ingest form (when no tabs open)
    └── OntologyExplorer.svelte (per tab)
        ├── ClassTree.svelte           # Inner left sidebar
        │   ├── Section: "Classes" (hierarchical tree)
        │   └── Section: "Code Lists" (flat list)
        │
        ├── EntityFocusView.svelte     # Center content
        │   ├── TypeBadge.svelte
        │   ├── IriLink.svelte
        │   ├── HierarchyBreadcrumb.svelte
        │   ├── ClassFocusView.svelte      # For owl:Class
        │   ├── PropertyFlowView.svelte    # For owl:*Property
        │   └── CodeListView.svelte        # For enumerations
        │
        └── DetailPanel.svelte         # Right sidebar
            └── Shows: isDefinedBy, annotations, full IRI
```

## Data Flow

### API Endpoints Used

| Endpoint | Component | Purpose |
|----------|-----------|---------|
| `GET /api/ontologies` | OntologyList | List cached ontologies |
| `GET /api/ontologies/{uri}/hierarchy` | ClassTree | Get OWL class tree |
| `GET /api/ontologies/{uri}/codelists` | ClassTree | Get enumeration summaries |
| `GET /api/entity` | EntityFocusView | Get entity metadata |
| `GET /api/codelist` | EntityFocusView | Get enumeration members |
| `GET /api/class-properties` | ClassFocusView | Get properties for a class |
| `GET /api/property` | PropertyFlowView | Get property domains/ranges |
| `POST /api/query` | DetailPanel | Raw SPARQL for annotations |
| `POST /api/ontologies/ingest` | TabPanel | Import from OntoPortal |

### Entity Types Recognized

```typescript
type OwlEntityType =
  | 'Class'           // owl:Class
  | 'ObjectProperty'  // owl:ObjectProperty
  | 'DatatypeProperty'// owl:DatatypeProperty
  | 'AnnotationProperty' // owl:AnnotationProperty
  | 'NamedIndividual' // owl:NamedIndividual
  | 'ConceptScheme'   // skos:ConceptScheme
  | 'Concept'         // skos:Concept
  | 'Unknown';
```

## Current Visualization Patterns

### TypeBadge Colors

| Type | Color Scheme |
|------|--------------|
| Class | Blue/slate (#4a5d7a) |
| ObjectProperty | Olive green (#5a7a2a) |
| DatatypeProperty | Terra cotta (#a25a3a) |
| AnnotationProperty | Gray |
| NamedIndividual | Purple (#7a5ab0) |
| ConceptScheme | Teal (#006666) |
| Concept | Light teal (#148080) |

### Code List Patterns Detected

| Pattern | Display Name | Detection Method |
|---------|--------------|------------------|
| `skos_scheme` | SKOS Concept Scheme | Members via `skos:inScheme` |
| `skos_collection` | SKOS Collection | Members via `skos:member` |
| `owl_oneof` | OWL Enumeration | Direct `owl:oneOf` list |
| `owl_equivalent_oneof` | OWL Enumeration | Via `owl:equivalentClass` |

## Current Limitations

1. **Single classification view**: ClassTree only shows OWL classes, not SKOS concepts in hierarchy
2. **No multi-type awareness**: Entities that are both `owl:NamedIndividual` AND `skos:Concept` show only primary type
3. **No ontology-level metadata**: No summary of what classification systems an ontology uses
4. **No filtering by type**: Can't filter to "show only SKOS things" or "show only OWL things"
5. **Flat code list display**: Code lists shown as flat list in sidebar, not in tree context

## Navigation Patterns

- **History-based navigation**: Back/forward buttons in EntityFocusView
- **Breadcrumb navigation**: For classes, shows superclass chain
- **Click-to-navigate**: Clicking any class/entity navigates to it
- **Tab persistence**: Each ontology opens in its own tab
