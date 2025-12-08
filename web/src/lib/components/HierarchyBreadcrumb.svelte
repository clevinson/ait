<script lang="ts">
	import { getDisplayName, type EntityRef, type DisplayNameMode } from '$lib/api';

	interface Props {
		currentLabel: string;
		superclasses: EntityRef[];
		onNavigate: (uri: string, label: string) => void;
		displayNameMode?: DisplayNameMode;
	}

	let { currentLabel, superclasses, onNavigate, displayNameMode = 'label' }: Props = $props();

	// Reverse superclasses to show from root to current
	const path = $derived([...superclasses].reverse());
</script>

<nav class="hierarchy-breadcrumb" aria-label="Class hierarchy">
	{#each path as ancestor, i (ancestor.uri)}
		{@const name = getDisplayName(ancestor, displayNameMode)}
		<button class="breadcrumb-item" onclick={() => onNavigate(ancestor.uri, name)}>
			{name}
		</button>
		<span class="separator">›</span>
	{/each}
	<span class="current">{currentLabel}</span>
</nav>

<style>
	.hierarchy-breadcrumb {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--space-1);
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		line-height: var(--leading-tight);
	}

	.breadcrumb-item {
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		font: inherit;
		color: var(--text-secondary);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.breadcrumb-item:hover {
		color: var(--accent);
		text-decoration: underline;
	}

	.separator {
		color: var(--text-muted);
		user-select: none;
	}

	.current {
		color: var(--text-primary);
		font-weight: 500;
	}
</style>
