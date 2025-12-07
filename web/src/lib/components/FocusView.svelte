<script lang="ts">
	import { executeQuery } from '$lib/api';

	interface Props {
		ontologyUri: string;
		classUri: string;
		classLabel: string;
		onNavigate: (classUri: string, label: string) => void;
	}

	let { ontologyUri, classUri, classLabel, onNavigate }: Props = $props();

	interface RelatedClass {
		uri: string;
		label: string;
		predicate: string;
		predicateLabel: string;
	}

	let incoming = $state<RelatedClass[]>([]);
	let outgoing = $state<RelatedClass[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Load relationships when classUri changes
	$effect(() => {
		if (classUri) {
			loadRelationships();
		}
	});

	async function loadRelationships() {
		loading = true;
		error = null;
		incoming = [];
		outgoing = [];

		try {
			// Query for outgoing relationships (this class as subject)
			const outQuery = `
				SELECT DISTINCT ?predicate ?object ?objectLabel WHERE {
					GRAPH <${ontologyUri}> {
						<${classUri}> ?predicate ?object .
						OPTIONAL { ?object <http://www.w3.org/2000/01/rdf-schema#label> ?objectLabel }
						FILTER(isIRI(?object))
						FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
					}
				} LIMIT 50
			`;

			// Query for incoming relationships (this class as object)
			const inQuery = `
				SELECT DISTINCT ?predicate ?subject ?subjectLabel WHERE {
					GRAPH <${ontologyUri}> {
						?subject ?predicate <${classUri}> .
						OPTIONAL { ?subject <http://www.w3.org/2000/01/rdf-schema#label> ?subjectLabel }
						FILTER(isIRI(?subject))
						FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
					}
				} LIMIT 50
			`;

			const [outResult, inResult] = await Promise.all([
				executeQuery(outQuery),
				executeQuery(inQuery)
			]);

			outgoing = outResult.results.map((r) => ({
				uri: String(r.object),
				label: String(r.objectLabel || extractLocalName(String(r.object))),
				predicate: String(r.predicate),
				predicateLabel: extractLocalName(String(r.predicate))
			}));

			incoming = inResult.results.map((r) => ({
				uri: String(r.subject),
				label: String(r.subjectLabel || extractLocalName(String(r.subject))),
				predicate: String(r.predicate),
				predicateLabel: extractLocalName(String(r.predicate))
			}));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load relationships';
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

	function handleNavigate(item: RelatedClass) {
		onNavigate(item.uri, item.label);
	}

	// Group relationships by predicate
	const outgoingGrouped = $derived(groupByPredicate(outgoing));
	const incomingGrouped = $derived(groupByPredicate(incoming));

	function groupByPredicate(items: RelatedClass[]): Map<string, RelatedClass[]> {
		const grouped = new Map<string, RelatedClass[]>();
		for (const item of items) {
			const key = item.predicateLabel;
			if (!grouped.has(key)) grouped.set(key, []);
			grouped.get(key)!.push(item);
		}
		return grouped;
	}
</script>

<div class="focus-view">
	<header class="focus-header">
		<h2>{classLabel}</h2>
		<code class="uri">{classUri}</code>
	</header>

	{#if loading}
		<div class="status">Loading relationships...</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else}
		<div class="relationships">
			<!-- Incoming -->
			<section class="relation-section">
				<h3 class="section-title">
					<span class="arrow">←</span> Incoming
					<span class="count">{incoming.length}</span>
				</h3>
				{#if incoming.length === 0}
					<p class="empty">No incoming relationships</p>
				{:else}
					{#each [...incomingGrouped.entries()] as [predicate, items]}
						<div class="predicate-group">
							<div class="predicate-label">{predicate}</div>
							<ul class="related-list">
								{#each items as item (item.uri)}
									<li>
										<button class="related-item" onclick={() => handleNavigate(item)}>
											{item.label}
										</button>
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				{/if}
			</section>

			<!-- Outgoing -->
			<section class="relation-section">
				<h3 class="section-title">
					<span class="arrow">→</span> Outgoing
					<span class="count">{outgoing.length}</span>
				</h3>
				{#if outgoing.length === 0}
					<p class="empty">No outgoing relationships</p>
				{:else}
					{#each [...outgoingGrouped.entries()] as [predicate, items]}
						<div class="predicate-group">
							<div class="predicate-label">{predicate}</div>
							<ul class="related-list">
								{#each items as item (item.uri)}
									<li>
										<button class="related-item" onclick={() => handleNavigate(item)}>
											{item.label}
										</button>
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				{/if}
			</section>
		</div>
	{/if}
</div>

<style>
	.focus-view {
		height: 100%;
		overflow-y: auto;
		padding: var(--space-5);
	}

	.focus-header {
		margin-bottom: var(--space-5);
		padding-bottom: var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.focus-header h2 {
		font-size: var(--text-xl);
		font-weight: 400;
		color: var(--text-primary);
		margin-bottom: var(--space-2);
		line-height: var(--leading-tight);
	}

	.uri {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		word-break: break-all;
	}

	.status {
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		font-style: italic;
		padding: var(--space-4);
	}

	.status.error {
		color: var(--color-error);
		font-style: normal;
	}

	.relationships {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}


	.section-title {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-tertiary);
		margin-bottom: var(--space-3);
	}

	.arrow {
		font-size: var(--text-sm);
	}

	.count {
		font-size: var(--text-xs);
		color: var(--text-muted);
	}

	.empty {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		font-style: italic;
		padding-left: var(--space-2);
	}

	.predicate-group {
		margin-bottom: var(--space-4);
	}

	.predicate-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		margin-bottom: var(--space-2);
		padding-left: var(--space-2);
	}

	.related-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.related-item {
		display: block;
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		padding: var(--space-2) var(--space-3);
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-primary);
		cursor: pointer;
		border-radius: var(--radius-sm);
		transition: var(--transition-fast);
	}

	.related-item:hover {
		background: var(--bg-muted);
		color: var(--accent);
	}
</style>
