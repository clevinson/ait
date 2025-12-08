<script lang="ts">
	import { getClassHierarchy, listCodeLists, getDisplayName, type HierarchyNode, type CodeListSummary, type DisplayNameMode } from '$lib/api';
	import { onMount } from 'svelte';

	interface Props {
		ontologyUri: string;
		selectedClassUri?: string | null;
		onSelect: (classUri: string, label: string) => void;
		displayNameMode?: DisplayNameMode;
	}

	let { ontologyUri, selectedClassUri = null, onSelect, displayNameMode = 'label' }: Props = $props();

	interface TreeNode {
		uri: string;
		label: string;
		children: TreeNode[];
		expanded: boolean;
	}

	let allNodes = $state<HierarchyNode[]>([]);
	let roots = $state<TreeNode[]>([]);
	let codeLists = $state<CodeListSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showExternal = $state(false);
	let externalCount = $state(0);

	onMount(async () => {
		await loadData();
	});

	async function loadData() {
		loading = true;
		error = null;

		try {
			// Load hierarchy and code lists in parallel
			const [nodes, lists] = await Promise.all([
				getClassHierarchy(ontologyUri),
				listCodeLists(ontologyUri)
			]);
			allNodes = nodes;
			externalCount = nodes.filter((n) => n.is_external).length;
			roots = buildTree(showExternal ? nodes : nodes.filter((n) => !n.is_external));
			codeLists = lists;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load';
		} finally {
			loading = false;
		}
	}

	// Rebuild tree when showExternal changes
	$effect(() => {
		if (allNodes.length > 0) {
			roots = buildTree(showExternal ? allNodes : allNodes.filter((n) => !n.is_external));
		}
	});

	function buildTree(nodes: HierarchyNode[]): TreeNode[] {
		// Build lookup maps
		const nodeMap = new Map<string, HierarchyNode>();
		const childrenMap = new Map<string, string[]>();
		const allUris = new Set(nodes.map((n) => n.uri));

		for (const node of nodes) {
			nodeMap.set(node.uri, node);

			// Build parent -> children mapping
			for (const parentUri of node.parent_uris) {
				if (!childrenMap.has(parentUri)) {
					childrenMap.set(parentUri, []);
				}
				childrenMap.get(parentUri)!.push(node.uri);
			}
		}

		// Find root nodes: those with no parents in our set
		const rootUris: string[] = [];
		for (const node of nodes) {
			const hasParentInSet = node.parent_uris.some((p) => allUris.has(p));
			if (!hasParentInSet) {
				rootUris.push(node.uri);
			}
		}

		// Build tree recursively
		function buildNode(uri: string, ancestorPath: Set<string>): TreeNode | null {
			const node = nodeMap.get(uri);
			if (!node) return null;

			// Prevent cycles
			if (ancestorPath.has(uri)) return null;

			const newPath = new Set(ancestorPath);
			newPath.add(uri);

			const childUris = childrenMap.get(uri) || [];
			const children = childUris
				.map((c) => buildNode(c, newPath))
				.filter((n): n is TreeNode => n !== null)
				.sort((a, b) => a.label.localeCompare(b.label));

			return {
				uri,
				label: getDisplayName(node, displayNameMode),
				children,
				expanded: false
			};
		}

		const treeRoots = rootUris
			.map((uri) => buildNode(uri, new Set()))
			.filter((n): n is TreeNode => n !== null)
			.sort((a, b) => a.label.localeCompare(b.label));

		return treeRoots;
	}

	function toggleExpand(node: TreeNode) {
		node.expanded = !node.expanded;
	}

	function handleSelect(uri: string, label: string) {
		onSelect(uri, label);
	}
</script>

