<script lang="ts">
	import { getClassProperties, type PropertyInfo, type EntityRef, type InheritedPropertyGroup } from '$lib/api';

	interface Props {
		ontologyUri: string;
		classUri: string;
		onNavigate: (uri: string, label: string) => void;
	}

	let { ontologyUri, classUri, onNavigate }: Props = $props();

	let domainOf = $state<PropertyInfo[]>([]);
	let inherited = $state<InheritedPropertyGroup[]>([]);
	let rangeOf = $state<PropertyInfo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		if (classUri) {
			loadProperties();
		}
	});

	async function loadProperties() {
		loading = true;
		error = null;

		try {
			const props = await getClassProperties(ontologyUri, classUri);
			domainOf = props.domain_of;
			inherited = props.inherited;
			rangeOf = props.range_of;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load properties';
		} finally {
			loading = false;
		}
	}

	function handleNavigate(item: EntityRef) {
		onNavigate(item.uri, item.label);
	}
</script>

<div class="class-focus">
	{#if loading}
		<div class="status">Loading properties...</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else}
		<!-- Properties this class HAS (domain) -->
		<section>
			<h4 class="section-title">Properties</h4>
			{#if domainOf.length === 0}
				<p class="empty">No properties defined for this class</p>
			{:else}
				<ul class="property-list">
					{#each domainOf as prop (prop.uri)}
						<li>
							<div class="property-row">
								<span class="property-type-indicator" class:object={prop.property_type === 'ObjectProperty'} class:data={prop.property_type === 'DatatypeProperty'}>
									{prop.property_type === 'ObjectProperty' ? '→' : '◇'}
								</span>
								<span class="property-name">{prop.label}</span>
								{#if prop.ranges.length === 1}
									<button
										class="range-link single"
										onclick={() => handleNavigate(prop.ranges[0])}
									>
										{prop.ranges[0].label}
									</button>
								{:else if prop.ranges.length > 1}
									<span class="range-list">
										{#each prop.ranges as range, i (range.uri)}
											<button
												class="range-link"
												onclick={() => handleNavigate(range)}
											>
												{range.label}
											</button>{#if i < prop.ranges.length - 1}<span class="range-separator">|</span>{/if}
										{/each}
									</span>
								{:else}
									<span class="range-empty">unspecified</span>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		<!-- Inherited properties from superclasses -->
		{#if inherited.length > 0}
			{#each inherited as group (group.from_class.uri)}
				<section class="inherited-section">
					<h4 class="section-title inherited-title">
						<span class="inherited-label">Inherited from</span>
						<button
							class="ancestor-link"
							onclick={() => handleNavigate(group.from_class)}
						>
							{group.from_class.label}
						</button>
					</h4>
					<ul class="property-list">
						{#each group.properties as prop (prop.uri)}
							<li>
								<div class="property-row inherited">
									<span class="property-type-indicator" class:object={prop.property_type === 'ObjectProperty'} class:data={prop.property_type === 'DatatypeProperty'}>
										{prop.property_type === 'ObjectProperty' ? '→' : '◇'}
									</span>
									<span class="property-name">{prop.label}</span>
									{#if prop.ranges.length === 1}
										<button
											class="range-link single"
											onclick={() => handleNavigate(prop.ranges[0])}
										>
											{prop.ranges[0].label}
										</button>
									{:else if prop.ranges.length > 1}
										<span class="range-list">
											{#each prop.ranges as range, i (range.uri)}
												<button
													class="range-link"
													onclick={() => handleNavigate(range)}
												>
													{range.label}
												</button>{#if i < prop.ranges.length - 1}<span class="range-separator">|</span>{/if}
											{/each}
										</span>
									{:else}
										<span class="range-empty">unspecified</span>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		{/if}

		<!-- Properties that POINT TO this class (range) -->
		{#if rangeOf.length > 0}
			<section>
				<h4 class="section-title">Referenced By</h4>
				<ul class="property-list incoming">
					{#each rangeOf as prop (prop.uri)}
						<li>
							<div class="property-row reverse">
								{#if prop.domains.length === 1}
									<button
										class="domain-link single"
										onclick={() => handleNavigate(prop.domains[0])}
									>
										{prop.domains[0].label}
									</button>
								{:else if prop.domains.length > 1}
									<span class="domain-list">
										{#each prop.domains as domain, i (domain.uri)}
											<button
												class="domain-link"
												onclick={() => handleNavigate(domain)}
											>
												{domain.label}
											</button>{#if i < prop.domains.length - 1}<span class="domain-separator">|</span>{/if}
										{/each}
									</span>
								{:else}
									<span class="domain-empty">any</span>
								{/if}
								<span class="property-name incoming">.{prop.label}</span>
							</div>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
	{/if}
</div>

<style>
	.class-focus {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.status {
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		font-style: italic;
		padding: var(--space-2);
	}

	.status.error {
		color: var(--color-error);
		font-style: normal;
	}

	.section-title {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-tertiary);
		margin-bottom: var(--space-3);
	}

	.empty {
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		font-style: italic;
	}

	.property-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.property-row {
		display: flex;
		align-items: baseline;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
	}

	.property-row.reverse {
		flex-direction: row;
	}

	.property-type-indicator {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		flex-shrink: 0;
		width: 16px;
		text-align: center;
	}

	.property-type-indicator.object {
		color: var(--entity-object-prop-color);
	}

	.property-type-indicator.data {
		color: var(--entity-data-prop-color);
	}

	.property-name {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--text-primary);
		flex-shrink: 0;
	}

	.property-name.incoming {
		color: var(--text-secondary);
	}

	.range-link,
	.domain-link {
		background: none;
		border: none;
		padding: 0;
		font-family: var(--font-serif);
		font-size: var(--text-sm);
		color: var(--accent);
		cursor: pointer;
		transition: var(--transition-fast);
	}

	.range-link:hover,
	.domain-link:hover {
		color: var(--accent-hover);
		text-decoration: underline;
	}

	.range-link.single,
	.domain-link.single {
		margin-left: auto;
	}

	.range-list,
	.domain-list {
		display: flex;
		align-items: baseline;
		gap: var(--space-1);
		margin-left: auto;
		flex-wrap: wrap;
	}

	.range-separator,
	.domain-separator {
		color: var(--text-muted);
	}

	.range-empty,
	.domain-empty {
		font-size: var(--text-sm);
		color: var(--text-muted);
		font-style: italic;
		margin-left: auto;
	}

	/* Inherited properties styles */
	.inherited-section {
		opacity: 0.85;
	}

	.inherited-title {
		display: flex;
		align-items: baseline;
		gap: var(--space-2);
	}

	.inherited-label {
		color: var(--text-muted);
	}

	.ancestor-link {
		background: none;
		border: none;
		padding: 0;
		font-family: var(--font-serif);
		font-size: var(--text-xs);
		color: var(--accent);
		cursor: pointer;
		transition: var(--transition-fast);
		text-transform: none;
		letter-spacing: normal;
	}

	.ancestor-link:hover {
		color: var(--accent-hover);
		text-decoration: underline;
	}

	.property-row.inherited {
		background: var(--bg-base);
		border-style: dashed;
	}
</style>
