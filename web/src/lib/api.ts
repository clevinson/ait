/**
 * API client for ait backend
 */

const API_BASE = 'http://127.0.0.1:8000/api';

export interface OntologyInfo {
	uri: string;
	label: string | null;
	triple_count: number;
}

export interface GraphNode {
	id: string;
	label: string;
	type: string;
}

export interface GraphEdge {
	source: string;
	target: string;
	label: string;
}

export interface GraphData {
	nodes: GraphNode[];
	edges: GraphEdge[];
}

export interface ClassInfo {
	uri: string;
	label: string;
	comment: string | null;
}

export interface QueryResponse {
	results: Record<string, unknown>[];
	count: number;
}

export interface IngestResponse {
	uri: string;
	label: string;
	triple_count: number;
}

// OWL/SKOS Entity types
export type OwlEntityType =
	| 'Class'
	| 'ObjectProperty'
	| 'DatatypeProperty'
	| 'AnnotationProperty'
	| 'NamedIndividual'
	| 'ConceptScheme'
	| 'Concept'
	| 'Unknown';

export interface EntityRef {
	uri: string;
	label: string;
	prefix_iri?: string | null;
}

export interface EntityInfo {
	uri: string;
	label: string | null;
	prefix_iri: string | null;
	comment: string | null;
	entity_type: OwlEntityType;
	all_types: EntityRef[];
	is_defined_by: string | null;
	superclasses: EntityRef[];
	subclasses: EntityRef[];
}

export interface PropertyInfo {
	uri: string;
	label: string | null;
	property_type: 'ObjectProperty' | 'DatatypeProperty' | 'AnnotationProperty';
	domains: EntityRef[];
	ranges: EntityRef[];
}

export interface InheritedPropertyGroup {
	from_class: EntityRef;
	properties: PropertyInfo[];
}

export interface ClassProperties {
	domain_of: PropertyInfo[];
	inherited: InheritedPropertyGroup[];
	range_of: PropertyInfo[];
}

export interface CodeListMember {
	uri: string;
	label: string;
	notation: string | null;
	description: string | null;
}

export type CodeListPattern = 'skos_scheme' | 'owl_oneof' | 'owl_equivalent_oneof' | 'skos_collection';

export interface CodeListInfo {
	uri: string;
	label: string | null;
	pattern: CodeListPattern;
	member_count: number;
	members: CodeListMember[];
}

export interface HierarchyNode {
	uri: string;
	label: string;
	prefix_iri?: string | null;
	entity_type: string;
	parent_uris: string[];
	is_external: boolean;
}

export interface CodeListSummary {
	uri: string;
	label: string;
	prefix_iri?: string | null;
	pattern: string;
	member_count: number;
}

export interface NamespaceInfo {
	namespace: string;
	prefix: string | null;
	class_count: number;
	selected: boolean;
}

export interface OntologyConfig {
	ontology_uri: string;
	selected_namespaces: string[];
}

export async function listOntologies(): Promise<OntologyInfo[]> {
	const res = await fetch(`${API_BASE}/ontologies`);
	if (!res.ok) throw new Error(`Failed to list ontologies: ${res.statusText}`);
	return res.json();
}

export async function getOntologyGraph(uri: string, limit = 200): Promise<GraphData> {
	const encodedUri = encodeURIComponent(uri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/graph?limit=${limit}`);
	if (!res.ok) throw new Error(`Failed to get graph: ${res.statusText}`);
	return res.json();
}

export async function listClasses(uri: string, limit = 100): Promise<ClassInfo[]> {
	const encodedUri = encodeURIComponent(uri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/classes?limit=${limit}`);
	if (!res.ok) throw new Error(`Failed to list classes: ${res.statusText}`);
	return res.json();
}

export async function executeQuery(sparql: string, limit = 100): Promise<QueryResponse> {
	const res = await fetch(`${API_BASE}/query`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ sparql, limit })
	});
	if (!res.ok) throw new Error(`Query failed: ${res.statusText}`);
	return res.json();
}

export async function ingestOntology(url: string): Promise<IngestResponse> {
	const res = await fetch(`${API_BASE}/ontologies/ingest`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ url })
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(error.detail || 'Failed to ingest ontology');
	}
	return res.json();
}

export async function getEntityInfo(ontologyUri: string, entityUri: string): Promise<EntityInfo> {
	const params = new URLSearchParams({ ontology: ontologyUri, entity: entityUri });
	const res = await fetch(`${API_BASE}/entity?${params}`);
	if (!res.ok) throw new Error(`Failed to get entity info: ${res.statusText}`);
	return res.json();
}

export async function getClassProperties(
	ontologyUri: string,
	classUri: string
): Promise<ClassProperties> {
	const params = new URLSearchParams({ ontology: ontologyUri, class_uri: classUri });
	const res = await fetch(`${API_BASE}/class-properties?${params}`);
	if (!res.ok) throw new Error(`Failed to get class properties: ${res.statusText}`);
	return res.json();
}

