# Ontology Overview UX Design Exploration

## Problem Statement

When exploring ontologies like SFWO or CSOPRA, the class hierarchy alone doesn't communicate "what this ontology is about." Analysis revealed:

- **SFWO**: 43% native classes, 2% native properties - defines trophic/functional groups for soil food web organisms
- **CSOPRA**: 6% native classes, 40% native properties - primarily an integration schema for agricultural carbon data

These are "integration ontologies" that primarily compose and connect existing terms. The class tree shows a mix of native and imported content without distinction, making it hard to understand the ontology's purpose.

## Design Goals

1. **Immediate comprehension**: User should understand "what is this ontology?" within 10 seconds
2. **Distinguish native vs imported**: Make it obvious what's original vs reused
3. **Show integration patterns**: Reveal which ontologies are being composed
4. **Support different mental models**: Some users want hierarchy, others want composition view

---

## Concept 1: Ontology Overview Dashboard

Replace the immediate jump to class tree with an overview page when loading an ontology.

```
┌─────────────────────────────────────────────────────────────────┐
│  CSOPRA                                                         │
│  Carbon and SOil PRoperties in Agriculture                      │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   78,989     │  │     312      │  │     156      │          │
│  │   triples    │  │   classes    │  │  properties  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌─ Composition ─────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  Native (CSOPRA)     ████░░░░░░░░░░░░░░░░░░░░░░  6%       │ │
│  │  AGRO                ██████████░░░░░░░░░░░░░░░░  21%      │ │
│  │  ENVO                ████████░░░░░░░░░░░░░░░░░░  17%      │ │
│  │  CHEBI               ██████░░░░░░░░░░░░░░░░░░░░  14%      │ │
│  │  UO                  █████░░░░░░░░░░░░░░░░░░░░░  12%      │ │
│  │  Other (8 sources)   ████████████████░░░░░░░░░░  30%      │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  This is an INTEGRATION ONTOLOGY that composes terms from       │
│  10 source ontologies to model agricultural carbon data.        │
│  Native contributions focus on measurement types, crop          │
│  classifications, and data properties.                          │
│                                                                 │
│  [Explore Class Hierarchy]  [Browse by Source]  [Native Only]   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key features:**
- Stats at a glance (triples, classes, properties)
- Visual composition bar showing namespace distribution
- Auto-generated description based on analysis
- Multiple entry points into the ontology

**Implementation notes:**
- Query classes/properties grouped by namespace (extract from URI)
- Identify "native" namespace from ontology URI or most common custom namespace
- Generate description template based on composition ratios

---

## Concept 2: Source-Grouped Explorer

Alternative to class hierarchy - group classes by their source ontology.

```
┌─────────────────────────────────────────────────────────────────┐
│  Browse by Source                                               │
│  ─────────────────                                              │
│                                                                 │
│  ▼ Native (CSOPRA)                           19 classes         │
│    ├─ FodderBeets                                               │
│    ├─ WinterWheat                                               │
│    ├─ CloverMixture                                             │
│    ├─ SoilOrganicCarbonStock                                    │
│    ├─ CarbonInputObs                                            │
│    └─ ... 14 more                                               │
│                                                                 │
│  ▶ AGRO (Agronomy Ontology)                  65 classes         │
│  ▶ ENVO (Environment Ontology)               53 classes         │
│  ▶ CHEBI (Chemical Entities)                 44 classes         │
│  ▶ UO (Units Ontology)                       38 classes         │
│  ▶ NCBITaxon                                 22 classes         │
│  ▶ PATO                                      15 classes         │
│  ▶ IAO                                       12 classes         │
│  ▶ Other sources...                          63 classes         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key features:**
- Immediate visual of "where does content come from?"
- Native content at top, emphasized
- Collapsible sections for each source
- Click to expand and see terms from that source

**Implementation notes:**
- Group HierarchyNode by namespace
- Sort by: native first, then by count descending
- Need namespace → ontology label mapping (could use prefix.cc or hardcode common ones)

