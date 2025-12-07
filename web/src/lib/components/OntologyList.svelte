<script lang="ts">
	import { listOntologies, type OntologyInfo } from '$lib/api';
	import { onMount } from 'svelte';

	interface Props {
		onSelect: (ontology: OntologyInfo) => void;
	}

	let { onSelect }: Props = $props();

	let ontologies = $state<OntologyInfo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			ontologies = await listOntologies();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load ontologies';
		} finally {
			loading = false;
		}
	});

	export async function refresh() {
		loading = true;
		error = null;
		try {
			ontologies = await listOntologies();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load ontologies';
		} finally {
			loading = false;
		}
	}
</script>

<div class="ontology-list">
	<div class="header">
		<h2>Ontologies</h2>
		<button onclick={refresh} disabled={loading} title="Refresh">
			{#if loading}...{:else}↻{/if}
		</button>
	</div>

	{#if error}
		<p class="error">{error}</p>
	{:else if ontologies.length === 0 && !loading}
		<p class="empty">No cached ontologies</p>
	{:else}
		<ul>
			{#each ontologies as ontology (ontology.uri)}
				<li>
					<button class="ontology-item" onclick={() => onSelect(ontology)}>
						<span class="label">{ontology.label ?? ontology.uri}</span>
						<span class="count">{ontology.triple_count} triples</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.ontology-list {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.header h2 {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-tertiary);
	}

	.header button {
		background: none;
		border: 1px solid var(--border);
		color: var(--text-tertiary);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
		font-size: var(--text-sm);
		transition: var(--transition-fast);
	}

	.header button:hover:not(:disabled) {
		background: var(--bg-muted);
		color: var(--text-primary);
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		overflow-y: auto;
		flex: 1;
	}

	li {
		border-bottom: 1px solid var(--border);
	}

	.ontology-item {
		display: flex;
		flex-direction: column;
		width: 100%;
		padding: var(--space-3) var(--space-4);
		background: none;
		border: none;
		color: var(--text-primary);
		text-align: left;
		cursor: pointer;
		gap: var(--space-1);
		transition: var(--transition-fast);
	}

	.ontology-item:hover {
		background: var(--bg-muted);
	}

	.label {
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		word-break: break-word;
		line-height: var(--leading-tight);
	}

	.count {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
	}

	.error {
		color: var(--color-error);
		padding: var(--space-4);
		font-size: var(--text-sm);
	}

	.empty {
		color: var(--text-tertiary);
		padding: var(--space-4);
		font-size: var(--text-sm);
		font-style: italic;
	}
</style>
