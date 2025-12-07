<script lang="ts">
	import ClassTree from './ClassTree.svelte';
	import EntityFocusView from './EntityFocusView.svelte';
	import DetailPanel from './DetailPanel.svelte';
	import NamespaceConfig from './NamespaceConfig.svelte';
	import { refreshOntology, getOntologyPrefixes } from '$lib/api';
	import { prefixStore } from '$lib/prefixContext';
	import { onMount } from 'svelte';

	interface Props {
		ontologyUri: string;
		ontologyLabel?: string;
		onRefresh?: () => void;
	}

	let { ontologyUri, ontologyLabel, onRefresh }: Props = $props();

	// Fetch and set prefixes on mount
	onMount(async () => {
		await loadPrefixes();
	});

	async function loadPrefixes() {
		try {
			const prefixes = await getOntologyPrefixes(ontologyUri);
			prefixStore.set(prefixes);
		} catch (e) {
			console.error('Failed to load prefixes:', e);
		}
	}

	// View mode: 'explore' or 'config'
	type ViewMode = 'explore' | 'config';
	let viewMode = $state<ViewMode>('explore');

	// Currently focused entity
	let focusedUri = $state<string | null>(null);
	let focusedLabel = $state<string>('');

	// Reference to ClassTree for refreshing after config change
	let classTreeRef = $state<{ refresh?: () => void } | null>(null);

	// Refresh state
	let refreshing = $state(false);

	// Layout state - hide detail panel for code list views
	let hideDetailPanel = $state(false);

	// Collapsible left sidebar
	let leftSidebarCollapsed = $state(false);

	function handleLayoutChange(shouldHideDetail: boolean) {
		hideDetailPanel = shouldHideDetail;
	}

	function toggleLeftSidebar() {
		leftSidebarCollapsed = !leftSidebarCollapsed;
	}

	// Navigation history for back/forward
	let history = $state<Array<{ uri: string; label: string }>>([]);
	let historyIndex = $state(-1);

	function handleClassSelect(uri: string, label: string) {
		// Add to history (truncate forward history if we navigated back)
		if (historyIndex < history.length - 1) {
			history = history.slice(0, historyIndex + 1);
		}
		history = [...history, { uri, label }];
		historyIndex = history.length - 1;

		focusedUri = uri;
		focusedLabel = label;
	}

	function navigateBack() {
		if (historyIndex > 0) {
			historyIndex--;
			const item = history[historyIndex];
			focusedUri = item.uri;
			focusedLabel = item.label;
		}
	}

	function navigateForward() {
		if (historyIndex < history.length - 1) {
			historyIndex++;
			const item = history[historyIndex];
			focusedUri = item.uri;
			focusedLabel = item.label;
		}
	}

	const canGoBack = $derived(historyIndex > 0);
	const canGoForward = $derived(historyIndex < history.length - 1);

	function openConfig() {
		viewMode = 'config';
	}

	function closeConfig() {
		viewMode = 'explore';
	}

	function handleConfigSaved() {
		viewMode = 'explore';
		// Trigger a reload of the class tree to reflect new config
		// We'll use a key to force remount
		configVersion++;
	}

	// Increment this to force ClassTree to remount after config changes
	let configVersion = $state(0);

	// Derive display label from ontologyLabel or extract from URI
	const displayLabel = $derived(ontologyLabel || ontologyUri.split('/').pop() || 'Ontology');

	async function handleRefresh() {
		if (refreshing) return;
		refreshing = true;
		try {
			await refreshOntology(ontologyUri);
			// Reload prefixes (may have changed)
			await loadPrefixes();
			// Reset navigation state
			focusedUri = null;
			focusedLabel = '';
			history = [];
			historyIndex = -1;
			// Force ClassTree to remount
			configVersion++;
			// Notify parent if callback provided
			onRefresh?.();
		} catch (e) {
			console.error('Failed to refresh ontology:', e);
		} finally {
			refreshing = false;
		}
	}
</script>

