<script lang="ts">
	import { listNamespaces, saveOntologyConfig, type NamespaceInfo } from '$lib/api';
	import { onMount } from 'svelte';

	interface Props {
		ontologyUri: string;
		ontologyLabel: string;
		onClose: () => void;
		onSave: () => void;
	}

	let { ontologyUri, ontologyLabel, onClose, onSave }: Props = $props();

	let namespaces = $state<NamespaceInfo[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);

	// Track selected namespaces locally
	let selectedSet = $state<Set<string>>(new Set());

	onMount(async () => {
		await loadNamespaces();
	});

	async function loadNamespaces() {
		loading = true;
		error = null;

		try {
			namespaces = await listNamespaces(ontologyUri);
			// Initialize selected set from current config
			selectedSet = new Set(namespaces.filter((n) => n.selected).map((n) => n.namespace));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load namespaces';
		} finally {
			loading = false;
		}
	}

	function toggleNamespace(namespace: string) {
		if (selectedSet.has(namespace)) {
			selectedSet.delete(namespace);
		} else {
			selectedSet.add(namespace);
		}
		selectedSet = new Set(selectedSet); // Trigger reactivity
	}

	function selectAll() {
		selectedSet = new Set(namespaces.map((n) => n.namespace));
	}

	function selectNone() {
		selectedSet = new Set();
	}

	async function handleSave() {
		saving = true;
		error = null;

		try {
			await saveOntologyConfig(ontologyUri, [...selectedSet]);
			onSave();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save configuration';
		} finally {
			saving = false;
		}
	}

	// Compute total selected class count
	const selectedClassCount = $derived(
		namespaces
			.filter((n) => selectedSet.has(n.namespace))
			.reduce((sum, n) => sum + n.class_count, 0)
	);

	const totalClassCount = $derived(namespaces.reduce((sum, n) => sum + n.class_count, 0));
</script>

<div class="namespace-config">
	<header class="config-header">
		<div class="header-content">
			<button class="back-button" onclick={onClose} title="Cancel and go back">
				<span class="back-arrow">←</span>
				<span>Back</span>
			</button>
			<div class="header-text">
				<h1>Configure Namespaces</h1>
				<p class="subtitle">{ontologyLabel}</p>
			</div>
		</div>
	</header>

	<main class="config-main">
		{#if loading}
			<div class="status">Loading namespaces...</div>
		{:else if error}
			<div class="status error">{error}</div>
		{:else}
			<div class="help-text">
				<p>Select which namespaces to include in the class hierarchy. Classes from unselected namespaces will be hidden (but can be shown via the toggle in the sidebar).</p>
			</div>

			<div class="selection-controls">
				<button class="control-btn" onclick={selectAll}>Select All</button>
				<button class="control-btn" onclick={selectNone}>Select None</button>
				<span class="selection-summary">
					{selectedSet.size} of {namespaces.length} namespaces selected
					({selectedClassCount} of {totalClassCount} classes)
				</span>
			</div>

			<table class="namespace-table">
				<thead>
					<tr>
						<th class="col-select"></th>
						<th class="col-prefix">Prefix</th>
						<th>Namespace</th>
						<th class="col-count">Classes</th>
					</tr>
				</thead>
				<tbody>
					{#each namespaces as ns (ns.namespace)}
						<tr class="namespace-row" onclick={() => toggleNamespace(ns.namespace)}>
							<td class="col-select">
								<input
									type="checkbox"
									checked={selectedSet.has(ns.namespace)}
									onchange={() => toggleNamespace(ns.namespace)}
									onclick={(e) => e.stopPropagation()}
								/>
							</td>
							<td class="col-prefix">
								{#if ns.prefix}
									<code class="prefix-value">{ns.prefix}</code>
								{:else}
									<span class="no-prefix">—</span>
								{/if}
							</td>
							<td>
								<code class="namespace-uri">{ns.namespace}</code>
							</td>
							<td class="col-count">{ns.class_count}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</main>

	<footer class="config-footer">
		<button class="cancel-btn" onclick={onClose} disabled={saving}>Cancel</button>
		<button class="save-btn" onclick={handleSave} disabled={saving || loading}>
			{#if saving}
				Saving...
			{:else}
				Save Configuration
			{/if}
		</button>
	</footer>
</div>

<style>
	.namespace-config {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--bg-base);
	}

	.config-header {
		padding: var(--space-4) var(--space-5);
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface);
	}

	.header-content {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.back-button {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		font-family: var(--font-sans);
		font-size: var(--text-sm);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.back-button:hover {
		background: var(--bg-muted);
		color: var(--text-primary);
	}

	.back-arrow {
		font-size: var(--text-base);
	}

	.header-text h1 {
		font-size: var(--text-lg);
		font-weight: 400;
		color: var(--text-primary);
		margin: 0;
	}

	.subtitle {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		margin: 0;
		margin-top: var(--space-1);
	}

	.config-main {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-5);
	}

	.status {
		color: var(--text-tertiary);
		font-style: italic;
		padding: var(--space-4);
	}

	.status.error {
		color: var(--color-error);
		font-style: normal;
	}

	.help-text {
		margin-bottom: var(--space-5);
		padding: var(--space-4);
		background: var(--bg-subtle);
		border-radius: var(--radius-md);
		border: 1px solid var(--border);
	}

	.help-text p {
		margin: 0;
		font-size: var(--text-sm);
		color: var(--text-secondary);
		line-height: var(--leading-relaxed);
	}

	.selection-controls {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-4);
		padding-bottom: var(--space-4);
		border-bottom: 1px solid var(--border);
	}

	.control-btn {
		padding: var(--space-1) var(--space-3);
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.control-btn:hover {
		background: var(--bg-muted);
		color: var(--text-primary);
	}

	.selection-summary {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		margin-left: auto;
	}

	.namespace-table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--text-sm);
	}

	.namespace-table thead {
		position: sticky;
		top: 0;
		background: var(--bg-surface);
		z-index: 1;
	}

	.namespace-table th {
		text-align: left;
		padding: var(--space-2) var(--space-3);
		border-bottom: 1px solid var(--border);
		font-weight: 500;
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.namespace-table td {
		padding: var(--space-2) var(--space-3);
		border-bottom: 1px solid var(--border);
		vertical-align: middle;
	}

	.namespace-row {
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.namespace-row:hover {
		background: var(--bg-muted);
	}

	.col-select {
		width: 32px;
	}

	.col-prefix {
		width: 120px;
	}

	.col-count {
		width: 60px;
		text-align: right;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
	}

	.prefix-value {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--accent);
		background: var(--bg-subtle);
		padding: 2px 6px;
		border-radius: var(--radius-sm);
	}

	.no-prefix {
		color: var(--text-tertiary);
	}

	.namespace-uri {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		word-break: break-all;
	}

	.config-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-5);
		border-top: 1px solid var(--border);
		background: var(--bg-surface);
	}

	.cancel-btn,
	.save-btn {
		padding: var(--space-2) var(--space-5);
		border-radius: var(--radius-md);
		font-family: var(--font-sans);
		font-size: var(--text-sm);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.cancel-btn {
		background: none;
		border: 1px solid var(--border);
		color: var(--text-secondary);
	}

	.cancel-btn:hover:not(:disabled) {
		background: var(--bg-muted);
		color: var(--text-primary);
	}

	.save-btn {
		background: var(--accent);
		border: none;
		color: white;
	}

	.save-btn:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.save-btn:disabled,
	.cancel-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