---

## Concept 3: Visual Distinction in Class Tree

Enhance existing class tree with visual markers for native vs imported.

```
┌─────────────────────────────────────────────────────────────────┐
│  Class Hierarchy                          [Native only ○]       │
│  ─────────────────                                              │
│                                                                 │
│  ▼ Thing                                                        │
│    ▼ continuant                                    BFO          │
│      ▼ independent continuant                      BFO          │
│        ▼ material entity                           BFO          │
│          ▼ ● SoilOrganicCarbonStock               CSOPRA        │
│          ▼ soil                                    ENVO          │
│          ▼ ● CarbonInputObs                       CSOPRA        │
│          ▼ agricultural field                      AGRO          │
│                                                                 │
│  Legend: ● = native to this ontology                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Options for visual distinction:**
1. **Dot/badge indicator**: Small colored dot next to native classes
2. **Muted styling**: Imported classes shown in lighter gray
3. **Source badge**: Small label showing source ontology (BFO, ENVO, etc.)
4. **Toggle filter**: "Native only" toggle to hide all imported classes

**Implementation notes:**
- Add `source_namespace` or `is_native` to HierarchyNode
- Compute native namespace from ontology URI pattern
- CSS styling for visual distinction

---

## Concept 4: Integration Graph

Visual graph showing import relationships and term counts.

```
                    ┌─────────┐
                    │  BFO    │
                    │  (12)   │
                    └────┬────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────┴────┐    ┌─────┴─────┐   ┌────┴────┐
    │  ENVO   │    │   AGRO    │   │  CHEBI  │
    │  (53)   │    │   (65)    │   │  (44)   │
    └────┬────┘    └─────┬─────┘   └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                  ┌──────┴──────┐
                  │   CSOPRA    │
                  │   (native)  │
                  │     19      │
                  └─────────────┘
```

**Key features:**
- Shows ontology as composition of sources
- Edge thickness or labels show term counts
- Click nodes to filter tree to that source
- Reveals the ontology's "shape"

**Implementation notes:**
- More complex to implement
- Could use simple SVG or a library like D3
- Would need to infer import hierarchy or just show flat composition

---

## Concept 5: "What's New Here" Panel

Dedicated panel answering "what does this ontology contribute?"

```
┌─────────────────────────────────────────────────────────────────┐
│  What's New in SFWO                                             │
│  ─────────────────────                                          │
│                                                                 │
│  SFWO contributes 43 classes and 2 properties not found         │
│  elsewhere. These fall into several categories:                 │
│                                                                 │
│  TROPHIC GROUPS (27 classes)                                    │
│  ├─ microbivory - organisms that feed on microbes               │
│  ├─ omnivory - organisms with mixed feeding strategies          │
│  ├─ predaceous - predatory organisms                            │
│  ├─ aphidophage - organisms that feed on aphids                 │
│  └─ ... more                                                    │
│                                                                 │
│  FUNCTIONAL CLASSIFICATIONS (12 classes)                        │
│  ├─ collector gatherer - organisms that collect detritus        │
│  ├─ collector filterer - filter-feeding organisms               │
│  └─ ... more                                                    │
│                                                                 │
│  TAXONOMIC GROUPINGS (4 classes)                                │
│  ├─ Formicidae.farmers - ant species that farm fungi            │
│  └─ ... more                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key features:**
- Focuses attention on novel contributions
- Groups native terms by category (manual or auto-clustered)
- Explains the ontology's value proposition

**Implementation notes:**
- Would need clustering or manual categorization
- Could auto-group by parent class or common label patterns
- Most valuable but hardest to automate well

---

## Concept 6: Ontology Type Classification

Auto-classify ontologies and show type prominently.

**Types:**
- **Domain Ontology**: >50% native content, focused vocabulary
- **Integration Ontology**: <30% native, primarily composes others
- **Application Ontology**: Mixed, built for specific use case
- **Upper Ontology**: Foundational, abstract concepts (BFO, DOLCE)
- **Vocabulary**: Primarily individuals/instances (code lists)

