<script lang="ts">
	import type { CodeListInfo } from '$lib/api';
	import IriLink from './IriLink.svelte';

	interface Props {
		codeList: CodeListInfo;
		onNavigate?: (uri: string, label: string) => void;
	}

	let { codeList, onNavigate }: Props = $props();

	// Pattern display names
	const patternLabels: Record<string, string> = {
		skos_scheme: 'SKOS Concept Scheme',
		skos_collection: 'SKOS Collection',
		owl_oneof: 'OWL Enumeration',
		owl_equivalent_oneof: 'OWL Enumeration'
	};

	// Check if any members have notation
	const hasNotation = $derived(codeList.members.some(m => m.notation));

	function handleMemberClick(uri: string, label: string) {
		if (onNavigate) {
			onNavigate(uri, label);
		}
	}
</script>

<section class="codelist-view">
	<header class="codelist-header">
		<span class="pattern-badge">{patternLabels[codeList.pattern] || codeList.pattern}</span>
		<span class="member-count">{codeList.member_count} members</span>
	</header>

	{#if codeList.members.length === 0}
		<p class="empty-state">No members found</p>
	{:else}
		<div class="table-wrapper">
			<table class="member-table">
				<thead>
					<tr>
						{#if hasNotation}
							<th class="col-code">Code</th>
						{/if}
						<th class="col-label">Label</th>
						<th class="col-iri">IRI</th>
					</tr>
				</thead>
				<tbody>
					{#each codeList.members as member}
						<tr class="member-row">
							{#if hasNotation}
								<td class="col-code">
									{#if member.notation}
										<code class="notation">{member.notation}</code>
									{:else}
										<span class="no-value">—</span>
									{/if}
								</td>
							{/if}
							<td class="col-label">
								<button
									class="member-link"
									onclick={() => handleMemberClick(member.uri, member.label)}
									title={member.uri}
								>
									{member.label}
								</button>
								{#if member.description}
									<p class="description">{member.description}</p>
								{/if}
							</td>
							<td class="col-iri">
								<IriLink uri={member.uri} />
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<style>
	.codelist-view {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.codelist-header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		background: var(--bg-surface);
		border-radius: var(--radius-md);
		border: 1px solid var(--border);
	}

	.pattern-badge {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		padding: var(--space-1) var(--space-2);
		background: rgba(107, 114, 128, 0.15);
		color: var(--text-secondary);
		border-radius: var(--radius-sm);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.member-count {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--text-tertiary);
	}

	.empty-state {
		padding: var(--space-4);
		color: var(--text-tertiary);
		font-style: italic;
		text-align: center;
	}

	.table-wrapper {
		overflow-x: auto;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
	}

	.member-table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--text-sm);
	}

	.member-table thead {
		background: var(--bg-muted);
		position: sticky;
		top: 0;
	}

	.member-table th {
		padding: var(--space-2) var(--space-3);
		text-align: left;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-secondary);
		border-bottom: 1px solid var(--border);
	}

	.member-table td {
		padding: var(--space-2) var(--space-3);
		border-bottom: 1px solid var(--border);
		vertical-align: top;
	}

	.member-row:last-child td {
		border-bottom: none;
	}

	.member-row:hover {
		background: var(--bg-subtle);
	}

	.col-code {
		white-space: nowrap;
		width: 1%;
	}

	.col-label {
		min-width: 200px;
	}

	.col-iri {
		white-space: nowrap;
		width: 1%;
	}

	.notation {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		padding: 2px 6px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-primary);
	}

	.member-link {
		background: none;
		border: none;
		padding: 0;
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-primary);
		cursor: pointer;
		text-align: left;
		transition: var(--transition-fast);
	}

	.member-link:hover {
		color: var(--accent);
	}

	.description {
		margin: var(--space-1) 0 0;
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--text-secondary);
		line-height: var(--leading-relaxed);
	}

	.no-value {
		color: var(--text-muted);
	}
</style>
