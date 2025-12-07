<script lang="ts">
	import { ingestOntology, type OntologyInfo } from '$lib/api';
	import OntologyExplorer from './OntologyExplorer.svelte';

	interface Props {
		onIngest?: () => void;
	}

	let { onIngest }: Props = $props();

	interface Tab {
		ontology: OntologyInfo;
		id: string;
	}

	let tabs = $state<Tab[]>([]);
	let activeTabId = $state<string | null>(null);

	// Ingest form state
	let url = $state('');
	let ingesting = $state(false);
	let error = $state<string | null>(null);

	export function openTab(ontology: OntologyInfo) {
		// Check if already open
		const existing = tabs.find((t) => t.ontology.uri === ontology.uri);
		if (existing) {
			activeTabId = existing.id;
			return;
		}

		// Create new tab
		const id = crypto.randomUUID();
		tabs = [...tabs, { ontology, id }];
		activeTabId = id;
	}

	function closeTab(id: string) {
		const idx = tabs.findIndex((t) => t.id === id);
		tabs = tabs.filter((t) => t.id !== id);

		// Update active tab
		if (activeTabId === id) {
			if (tabs.length === 0) {
				activeTabId = null;
			} else if (idx >= tabs.length) {
				activeTabId = tabs[tabs.length - 1].id;
			} else {
				activeTabId = tabs[idx].id;
			}
		}
	}

	function selectTab(id: string) {
		activeTabId = id;
	}

	async function handleIngest() {
		if (!url.trim()) return;

		ingesting = true;
		error = null;

		try {
			const result = await ingestOntology(url.trim());

			// Open the new ontology in a tab
			openTab({
				uri: result.uri,
				label: result.label,
				triple_count: result.triple_count
			});

			// Clear form
			url = '';

			// Notify parent to refresh sidebar
			onIngest?.();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to ingest ontology';
		} finally {
			ingesting = false;
		}
	}

	const activeTab = $derived(tabs.find((t) => t.id === activeTabId));
</script>

<div class="tab-panel">
	{#if tabs.length === 0}
		<div class="empty">
			<div class="ingest-form">
				<h2>Import an Ontology</h2>
				<p class="hint">Enter an OntoPortal URL (BioPortal, AgroPortal, EcoPortal, MatPortal)</p>

				<form onsubmit={(e) => { e.preventDefault(); handleIngest(); }}>
					<input
						type="url"
						bind:value={url}
						placeholder="https://agroportal.lirmm.fr/ontologies/GLOSIS"
						disabled={ingesting}
					/>

					<button type="submit" disabled={ingesting || !url.trim()}>
						{#if ingesting}
							Importing...
						{:else}
							Import Ontology
						{/if}
					</button>
				</form>

				{#if error}
					<p class="error">{error}</p>
				{/if}
			</div>
		</div>
	{:else}
		<div class="tab-bar">
			{#each tabs as tab (tab.id)}
				<div
					class="tab"
					class:active={tab.id === activeTabId}
					onclick={() => selectTab(tab.id)}
					onkeydown={(e) => e.key === 'Enter' && selectTab(tab.id)}
					role="tab"
					tabindex="0"
				>
					<span class="tab-label">{tab.ontology.label ?? tab.ontology.uri}</span>
					<button
						class="close"
						onclick={(e) => {
							e.stopPropagation();
							closeTab(tab.id);
						}}
						title="Close tab"
					>
						×
					</button>
				</div>
			{/each}
		</div>
		<div class="tab-content">
			{#if activeTab}
				{#key activeTab.id}
					<OntologyExplorer
						ontologyUri={activeTab.ontology.uri}
						ontologyLabel={activeTab.ontology.label ?? undefined}
					/>
				{/key}
			{/if}
		</div>
	{/if}
</div>

<style>
	.tab-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		padding: var(--space-6);
	}

	.ingest-form {
		max-width: 480px;
		width: 100%;
	}

	.ingest-form h2 {
		font-size: var(--text-xl);
		font-weight: 400;
		color: var(--text-primary);
		margin-bottom: var(--space-2);
	}

	.hint {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		margin-bottom: var(--space-5);
		line-height: var(--leading-relaxed);
	}

	form {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	input[type='url'] {
		padding: var(--space-3) var(--space-4);
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-primary);
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		outline: none;
		transition: var(--transition-fast);
	}

	input:focus {
		border-color: var(--border-focus);
	}

	input::placeholder {
		color: var(--text-muted);
	}

	input:disabled {
		opacity: 0.6;
	}

	button[type='submit'] {
		padding: var(--space-3) var(--space-5);
		background: var(--accent);
		border: none;
		border-radius: var(--radius-md);
		color: var(--bg-surface);
		font-family: var(--font-sans);
		font-size: var(--text-sm);
		font-weight: 500;
		cursor: pointer;
		transition: var(--transition-fast);
	}

	button[type='submit']:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	button[type='submit']:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error {
		margin-top: var(--space-4);
		padding: var(--space-3);
		background: rgba(170, 51, 51, 0.08);
		border: 1px solid rgba(170, 51, 51, 0.2);
		border-radius: var(--radius-md);
		color: var(--color-error);
		font-size: var(--text-sm);
	}

	.tab-bar {
		display: flex;
		background: var(--bg-subtle);
		border-bottom: 1px solid var(--border);
		overflow-x: auto;
		flex-shrink: 0;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: none;
		border: none;
		border-right: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		max-width: 200px;
		white-space: nowrap;
		outline: none;
		transition: var(--transition-fast);
	}

	.tab:hover {
		background: var(--bg-muted);
	}

	.tab.active {
		background: var(--bg-base);
		color: var(--text-primary);
		border-bottom: 2px solid var(--accent);
		margin-bottom: -1px;
	}

	.tab-label {
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.close {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		height: 18px;
		padding: 0;
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		color: var(--text-tertiary);
		cursor: pointer;
		font-size: 1rem;
		line-height: 1;
		transition: var(--transition-fast);
	}

	.close:hover {
		background: var(--bg-muted);
		color: var(--text-primary);
	}

	.tab-content {
		flex: 1;
		overflow: hidden;
	}
</style>
