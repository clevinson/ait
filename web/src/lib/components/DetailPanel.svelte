<script lang="ts">
	import { getEntityInfo, executeQuery, getDisplayName, type EntityInfo, type DisplayNameMode } from '$lib/api';
	import { prefixStore, getPrefixedForm } from '$lib/prefixContext';
	import IriLink from './IriLink.svelte';

	interface Props {
		ontologyUri: string;
		entityUri: string;
		onNavigate?: (uri: string, label: string) => void;
		displayNameMode?: DisplayNameMode;
	}

	let { ontologyUri, entityUri, onNavigate, displayNameMode = 'label' }: Props = $props();

	// Get prefix map for formatting URIs
	const prefixes = $derived($prefixStore);

	/**
	 * Format a URI for display: prefixed form (prefix:localName) or full URI
	 */
	function formatUri(uri: string): string {
		const prefixed = getPrefixedForm(prefixes, uri);
		if (prefixed) {
			return `${prefixed.prefix}:${prefixed.localName}`;
		}
		return uri;
	}

	interface PropertyValue {
		predicate: string;
		predicateLabel: string;
		value: string;
	}

	interface RelatedEntity {
		uri: string;
		label: string;
	}

	let entityInfo = $state<EntityInfo | null>(null);
	let annotations = $state<PropertyValue[]>([]);
	let seeAlso = $state<RelatedEntity[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Load details when entityUri changes
	$effect(() => {
		if (entityUri) {
			loadDetails();
		}
	});

	async function loadDetails() {
		loading = true;
		error = null;
		annotations = [];
		seeAlso = [];

		try {
			// Get entity info for isDefinedBy
			entityInfo = await getEntityInfo(ontologyUri, entityUri);

			// Query for all literal properties and annotations
			const query = `
				SELECT DISTINCT ?predicate ?value WHERE {
					GRAPH <${ontologyUri}> {
						<${entityUri}> ?predicate ?value .
						FILTER(isLiteral(?value))
					}
				} LIMIT 100
			`;

			const result = await executeQuery(query);

			// Filter out prefixIRI and IDENTIFIER annotations
		const excludePredicates = ['prefixIRI', 'IDENTIFIER'];
		annotations = result.results
			.map((r) => ({
				predicate: String(r.predicate),
				predicateLabel: extractLocalName(String(r.predicate)),
				value: String(r.value)
			}))
			.filter((a) => !excludePredicates.includes(a.predicateLabel));

		// Sort by predicate label, but put common ones first (definition before comment)
		const priority = ['label', 'definition', 'description', 'comment'];
			annotations.sort((a, b) => {
				const aIdx = priority.indexOf(a.predicateLabel.toLowerCase());
				const bIdx = priority.indexOf(b.predicateLabel.toLowerCase());
				if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
				if (aIdx !== -1) return -1;
				if (bIdx !== -1) return 1;
				return a.predicateLabel.localeCompare(b.predicateLabel);
			});

			// Query for rdfs:seeAlso links
			const seeAlsoQuery = `
				SELECT DISTINCT ?related ?label WHERE {
					GRAPH <${ontologyUri}> {
						<${entityUri}> <http://www.w3.org/2000/01/rdf-schema#seeAlso> ?related .
						FILTER(isIRI(?related))
						OPTIONAL { ?related <http://www.w3.org/2000/01/rdf-schema#label> ?label }
					}
				} LIMIT 20
			`;
			const seeAlsoResult = await executeQuery(seeAlsoQuery);
			seeAlso = seeAlsoResult.results.map((r) => ({
				uri: String(r.related),
				label: r.label ? String(r.label) : extractLocalName(String(r.related))
			}));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load details';
		} finally {
			loading = false;
		}
	}

	function extractLocalName(uri: string): string {
		const hashIdx = uri.lastIndexOf('#');
		const slashIdx = uri.lastIndexOf('/');
		const idx = Math.max(hashIdx, slashIdx);
		return idx >= 0 ? uri.slice(idx + 1) : uri;
	}

	function handleNavigate(entity: RelatedEntity) {
		if (onNavigate) {
			onNavigate(entity.uri, entity.label);
		}
	}

	// Group annotations by predicate for display
	const groupedAnnotations = $derived(() => {
		const grouped = new Map<string, string[]>();
		for (const prop of annotations) {
			const key = prop.predicateLabel;
			if (!grouped.has(key)) grouped.set(key, []);
			grouped.get(key)!.push(prop.value);
		}
		return grouped;
	});
</script>

<aside class="detail-panel">
	<header class="panel-header">
		<h3>Details</h3>
	</header>

	{#if loading}
		<div class="status">Loading...</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else}
		<div class="details-content">
			<!-- See Also section (prominent navigation links) -->
			{#if seeAlso.length > 0}
				<section class="see-also-section">
					<h4 class="section-label">See Also</h4>
					<ul class="see-also-list">
						{#each seeAlso as related (related.uri)}
							{@const formattedUri = formatUri(related.uri)}
							<li>
								{#if onNavigate}
									<button
										class="see-also-link"
										onclick={() => onNavigate(related.uri, formattedUri)}
										title={related.uri}
									>
										{formattedUri}
									</button>
								{:else}
									<IriLink uri={related.uri} />
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Types section (all rdf:types) -->
			{#if entityInfo?.all_types && entityInfo.all_types.length > 0}
				<section class="types-section">
					<h4 class="section-label">Types</h4>
					<ul class="types-list">
						{#each entityInfo.all_types as typeRef (typeRef.uri)}
							{@const typeName = getDisplayName(typeRef, displayNameMode)}
							<li>
								{#if onNavigate}
									<button
										class="type-link"
										onclick={() => onNavigate(typeRef.uri, typeName)}
										title={typeRef.uri}
									>
										{typeName}
									</button>
								{:else}
									<span class="type-label">{typeName}</span>
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Provenance section (isDefinedBy) -->
			{#if entityInfo?.is_defined_by}
				<section class="provenance-section">
					<h4 class="section-label">Defined in</h4>
					<div class="provenance-value">
						<IriLink uri={entityInfo.is_defined_by} />
					</div>
				</section>
			{/if}

			<!-- Annotations -->
			{#if annotations.length === 0}
				<div class="status">No annotations</div>
			{:else}
				<section class="annotations-section">
					<h4 class="section-label">Annotations</h4>
					<dl class="properties">
						{#each [...groupedAnnotations().entries()] as [predicate, values]}
							<div class="property">
								<dt class="property-name">{predicate}</dt>
								{#each values as value}
									<dd class="property-value">{value}</dd>
								{/each}
							</div>
						{/each}
					</dl>
				</section>
			{/if}

		</div>
	{/if}
</aside>

<style>
	.detail-panel {
		height: 100%;
		overflow-y: auto;
		border-left: 1px solid var(--border);
		background: var(--bg-subtle);
	}

	.panel-header {
		padding: var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.panel-header h3 {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-tertiary);
		margin: 0;
	}

	.status {
		padding: var(--space-4);
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		font-style: italic;
	}

	.status.error {
		color: var(--color-error);
		font-style: normal;
	}

	.details-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		padding: var(--space-3);
	}

	.section-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-tertiary);
		margin: 0 0 var(--space-2);
	}

	.provenance-section {
		padding: var(--space-3);
		background: rgba(74, 93, 122, 0.08);
		border-radius: var(--radius-md);
		border: 1px solid rgba(74, 93, 122, 0.15);
	}

	.provenance-value {
		font-family: var(--font-serif);
		font-size: var(--text-sm);
	}

	.properties {
		margin: 0;
	}

	.property {
		margin-bottom: var(--space-3);
	}

	.property:last-child {
		margin-bottom: 0;
	}

	.property-name {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		margin-bottom: var(--space-1);
	}

	.property-value {
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-primary);
		line-height: var(--leading-relaxed);
		margin: 0;
		padding-left: 0;
	}

	.property-value + .property-value {
		margin-top: var(--space-1);
		padding-top: var(--space-1);
		border-top: 1px solid var(--border);
	}

	/* See Also section */
	.see-also-section {
		padding: var(--space-3);
		background: rgba(59, 130, 246, 0.08);
		border-radius: var(--radius-md);
		border: 1px solid rgba(59, 130, 246, 0.2);
	}

	.see-also-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.see-also-link {
		background: none;
		border: none;
		padding: 0;
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--accent);
		cursor: pointer;
		text-align: left;
		transition: var(--transition-fast);
	}

	.see-also-link:hover {
		color: var(--accent-hover);
		text-decoration: underline;
	}

	.types-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.type-link {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 2px 8px;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.type-link:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.type-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 2px 8px;
	}
</style>
