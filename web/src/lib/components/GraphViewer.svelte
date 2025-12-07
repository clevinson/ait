<script lang="ts">
	import { onMount } from 'svelte';
	import * as d3 from 'd3';
	import { getOntologyGraph, type GraphNode, type GraphEdge } from '$lib/api';

	interface Props {
		ontologyUri: string;
	}

	let { ontologyUri }: Props = $props();

	let container: HTMLDivElement;
	let loading = $state(true);
	let error = $state<string | null>(null);
	let nodeCount = $state(0);
	let edgeCount = $state(0);

	interface SimNode extends d3.SimulationNodeDatum {
		id: string;
		label: string;
		type: string;
	}

	interface SimLink extends d3.SimulationLinkDatum<SimNode> {
		label: string;
	}

	onMount(() => {
		loadGraph();
	});

	async function loadGraph() {
		loading = true;
		error = null;

		try {
			const data = await getOntologyGraph(ontologyUri);
			nodeCount = data.nodes.length;
			edgeCount = data.edges.length;

			if (data.nodes.length === 0) {
				loading = false;
				return;
			}

			renderGraph(data.nodes, data.edges);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load graph';
		} finally {
			loading = false;
		}
	}

	function renderGraph(nodes: GraphNode[], edges: GraphEdge[]) {
		// Clear existing
		d3.select(container).selectAll('*').remove();

		const width = container.clientWidth;
		const height = container.clientHeight;

		// Create SVG
		const svg = d3
			.select(container)
			.append('svg')
			.attr('width', '100%')
			.attr('height', '100%')
			.attr('viewBox', [0, 0, width, height]);

		// Add zoom behavior
		const g = svg.append('g');
		svg.call(
			d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.1, 4]).on('zoom', (event) => {
				g.attr('transform', event.transform);
			}) as unknown as (selection: d3.Selection<SVGSVGElement, unknown, null, undefined>) => void
		);

		// Prepare data
		const simNodes: SimNode[] = nodes.map((n) => ({ ...n }));
		const nodeById = new Map(simNodes.map((n) => [n.id, n]));

		const simLinks: SimLink[] = edges
			.filter((e) => nodeById.has(e.source) && nodeById.has(e.target))
			.map((e) => ({
				source: e.source,
				target: e.target,
				label: e.label
			}));

		// Create simulation
		const simulation = d3
			.forceSimulation(simNodes)
			.force(
				'link',
				d3
					.forceLink<SimNode, SimLink>(simLinks)
					.id((d) => d.id)
					.distance(80)
			)
			.force('charge', d3.forceManyBody().strength(-200))
			.force('center', d3.forceCenter(width / 2, height / 2))
			.force('collision', d3.forceCollide().radius(30));

		// Arrow marker
		svg
			.append('defs')
			.append('marker')
			.attr('id', 'arrowhead')
			.attr('viewBox', '-0 -5 10 10')
			.attr('refX', 20)
			.attr('refY', 0)
			.attr('orient', 'auto')
			.attr('markerWidth', 6)
			.attr('markerHeight', 6)
			.append('path')
			.attr('d', 'M 0,-5 L 10 ,0 L 0,5')
			.attr('fill', '#b3aca3');

		// Links
		const link = g
			.append('g')
			.attr('class', 'links')
			.selectAll('line')
			.data(simLinks)
			.join('line')
			.attr('stroke', '#b3aca3')
			.attr('stroke-width', 1)
			.attr('marker-end', 'url(#arrowhead)');

		// Nodes
		const node = g
			.append('g')
			.attr('class', 'nodes')
			.selectAll<SVGGElement, SimNode>('g')
			.data(simNodes)
			.join('g')
			.call(
				d3
					.drag<SVGGElement, SimNode>()
					.on('start', (event, d) => {
						if (!event.active) simulation.alphaTarget(0.3).restart();
						d.fx = d.x;
						d.fy = d.y;
					})
					.on('drag', (event, d) => {
						d.fx = event.x;
						d.fy = event.y;
					})
					.on('end', (event, d) => {
						if (!event.active) simulation.alphaTarget(0);
						d.fx = null;
						d.fy = null;
					}) as unknown as (
					selection: d3.Selection<SVGGElement, SimNode, SVGGElement, unknown>
				) => void
			);

		// Node circles
		node
			.append('circle')
			.attr('r', 6)
			.attr('fill', '#4a5d7a')
			.attr('stroke', '#3a4d6a')
			.attr('stroke-width', 1.5);

		// Node labels
		node
			.append('text')
			.text((d) => d.label)
			.attr('x', 10)
			.attr('y', 4)
			.attr('font-size', '12px')
			.attr('font-family', "'Iowan Old Style', 'Palatino Linotype', serif")
			.attr('fill', '#2c2825');

		// Hover effects
		node
			.on('mouseenter', function () {
				d3.select(this).select('circle').attr('fill', '#5a6d8a');
			})
			.on('mouseleave', function () {
				d3.select(this).select('circle').attr('fill', '#4a5d7a');
			});

		// Tick
		simulation.on('tick', () => {
			link
				.attr('x1', (d) => (d.source as SimNode).x!)
				.attr('y1', (d) => (d.source as SimNode).y!)
				.attr('x2', (d) => (d.target as SimNode).x!)
				.attr('y2', (d) => (d.target as SimNode).y!);

			node.attr('transform', (d) => `translate(${d.x},${d.y})`);
		});
	}
</script>

<div class="graph-viewer">
	{#if loading}
		<div class="status">Loading graph...</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else if nodeCount === 0}
		<div class="status">No classes found in this ontology</div>
	{:else}
		<div class="info">{nodeCount} nodes, {edgeCount} edges</div>
	{/if}
	<div class="canvas" bind:this={container}></div>
</div>

<style>
	.graph-viewer {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--bg-base);
		position: relative;
	}

	.canvas {
		flex: 1;
		overflow: hidden;
	}

	.status {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		font-style: italic;
	}

	.status.error {
		color: var(--color-error);
		font-style: normal;
	}

	.info {
		position: absolute;
		top: var(--space-3);
		right: var(--space-3);
		padding: var(--space-1) var(--space-2);
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		z-index: 10;
	}
</style>