{#if viewMode === 'config'}
	<NamespaceConfig
		{ontologyUri}
		ontologyLabel={displayLabel}
		onClose={closeConfig}
		onSave={handleConfigSaved}
	/>
{:else}
	<div class="ontology-explorer">
		<aside class="tree-sidebar" class:collapsed={leftSidebarCollapsed}>
			<div class="sidebar-header">
				<button
					class="collapse-btn"
					onclick={toggleLeftSidebar}
					title={leftSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
				>
					{leftSidebarCollapsed ? '→' : '←'}
				</button>
				{#if !leftSidebarCollapsed}
					<span class="ontology-name" title={ontologyUri}>{displayLabel}</span>
					<div class="header-actions">
						<button
							class="header-btn"
							onclick={handleRefresh}
							disabled={refreshing}
							title="Refresh ontology from source"
						>
							<svg
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								class:spinning={refreshing}
							>
								<path d="M23 4v6h-6M1 20v-6h6" />
								<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
							</svg>
						</button>
						<button class="header-btn" onclick={openConfig} title="Configure namespaces">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<circle cx="12" cy="12" r="3"/>
								<path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
							</svg>
						</button>
					</div>
				{/if}
			</div>
			{#if !leftSidebarCollapsed}
				{#key configVersion}
					<ClassTree
						{ontologyUri}
						selectedClassUri={focusedUri}
						onSelect={handleClassSelect}
					/>
				{/key}
			{/if}
		</aside>

		<main class="focus-area">
			{#if focusedUri}
				<nav class="nav-bar">
					<button
						class="nav-btn"
						onclick={navigateBack}
						disabled={!canGoBack}
						title="Back"
					>
						←
					</button>
					<button
						class="nav-btn"
						onclick={navigateForward}
						disabled={!canGoForward}
						title="Forward"
					>
						→
					</button>
				</nav>
				<EntityFocusView
					{ontologyUri}
					entityUri={focusedUri}
					onNavigate={handleClassSelect}
					onLayoutChange={handleLayoutChange}
				/>
			{:else}
				<div class="empty-state">
					<p>Select a class from the tree to explore</p>
				</div>
			{/if}
		</main>

		{#if focusedUri && !hideDetailPanel}
			<aside class="detail-sidebar">
				<DetailPanel
					{ontologyUri}
					entityUri={focusedUri}
					onNavigate={handleClassSelect}
				/>
			</aside>
		{/if}
	</div>
{/if}

<style>
	.ontology-explorer {
		display: flex;
		height: 100%;
		overflow: hidden;
	}

	.tree-sidebar {
		width: 260px;
		flex-shrink: 0;
		border-right: 1px solid var(--border);
		background: var(--bg-subtle);
		overflow-y: auto;
		overflow-x: hidden;
		display: flex;
		flex-direction: column;
		transition: width 0.2s ease;
	}

	.tree-sidebar.collapsed {
		width: 40px;
		overflow: hidden;
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-3);
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface);
		flex-shrink: 0;
	}

	.collapse-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		padding: 0;
		background: none;
		border: 1px solid transparent;
		border-radius: var(--radius-sm);
		color: var(--text-tertiary);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		cursor: pointer;
		transition: var(--transition-fast);
		flex-shrink: 0;
	}

	.collapse-btn:hover {
		background: var(--bg-muted);
		border-color: var(--border);
		color: var(--text-primary);
	}

	.ontology-name {
		flex: 1;
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		font-weight: 500;
		color: var(--text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.header-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		padding: 0;
		background: none;
		border: 1px solid transparent;
		border-radius: var(--radius-sm);
		color: var(--text-tertiary);
		cursor: pointer;
		transition: var(--transition-fast);
		flex-shrink: 0;
	}

	.header-btn:hover:not(:disabled) {
		background: var(--bg-muted);
		border-color: var(--border);
		color: var(--text-primary);
	}

	.header-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinning {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.focus-area {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		background: var(--bg-base);
	}

	.nav-bar {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface);
		flex-shrink: 0;
	}

	.nav-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		padding: 0;
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
		font-size: var(--text-sm);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.nav-btn:hover:not(:disabled) {
		background: var(--bg-muted);
		color: var(--text-primary);
	}

	.nav-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.detail-sidebar {
		width: var(--detail-panel-width);
		flex-shrink: 0;
		overflow: hidden;
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		padding: var(--space-6);
	}

	.empty-state p {
		font-size: var(--text-base);
		color: var(--text-tertiary);
		font-style: italic;
	}
</style>
