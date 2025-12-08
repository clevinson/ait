<script lang="ts">
	import { getEntityInfo, getCodeListInfo, getDisplayName, executeQuery, type EntityInfo, type CodeListInfo, type DisplayNameMode } from '$lib/api';
	import { prefixStore, getPrefixedForm } from '$lib/prefixContext';
	import TypeBadge from './TypeBadge.svelte';
	import IriLink from './IriLink.svelte';
	import HierarchyBreadcrumb from './HierarchyBreadcrumb.svelte';
	import ClassFocusView from './ClassFocusView.svelte';
	import PropertyFlowView from './PropertyFlowView.svelte';
	import CodeListView from './CodeListView.svelte';

	interface Props {
		ontologyUri: string;
		entityUri: string;
		onNavigate: (uri: string, label: string) => void;
		onLayoutChange?: (hideDetailPanel: boolean) => void;
		displayNameMode?: DisplayNameMode;
	}

	let { ontologyUri, entityUri, onNavigate, onLayoutChange, displayNameMode = 'label' }: Props = $props();

	// Get prefix map for formatting URIs
	const prefixes = $derived($prefixStore);

	let entityInfo = $state<EntityInfo | null>(null);
	let codeListInfo = $state<CodeListInfo | null>(null);
	let seeAlso = $state<Array<{ uri: string; label: string }>>([]);
	let annotations = $state<Array<{ predicate: string; predicateLabel: string; value: string }>>([]);
	let showAnnotations = $state(false);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Determine if this is a code list view (needs wide layout)
	const isCodeListView = $derived(
		(entityInfo?.entity_type === 'ConceptScheme' || entityInfo?.entity_type === 'Concept') && codeListInfo !== null
	);

	// Notify parent about layout changes
	$effect(() => {
		if (onLayoutChange) {
			onLayoutChange(isCodeListView);
		}
	});

	$effect(() => {
		if (entityUri) {
			loadEntity();
		}
	});

	async function loadEntity() {
		loading = true;
		error = null;
		codeListInfo = null;
		seeAlso = [];
		annotations = [];

		try {
			// Load entity info and check for code list pattern in parallel
			const [entity, codelist] = await Promise.all([
				getEntityInfo(ontologyUri, entityUri),
				getCodeListInfo(ontologyUri, entityUri).catch(() => null)
			]);
			entityInfo = entity;
			codeListInfo = codelist;

			// For code list views, also load See Also and annotations
			if ((entity.entity_type === 'ConceptScheme' || entity.entity_type === 'Concept') && codelist) {
				await loadDetailsForCodeList();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load entity';
		} finally {
			loading = false;
		}
	}

	async function loadDetailsForCodeList() {
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

		// Query for annotations
		const annotationsQuery = `
			SELECT DISTINCT ?predicate ?value WHERE {
				GRAPH <${ontologyUri}> {
					<${entityUri}> ?predicate ?value .
					FILTER(isLiteral(?value))
				}
			} LIMIT 100
		`;
		const annotationsResult = await executeQuery(annotationsQuery);
		const excludePredicates = ['prefixIRI', 'IDENTIFIER', 'label', 'comment'];
		annotations = annotationsResult.results
			.map((r) => ({
				predicate: String(r.predicate),
				predicateLabel: extractLocalName(String(r.predicate)),
				value: String(r.value)
			}))
			.filter((a) => !excludePredicates.includes(a.predicateLabel));
	}

	function extractLocalName(uri: string): string {
		const hashIdx = uri.lastIndexOf('#');
		const slashIdx = uri.lastIndexOf('/');
		const idx = Math.max(hashIdx, slashIdx);
		return idx >= 0 ? uri.slice(idx + 1) : uri;
	}

	function formatUri(uri: string): string {
		const prefixed = getPrefixedForm(prefixes, uri);
		if (prefixed) {
			return `${prefixed.prefix}:${prefixed.localName}`;
		}
		return uri;
	}
</script>

<div class="entity-focus">
	{#if loading}
		<div class="loading-state">Loading...</div>
	{:else if error}
		<div class="error-state">{error}</div>
	{:else if entityInfo}
		<!-- Header with type badge(s) and hierarchy -->
		<header class="entity-header">
			<div class="header-main">
				<div class="type-row">
					<div class="type-badges">
						<TypeBadge type={entityInfo.entity_type} />
						{#if entityInfo.all_types.length > 1}
							{#each entityInfo.all_types as typeRef (typeRef.uri)}
								{@const typeName = getDisplayName(typeRef, displayNameMode)}
								{#if typeName !== entityInfo.entity_type && !['Thing', 'Resource'].includes(typeName)}
									<span class="secondary-type" title={typeRef.uri}>{typeName}</span>
								{/if}
							{/each}
						{/if}
					</div>
					<IriLink uri={entityInfo.uri} />
				</div>

				{#if entityInfo.entity_type === 'Class' && entityInfo.superclasses.length > 0}
					{@const currentDisplayName = getDisplayName({ uri: entityInfo.uri, label: entityInfo.label || '' }, displayNameMode)}
					<HierarchyBreadcrumb
						currentLabel={currentDisplayName}
						superclasses={entityInfo.superclasses}
						{onNavigate}
						{displayNameMode}
					/>
				{:else}
					{@const name = getDisplayName({ uri: entityInfo.uri, label: entityInfo.label || '' }, displayNameMode)}
					<h2 class="entity-label">{name}</h2>
				{/if}

				{#if entityInfo.comment}
					<p class="entity-comment">{entityInfo.comment}</p>
				{/if}

				<!-- Metadata row for code list views: Annotations + See Also -->
				{#if isCodeListView && (seeAlso.length > 0 || annotations.length > 0)}
					<div class="metadata-row">
						{#if annotations.length > 0}
							<div>
								<button class="toggle-btn" onclick={() => showAnnotations = !showAnnotations}>
									<span class="toggle-icon">{showAnnotations ? '−' : '+'}</span>
									<span class="toggle-label">Annotations ({annotations.length})</span>
								</button>
							</div>
						{/if}
						{#if seeAlso.length > 0}
							<div class="see-also-block">
								<span class="metadata-label">See Also</span>
								{#each seeAlso as related, i (related.uri)}
									{@const formattedUri = formatUri(related.uri)}
									<button
										class="see-also-link"
										onclick={() => onNavigate(related.uri, formattedUri)}
										title={related.uri}
									>
										{formattedUri}
									</button>{#if i < seeAlso.length - 1}<span class="separator">,</span>{/if}
								{/each}
							</div>
						{/if}
					</div>
					{#if showAnnotations && annotations.length > 0}
						<dl class="annotations-list">
							{#each annotations as ann}
								<div class="annotation-item">
									<dt>{ann.predicateLabel}</dt>
									<dd>{ann.value}</dd>
								</div>
							{/each}
						</dl>
					{/if}
				{/if}
			</div>
		</header>

		<!-- Content based on entity type -->
		<div class="entity-content">
			{#if entityInfo.entity_type === 'ConceptScheme' || entityInfo.entity_type === 'Concept'}
				<!-- SKOS ConceptScheme or Concept - show code list if available -->
				{#if codeListInfo}
					<CodeListView codeList={codeListInfo} {onNavigate} />
				{:else}
					<div class="generic-content">
						<p class="entity-type-note">
							{entityInfo.entity_type === 'ConceptScheme' ? 'Concept scheme' : 'Concept'} with no enumerated members
						</p>
					</div>
				{/if}
			{:else if entityInfo.entity_type === 'Class'}
				<!-- Code list members (if this class is an enumeration) -->
				{#if codeListInfo}
					<section class="codelist-section">
						<h4 class="section-title">Enumeration Values</h4>
						<CodeListView codeList={codeListInfo} {onNavigate} />
					</section>
				{/if}

				<!-- Class properties -->
				<ClassFocusView {ontologyUri} classUri={entityUri} {onNavigate} />

				<!-- Subclasses section -->
				{#if entityInfo.subclasses.length > 0}
					<section class="subclasses-section">
						<h4 class="section-title">Subclasses</h4>
						<ul class="subclass-list">
							{#each entityInfo.subclasses as sub (sub.uri)}
								{@const subName = getDisplayName(sub, displayNameMode)}
								<li>
									<button
										class="subclass-link"
										onclick={() => onNavigate(sub.uri, subName)}
									>
										{subName}
									</button>
								</li>
							{/each}
						</ul>
					</section>
				{/if}
			{:else if entityInfo.entity_type === 'ObjectProperty' || entityInfo.entity_type === 'DatatypeProperty' || entityInfo.entity_type === 'AnnotationProperty'}
				<PropertyFlowView {ontologyUri} propertyUri={entityUri} {onNavigate} />
			{:else if entityInfo.entity_type === 'NamedIndividual'}
				<!-- Named individual - could be a code list member -->
				<div class="generic-content">
					<p class="entity-type-note">
						Individual instance
					</p>
				</div>
			{:else}
				<div class="generic-content">
					<p class="entity-type-note">
						Viewing {entityInfo.entity_type.toLowerCase()} entity
					</p>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.entity-focus {
		height: 100%;
		overflow-y: auto;
		padding: var(--space-5);
	}

	.loading-state,
	.error-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 200px;
		color: var(--text-tertiary);
		font-style: italic;
	}

	.error-state {
		color: var(--color-error);
		font-style: normal;
	}

	.entity-header {
		margin-bottom: var(--space-5);
		padding-bottom: var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.header-main {
		flex: 1;
		min-width: 0;
	}

	.type-row {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-3);
	}

	.type-badges {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.secondary-type {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		padding: 2px 6px;
		background: var(--bg-muted);
		color: var(--text-secondary);
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
	}

	.entity-label {
		font-size: var(--text-xl);
		font-weight: 400;
		color: var(--text-primary);
		margin: 0;
		line-height: var(--leading-tight);
	}

	.entity-comment {
		margin-top: var(--space-3);
		font-size: var(--text-sm);
		color: var(--text-secondary);
		line-height: var(--leading-relaxed);
	}

	/* Metadata row: See Also + Annotations */
	.metadata-row {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--space-3);
		margin-top: var(--space-3);
	}

	.see-also-block {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: rgba(59, 130, 246, 0.08);
		border: 1px solid rgba(59, 130, 246, 0.2);
		border-radius: var(--radius-md);
	}

	.metadata-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: rgba(59, 130, 246, 0.7);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 500;
	}

	.separator {
		color: var(--text-muted);
		margin-right: var(--space-1);
	}

	.toggle-btn {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-2);
		background: var(--bg-muted);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.toggle-btn:hover {
		background: var(--bg-surface);
		color: var(--text-primary);
	}

	.toggle-icon {
		width: 14px;
		text-align: center;
		font-weight: 600;
	}

	.annotations-list {
		margin: var(--space-2) 0 0;
		padding: var(--space-3);
		background: var(--bg-subtle);
		border-radius: var(--radius-md);
		border: 1px solid var(--border);
	}

	.annotation-item {
		display: flex;
		gap: var(--space-3);
		margin-bottom: var(--space-2);
	}

	.annotation-item:last-child {
		margin-bottom: 0;
	}

	.annotation-item dt {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		min-width: 100px;
		flex-shrink: 0;
	}

	.annotation-item dd {
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-primary);
		margin: 0;
	}

	.see-also-link {
		background: none;
		border: none;
		padding: 0;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--accent);
		cursor: pointer;
		text-align: left;
		transition: var(--transition-fast);
	}

	.see-also-link:hover {
		color: var(--accent-hover);
		text-decoration: underline;
	}

	.entity-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.codelist-section {
		margin-bottom: var(--space-4);
		padding-bottom: var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.subclasses-section {
		margin-top: var(--space-4);
		padding-top: var(--space-4);
		border-top: 1px solid var(--border);
	}

	.section-title {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-tertiary);
		margin-bottom: var(--space-3);
	}

	.subclass-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.subclass-link {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: var(--space-1) var(--space-2);
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-primary);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.subclass-link:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.generic-content {
		padding: var(--space-4);
		text-align: center;
	}

	.entity-type-note {
		color: var(--text-tertiary);
		font-style: italic;
	}
</style>
