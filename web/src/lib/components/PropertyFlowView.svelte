<script lang="ts">
	import { getPropertyInfo, type PropertyInfo, type EntityRef } from '$lib/api';
	import TypeBadge from './TypeBadge.svelte';

	interface Props {
		ontologyUri: string;
		propertyUri: string;
		onNavigate: (uri: string, label: string) => void;
	}

	let { ontologyUri, propertyUri, onNavigate }: Props = $props();

	let propertyInfo = $state<PropertyInfo | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		if (propertyUri) {
			loadProperty();
		}
	});

	async function loadProperty() {
		loading = true;
		error = null;

		try {
			propertyInfo = await getPropertyInfo(ontologyUri, propertyUri);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load property';
		} finally {
			loading = false;
		}
	}

	function handleNavigate(item: EntityRef) {
		onNavigate(item.uri, item.label);
	}
</script>

<div class="property-flow">
	{#if loading}
		<div class="status">Loading property...</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else if propertyInfo}
		<!-- Flow Diagram: Domain → Property → Range -->
		<div class="flow-diagram">
			<!-- Domains (left) -->
			<div class="flow-column domains">
				<div class="column-label">Domain</div>
				{#if propertyInfo.domains.length === 0}
					<div class="flow-node empty">
						<span>any class</span>
					</div>
				{:else}
					{#each propertyInfo.domains as domain (domain.uri)}
						<button class="flow-node clickable" onclick={() => handleNavigate(domain)}>
							{domain.label}
						</button>
					{/each}
				{/if}
			</div>

			<!-- Arrow -->
			<div class="flow-arrow">
				<svg width="60" height="40" viewBox="0 0 60 40">
					<line x1="0" y1="20" x2="50" y2="20" stroke="currentColor" stroke-width="1.5" />
					<polygon points="50,15 60,20 50,25" fill="currentColor" />
				</svg>
			</div>

			<!-- Property (center) -->
			<div class="flow-column property">
				<div class="flow-node property-node">
					<span class="property-label">{propertyInfo.label}</span>
					<TypeBadge type={propertyInfo.property_type} />
				</div>
			</div>

			<!-- Arrow -->
			<div class="flow-arrow">
				<svg width="60" height="40" viewBox="0 0 60 40">
					<line x1="0" y1="20" x2="50" y2="20" stroke="currentColor" stroke-width="1.5" />
					<polygon points="50,15 60,20 50,25" fill="currentColor" />
				</svg>
			</div>

			<!-- Ranges (right) -->
			<div class="flow-column ranges">
				<div class="column-label">Range</div>
				{#if propertyInfo.ranges.length === 0}
					<div class="flow-node empty">
						<span>any value</span>
					</div>
				{:else}
					{#each propertyInfo.ranges as range (range.uri)}
						<button class="flow-node clickable" onclick={() => handleNavigate(range)}>
							{range.label}
						</button>
					{/each}
				{/if}
			</div>
		</div>

		<!-- Property description if available -->
		<div class="property-meta">
			<code class="property-uri">{propertyInfo.uri}</code>
		</div>
	{/if}
</div>

<style>
	.property-flow {
		padding: var(--space-4);
	}

	.status {
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		font-style: italic;
	}

	.status.error {
		color: var(--color-error);
		font-style: normal;
	}

	.flow-diagram {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-6) var(--space-4);
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		min-height: 200px;
	}

	.flow-column {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		min-width: 120px;
	}

	.column-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: var(--space-1);
	}

	.flow-node {
		padding: var(--space-3) var(--space-4);
		background: var(--bg-base);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		text-align: center;
		min-width: 100px;
	}

	.flow-node.clickable {
		cursor: pointer;
		transition: var(--transition-fast);
		color: var(--text-primary);
	}

	.flow-node.clickable:hover {
		border-color: var(--accent);
		color: var(--accent);
		background: rgba(74, 93, 122, 0.05);
	}

	.flow-node.empty {
		border-style: dashed;
		color: var(--text-muted);
		font-style: italic;
	}

	.flow-node.property-node {
		background: var(--accent);
		border-color: var(--accent-hover);
		color: white;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-width: 140px;
	}

	.flow-node.property-node :global(.type-badge) {
		background: rgba(255, 255, 255, 0.2);
		border-color: rgba(255, 255, 255, 0.3);
		color: rgba(255, 255, 255, 0.9);
	}

	.property-label {
		font-family: var(--font-mono);
		font-weight: 500;
	}

	.flow-arrow {
		color: var(--text-muted);
		flex-shrink: 0;
	}

	.property-meta {
		margin-top: var(--space-4);
		padding-top: var(--space-4);
		border-top: 1px solid var(--border);
	}

	.property-uri {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		word-break: break-all;
	}
</style>