export async function getPropertyInfo(
	ontologyUri: string,
	propertyUri: string
): Promise<PropertyInfo> {
	const params = new URLSearchParams({ ontology: ontologyUri, property: propertyUri });
	const res = await fetch(`${API_BASE}/property?${params}`);
	if (!res.ok) throw new Error(`Failed to get property info: ${res.statusText}`);
	return res.json();
}

export async function getCodeListInfo(
	ontologyUri: string,
	entityUri: string
): Promise<CodeListInfo | null> {
	const params = new URLSearchParams({ ontology: ontologyUri, entity: entityUri });
	const res = await fetch(`${API_BASE}/codelist?${params}`);
	if (!res.ok) throw new Error(`Failed to get code list info: ${res.statusText}`);
	const data = await res.json();
	return data; // Returns null if entity is not a code list
}

export async function getClassHierarchy(ontologyUri: string): Promise<HierarchyNode[]> {
	const encodedUri = encodeURIComponent(ontologyUri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/hierarchy`);
	if (!res.ok) throw new Error(`Failed to get class hierarchy: ${res.statusText}`);
	return res.json();
}

export async function listCodeLists(ontologyUri: string): Promise<CodeListSummary[]> {
	const encodedUri = encodeURIComponent(ontologyUri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/codelists`);
	if (!res.ok) throw new Error(`Failed to list code lists: ${res.statusText}`);
	return res.json();
}

export async function listNamespaces(ontologyUri: string): Promise<NamespaceInfo[]> {
	const encodedUri = encodeURIComponent(ontologyUri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/namespaces`);
	if (!res.ok) throw new Error(`Failed to list namespaces: ${res.statusText}`);
	return res.json();
}

export async function getOntologyConfig(ontologyUri: string): Promise<OntologyConfig> {
	const encodedUri = encodeURIComponent(ontologyUri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/config`);
	if (!res.ok) throw new Error(`Failed to get ontology config: ${res.statusText}`);
	return res.json();
}

export async function saveOntologyConfig(
	ontologyUri: string,
	selectedNamespaces: string[]
): Promise<OntologyConfig> {
	const encodedUri = encodeURIComponent(ontologyUri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/config`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			ontology_uri: ontologyUri,
			selected_namespaces: selectedNamespaces
		})
	});
	if (!res.ok) throw new Error(`Failed to save ontology config: ${res.statusText}`);
	return res.json();
}

export async function getOntologyPrefixes(ontologyUri: string): Promise<Record<string, string>> {
	const encodedUri = encodeURIComponent(ontologyUri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/prefixes`);
	if (!res.ok) throw new Error(`Failed to get prefixes: ${res.statusText}`);
	return res.json();
}

export async function refreshOntology(ontologyUri: string): Promise<IngestResponse> {
	const encodedUri = encodeURIComponent(ontologyUri);
	const res = await fetch(`${API_BASE}/ontologies/${encodedUri}/refresh`, {
		method: 'POST'
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(error.detail || 'Failed to refresh ontology');
	}
	return res.json();
}

// ============================================================================
// Display Name Utilities
// ============================================================================

/**
 * Extract the local name from a URI (after last # or /).
 */
export function extractLocalName(uri: string): string {
	const hashIdx = uri.lastIndexOf('#');
	const slashIdx = uri.lastIndexOf('/');
	const idx = Math.max(hashIdx, slashIdx);
	return idx >= 0 ? uri.slice(idx + 1) : uri;
}

/**
 * Extract the local name from a prefixIRI notation (e.g., 'glosis:Foo' -> 'Foo').
 */
export function extractPrefixLocalName(prefixIri: string | null | undefined): string | null {
	if (!prefixIri || !prefixIri.includes(':')) return null;
	const parts = prefixIri.split(':', 2);
	return parts[1] || null;
}

/**
 * Get the display name for an entity with priority:
 * prefixIRI local > label > URI local
 * Works with EntityRef, HierarchyNode, CodeListSummary, or any object with uri/label/prefix_iri
 */
export function getDisplayName(entity: { uri: string; label: string; prefix_iri?: string | null }): string {
	// Priority 1: Local part of prefixIRI
	const prefixLocal = extractPrefixLocalName(entity.prefix_iri);
	if (prefixLocal) return prefixLocal;
	// Priority 2: Label
	if (entity.label) return entity.label;
	// Priority 3: Local part of URI
	return extractLocalName(entity.uri);
}

/**
 * Get the sidebar display name for an entity with priority:
 * prefixIRI local > URI local > label
 * This prioritizes short identifiers over verbose labels for compact sidebar display.
 */
export function getSidebarDisplayName(entity: { uri: string; label?: string; prefix_iri?: string | null }): string {
	// Priority 1: Local part of prefixIRI
	const prefixLocal = extractPrefixLocalName(entity.prefix_iri);
	if (prefixLocal) return prefixLocal;
	// Priority 2: Local part of URI (short identifier)
	const uriLocal = extractLocalName(entity.uri);
	if (uriLocal) return uriLocal;
	// Priority 3: Label (fallback)
	return entity.label || entity.uri;
}