<div class="sidebar-content">
	{#if loading}
		<div class="status">Loading...</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else}
		<!-- Class Hierarchy Section -->
		<section>
			<h3 class="section-header">Classes</h3>
			{#if roots.length === 0}
				<div class="status">No classes found</div>
			{:else}
				<ul class="tree-root">
					{#each roots as node (node.uri)}
						{@render treeNode(node, 0)}
					{/each}
				</ul>
			{/if}
		</section>

		<!-- Concept Schemes Section (SKOS) -->
		{#if codeLists.length > 0}
			<section class="codelists-section">
				<h3 class="section-header">Concept Schemes</h3>
				<ul class="codelist-list">
					{#each codeLists as codeList (codeList.uri)}
						{@const name = getDisplayName(codeList, displayNameMode)}
						<li>
							<button
								class="codelist-item"
								class:selected={selectedClassUri === codeList.uri}
								onclick={() => handleSelect(codeList.uri, name)}
								title={codeList.uri}
							>
								<span class="codelist-label">{name}</span>
								<span class="codelist-count">{codeList.member_count}</span>
							</button>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- External Classes Toggle -->
		{#if externalCount > 0}
			<div class="external-toggle">
				<label class="toggle-label">
					<input type="checkbox" bind:checked={showExternal} />
					<span>Show external classes ({externalCount})</span>
				</label>
			</div>
		{/if}
	{/if}
</div>

{#snippet treeNode(node: TreeNode, depth: number)}
	<li class="tree-item">
		<div
			class="node-row"
			class:selected={selectedClassUri === node.uri}
		>
			{#if node.children.length > 0}
				<button
					class="toggle"
					onclick={() => toggleExpand(node)}
					aria-label={node.expanded ? 'Collapse' : 'Expand'}
				>
					{node.expanded ? '−' : '+'}
				</button>
			{:else}
				<span class="toggle-spacer"></span>
			{/if}
			<button class="node-label" onclick={() => handleSelect(node.uri, node.label)}>
				{node.label}
			</button>
		</div>
		{#if node.expanded && node.children.length > 0}
			<ul class="tree-children">
				{#each node.children as child (child.uri)}
					{@render treeNode(child, depth + 1)}
				{/each}
			</ul>
		{/if}
	</li>
{/snippet}

<style>
	.sidebar-content {
		display: flex;
		flex-direction: column;
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

	/* Section headers */
	.section-header {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-tertiary);
		padding: var(--space-3) var(--space-3) var(--space-2);
		margin: 0;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface);
	}

	.tree-root,
	.tree-children {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.tree-root {
		padding: var(--space-2) 0;
	}

	.tree-children {
		margin-left: var(--space-4);
	}

	.tree-item {
		margin: 0;
	}

	.node-row {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-3);
		transition: var(--transition-fast);
	}

	.node-row:hover {
		background: var(--bg-muted);
	}

	.node-row.selected {
		background: var(--bg-muted);
	}

	.node-row.selected .node-label {
		color: var(--accent);
	}

	.toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		padding: 0;
		background: none;
		border: none;
		color: var(--text-tertiary);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		cursor: pointer;
		flex-shrink: 0;
	}

	.toggle:hover {
		color: var(--text-primary);
	}

	.toggle-spacer {
		width: 16px;
		flex-shrink: 0;
	}

	.node-label {
		flex: 1;
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		text-align: left;
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-primary);
		cursor: pointer;
		line-height: var(--leading-tight);
		word-break: break-word;
	}

	.node-label:hover {
		color: var(--accent);
	}

	/* Code Lists section */
	.codelists-section {
		border-top: 1px solid var(--border);
		flex-shrink: 0;
	}

	.codelist-list {
		list-style: none;
		margin: 0;
		padding: var(--space-2) 0;
	}

	.codelist-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: var(--space-2) var(--space-3);
		background: none;
		border: none;
		text-align: left;
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.codelist-item:hover {
		background: var(--bg-muted);
	}

	.codelist-item.selected {
		background: var(--bg-muted);
	}

	.codelist-item.selected .codelist-label {
		color: var(--accent);
	}

	.codelist-label {
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-primary);
	}

	.codelist-count {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		background: var(--bg-muted);
		padding: 1px 6px;
		border-radius: var(--radius-sm);
	}

	/* External classes toggle */
	.external-toggle {
		padding: var(--space-3);
		border-top: 1px solid var(--border);
		background: var(--bg-subtle);
	}

	.toggle-label {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		cursor: pointer;
	}

	.toggle-label:hover {
		color: var(--text-secondary);
	}

	.toggle-label input[type='checkbox'] {
		margin: 0;
		cursor: pointer;
	}
</style>
