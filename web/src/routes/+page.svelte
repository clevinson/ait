<script lang="ts">
	import OntologyList from '$lib/components/OntologyList.svelte';
	import TabPanel from '$lib/components/TabPanel.svelte';
	import type { OntologyInfo } from '$lib/api';

	let tabPanel: ReturnType<typeof TabPanel>;
	let ontologyList: ReturnType<typeof OntologyList>;

	function handleOntologySelect(ontology: OntologyInfo) {
		tabPanel.openTab(ontology);
	}

	function handleIngest() {
		ontologyList.refresh();
	}
</script>

<svelte:head>
	<title>ait - Archive of Interconnected Terms</title>
</svelte:head>

<div class="app">
	<aside class="sidebar">
		<OntologyList bind:this={ontologyList} onSelect={handleOntologySelect} />
	</aside>
	<main class="content">
		<TabPanel bind:this={tabPanel} onIngest={handleIngest} />
	</main>
</div>

<style>
	.app {
		display: flex;
		height: 100vh;
		width: 100vw;
		overflow: hidden;
	}

	.sidebar {
		width: var(--sidebar-width);
		flex-shrink: 0;
		border-right: 1px solid var(--border);
		background: var(--bg-subtle);
		overflow: hidden;
	}

	.content {
		flex: 1;
		overflow: hidden;
		background: var(--bg-base);
	}
</style>