```
┌─────────────────────────────────────────────────────────────────┐
│  CSOPRA                                                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  INTEGRATION ONTOLOGY                                           │
│                                                                 │
│  Composes terms from 10 source ontologies to create a           │
│  unified schema for agricultural carbon research data.          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Classification heuristics:**
- Native class % < 20% → likely integration
- Native property % > 30% with low native class % → data schema
- Native class % > 60% → domain ontology
- Most classes are individuals → vocabulary/code list

---

## Recommended Implementation Path

### Phase 1: Quick Wins
1. **Add composition stats to existing config/info panel**
   - Show native vs imported breakdown
   - List source ontologies with counts
   - Low effort, high information value

2. **Add "Native only" filter toggle**
   - Filter hierarchy to native classes only
   - Simple boolean filter on existing tree

### Phase 2: Overview Dashboard
3. **Create Ontology Overview component**
   - Stats, composition bar, source list
   - Entry point before drilling into hierarchy
   - Auto-generated summary text

### Phase 3: Alternative Views
4. **Source-grouped browser**
   - Alternative to hierarchy view
   - Tab or toggle to switch views

5. **Visual distinction in tree**
   - Badge/styling for native vs imported
   - Source namespace labels

### Phase 4: Advanced
6. **Integration graph visualization**
7. **"What's New" analysis panel**
8. **Ontology type classification**

---

---

## Backend API Design

### New Endpoint: `/api/ontologies/{uri}/composition`

Returns composition statistics for an ontology.

```python
class NamespaceStats(BaseModel):
    """Statistics for a single namespace within an ontology."""
    namespace: str           # Full namespace URI
    prefix: str              # Short prefix (e.g., "BFO", "CHEBI")
    label: str               # Human-readable name
    class_count: int         # Number of classes from this namespace
    property_count: int      # Number of properties from this namespace
    is_native: bool          # True if this is the ontology's own namespace
    is_obo: bool             # True if from OBO Foundry


class OntologyComposition(BaseModel):
    """Composition analysis of an ontology."""
    ontology_uri: str
    total_classes: int
    total_properties: int
    total_triples: int
    native_namespace: str | None       # Detected native namespace
    native_class_count: int
    native_property_count: int
    native_class_pct: float            # 0.0 - 1.0
    native_property_pct: float
    namespace_stats: list[NamespaceStats]  # Sorted by count desc
    ontology_type: str                 # "domain", "integration", "application", "vocabulary"
    source_ontologies: list[str]       # List of imported ontology prefixes
```

### Implementation Approach

```python
@app.get("/api/ontologies/{ontology_uri:path}/composition")
async def get_ontology_composition(ontology_uri: str) -> OntologyComposition:
    """Analyze the composition of an ontology by namespace."""

    # Query all class URIs
    class_query = f"""
    SELECT DISTINCT ?class WHERE {{
        GRAPH <{ontology_uri}> {{
            {{ ?class a <{OWL_CLASS}> }}
            UNION
            {{ ?class a <{RDFS_CLASS}> }}
            FILTER(isIRI(?class))
        }}
    }}
    """

    # Query all property URIs
    prop_query = f"""
    SELECT DISTINCT ?prop WHERE {{
        GRAPH <{ontology_uri}> {{
            {{ ?prop a <{OWL_OBJECT_PROPERTY}> }}
            UNION
            {{ ?prop a <{OWL_DATATYPE_PROPERTY}> }}
            UNION
            {{ ?prop a <{OWL_ANNOTATION_PROPERTY}> }}
            FILTER(isIRI(?prop))
        }}
    }}
    """

    # Extract namespaces from URIs and count
    class_ns_counts = defaultdict(int)
    for row in store.query(class_query, ontology_uri):
        ns_info = extract_namespace_info(str(row["class"]))
        class_ns_counts[ns_info["namespace"]] += 1

    # Infer native namespace
    native_ns = infer_native_namespace(ontology_uri, class_ns_counts)

    # Classify ontology type based on composition
    native_pct = class_ns_counts.get(native_ns, 0) / sum(class_ns_counts.values())
    if native_pct > 0.5:
        ont_type = "domain"
    elif native_pct < 0.2:
        ont_type = "integration"
    else:
        ont_type = "application"

    # Build response...
