<script lang="ts">
	import { prefixStore, getPrefixedForm } from '$lib/prefixContext';

	interface Props {
		uri: string;
		showFull?: boolean;
	}

	let { uri, showFull = false }: Props = $props();

	// Subscribe to prefix store (set by OntologyExplorer)
	const prefixes = $derived($prefixStore);

	// Check if URI looks like a valid HTTP(S) URL
	const isHttpUrl = $derived(uri.startsWith('http://') || uri.startsWith('https://'));

	const prefixed = $derived(getPrefixedForm(prefixes, uri));
</script>

<span class="iri-link" title={uri}>
	{#if showFull}
		<code class="full-uri">{uri}</code>
	{:else if isHttpUrl}
		<a href={uri} target="_blank" rel="noopener noreferrer" class="prefixed-link">
			{#if prefixed}
				<span class="prefix">{prefixed.prefix}</span>{#if prefixed.localName}<span class="local-name">:{prefixed.localName}</span>{/if}
			{:else}
				<span class="full-url">{uri}</span>
			{/if}
			<svg
				class="link-icon"
				width="10"
				height="10"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
				<polyline points="15 3 21 3 21 9" />
				<line x1="10" y1="14" x2="21" y2="3" />
			</svg>
		</a>
	{:else}
		<code class="full-uri">{uri}</code>
	{/if}
</span>

<style>
	.iri-link {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
	}

	.full-uri,
	.full-url {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		word-break: break-all;
	}

	.prefixed-link {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--accent-muted);
		text-decoration: none;
		transition: var(--transition-fast);
	}

	.prefixed-link:hover {
		color: var(--accent);
	}

	.prefixed-link:hover .prefix {
		color: var(--accent);
	}

	.prefix {
		color: var(--text-tertiary);
		transition: var(--transition-fast);
	}

	.prefixed-link .local-name {
		color: inherit;
	}

	.link-icon {
		opacity: 0.5;
		flex-shrink: 0;
		margin-left: 2px;
	}

	.prefixed-link:hover .link-icon {
		opacity: 1;
	}
</style>