```

### Caching Strategy

Composition analysis is relatively expensive (requires scanning all classes/properties). Options:

1. **Compute on demand, cache in metagraph**: Store results with TTL
2. **Compute on ingest**: Calculate during ontology import, store permanently
3. **Background job**: Lazy compute on first access, update periodically

Recommendation: Compute on ingest and store in metagraph. Update on refresh.

```sparql
# Metagraph storage for composition stats
<{ontology_uri}> ait:nativeNamespace "{ns}" .
<{ontology_uri}> ait:nativeClassCount 43 .
<{ontology_uri}> ait:totalClassCount 100 .
<{ontology_uri}> ait:ontologyType "integration" .
<{ontology_uri}> ait:sourceOntologies "BFO,CHEBI,ENVO,RO" .
```

---

---

## Frontend Component Sketch

### OntologyOverview.svelte

```svelte
<script lang="ts">
  import { getOntologyComposition, type OntologyComposition } from '$lib/api';

  interface Props {
    ontologyUri: string;
    ontologyLabel: string;
    onExploreHierarchy: () => void;
    onBrowseBySource: () => void;
  }

  let { ontologyUri, ontologyLabel, onExploreHierarchy, onBrowseBySource }: Props = $props();

  let composition = $state<OntologyComposition | null>(null);
  let loading = $state(true);

  $effect(() => {
    loadComposition();
  });

  async function loadComposition() {
    loading = true;
    composition = await getOntologyComposition(ontologyUri);
    loading = false;
  }

  const ontologyTypeLabel = $derived(() => {
    switch (composition?.ontology_type) {
      case 'domain': return 'Domain Ontology';
      case 'integration': return 'Integration Ontology';
      case 'application': return 'Application Ontology';
      case 'vocabulary': return 'Vocabulary';
      default: return 'Ontology';
    }
  });

  const nativeStats = $derived(
    composition?.namespace_stats.find(s => s.is_native)
  );
</script>

<div class="ontology-overview">
  <header>
    <h1>{ontologyLabel}</h1>
    <span class="ontology-type-badge">{ontologyTypeLabel}</span>
  </header>

  {#if loading}
    <div class="loading">Analyzing ontology composition...</div>
  {:else if composition}
    <!-- Stats row -->
    <div class="stats-row">
      <div class="stat">
        <span class="stat-value">{composition.total_triples.toLocaleString()}</span>
        <span class="stat-label">triples</span>
      </div>
      <div class="stat">
        <span class="stat-value">{composition.total_classes}</span>
        <span class="stat-label">classes</span>
      </div>
      <div class="stat">
        <span class="stat-value">{composition.total_properties}</span>
        <span class="stat-label">properties</span>
      </div>
    </div>

    <!-- Composition bar -->
    <section class="composition-section">
      <h2>Composition</h2>
      <div class="composition-bar">
        {#each composition.namespace_stats as ns}
          <div
            class="bar-segment"
            class:native={ns.is_native}
            style="width: {ns.class_count / composition.total_classes * 100}%"
            title="{ns.label}: {ns.class_count} classes"
          />
        {/each}
      </div>

      <div class="composition-legend">
        {#each composition.namespace_stats.slice(0, 6) as ns}
          <div class="legend-item" class:native={ns.is_native}>
            <span class="legend-color" />
            <span class="legend-label">{ns.prefix}</span>
            <span class="legend-count">{ns.class_count}</span>
            <span class="legend-pct">
              ({(ns.class_count / composition.total_classes * 100).toFixed(0)}%)
            </span>
          </div>
        {/each}
        {#if composition.namespace_stats.length > 6}
          <div class="legend-item muted">
            + {composition.namespace_stats.length - 6} more sources
          </div>
        {/if}
      </div>
    </section>

    <!-- Auto-generated description -->
    <section class="description-section">
      {#if composition.ontology_type === 'integration'}
        <p>
          This <strong>integration ontology</strong> composes terms from
          {composition.source_ontologies.length} source ontologies.
          It contributes {composition.native_class_count} native classes
          ({(composition.native_class_pct * 100).toFixed(0)}%) and
          {composition.native_property_count} native properties.
        </p>
      {:else if composition.ontology_type === 'domain'}
        <p>
          This <strong>domain ontology</strong> defines
          {composition.native_class_count} classes
          ({(composition.native_class_pct * 100).toFixed(0)}% native content)
          with some terms imported from {composition.source_ontologies.length}
          other ontologies.
        </p>
      {:else}
        <p>
          This ontology contains {composition.total_classes} classes from
          {composition.namespace_stats.length} namespaces.
        </p>
      {/if}
    </section>

    <!-- Action buttons -->
    <div class="actions">
      <button class="primary" onclick={onExploreHierarchy}>
        Explore Class Hierarchy
      </button>
      <button class="secondary" onclick={onBrowseBySource}>
        Browse by Source
      </button>
    </div>
  {/if}
</div>
```

### Integration with OntologyExplorer

The overview could be:
1. **Initial landing view**: Show overview first, then navigate to hierarchy
2. **Collapsible header**: Always visible at top, expands to show full stats
3. **Separate tab**: Tabs for "Overview", "Hierarchy", "By Source"

Recommendation: Start with option 1 (landing view) as it sets context before diving in.

---

## Quick Win: Phase 1 Implementation

If we want to ship something small first, here's a minimal implementation:

### 1. Add composition stats to existing ontology list (2-3 hours)

On the home page ontology cards, show a small composition indicator:

```
┌─────────────────────────────────────────────┐
│  CSOPRA                                     │
│  Carbon and SOil PRoperties in Agriculture  │
│  78,989 triples                             │
│                                             │
│  ████░░░░░░░░░░░░░░░░  6% native classes   │
│  Integrates: AGRO, ENVO, CHEBI, UO +6 more │
│                                             │
│  [Explore]  [Configure]                     │
└─────────────────────────────────────────────┘
```

Changes needed:
- Add `/api/ontologies/{uri}/composition` endpoint
- Modify OntologyInfo to include basic composition summary
- Update OntologyCard.svelte to show mini composition bar

### 2. Add "Native only" toggle to class tree (1-2 hours)

Add a simple toggle in ClassTree header that filters to native classes only.

Changes needed:
- Pass native_namespace to frontend (from composition endpoint or config)
- Add toggle state and filter logic in ClassTree.svelte
- Filter hierarchy nodes where URI starts with native_namespace

### 3. Show source badge in class tree (1 hour)

Add a small muted badge showing source ontology next to each class:

```
▼ material entity                          BFO
  ▼ SoilOrganicCarbonStock               native
  ▼ soil                                   ENVO
```

Changes needed:
- Add source_namespace to HierarchyNode (backend)
- Extract prefix from namespace for display
- Small CSS badge styling

---

## Open Questions

1. **How to identify "native" namespace?**
   - Match against ontology URI?
   - Look for custom (non-OBO, non-standard) namespaces?
   - User configurable?

2. **How to get ontology labels for source namespaces?**
   - Hardcode common OBO ontologies?
   - Query prefix.cc or similar service?
   - Store in metagraph when importing?

3. **Performance concerns?**
   - Namespace analysis on large ontologies could be slow
   - Cache composition stats in metagraph?

4. **Where does this fit in navigation?**
   - Replace current landing view?
   - New tab alongside hierarchy?
   - Expandable section in sidebar?
