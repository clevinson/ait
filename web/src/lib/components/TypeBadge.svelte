<script lang="ts">
	import type { OwlEntityType } from '$lib/api';

	interface Props {
		type: OwlEntityType;
	}

	let { type }: Props = $props();

	const typeLabels: Record<OwlEntityType, string> = {
		Class: 'Class',
		ObjectProperty: 'Object Property',
		DatatypeProperty: 'Data Property',
		AnnotationProperty: 'Annotation',
		NamedIndividual: 'Individual',
		ConceptScheme: 'Concept Scheme',
		Concept: 'Concept',
		Unknown: 'Entity'
	};

	const typeColors: Record<OwlEntityType, string> = {
		Class: 'class',
		ObjectProperty: 'object-prop',
		DatatypeProperty: 'data-prop',
		AnnotationProperty: 'annotation',
		NamedIndividual: 'individual',
		ConceptScheme: 'concept-scheme',
		Concept: 'concept',
		Unknown: 'unknown'
	};
</script>

<span class="type-badge {typeColors[type]}">
	{typeLabels[type]}
</span>

<style>
	.type-badge {
		display: inline-block;
		padding: var(--space-1) var(--space-2);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-radius: var(--radius-sm);
		border: 1px solid;
	}

	.class {
		background: var(--entity-class-bg);
		color: var(--entity-class-color);
		border-color: var(--entity-class-border);
	}

	.object-prop {
		background: var(--entity-object-prop-bg);
		color: var(--entity-object-prop-color);
		border-color: var(--entity-object-prop-border);
	}

	.data-prop {
		background: var(--entity-data-prop-bg);
		color: var(--entity-data-prop-color);
		border-color: var(--entity-data-prop-border);
	}

	.annotation {
		background: var(--entity-annotation-bg);
		color: var(--entity-annotation-color);
		border-color: var(--entity-annotation-border);
	}

	.individual {
		background: var(--entity-individual-bg);
		color: var(--entity-individual-color);
		border-color: var(--entity-individual-border);
	}

	.concept-scheme {
		background: var(--entity-concept-scheme-bg);
		color: var(--entity-concept-scheme-color);
		border-color: var(--entity-concept-scheme-border);
	}

	.concept {
		background: var(--entity-concept-bg);
		color: var(--entity-concept-color);
		border-color: var(--entity-concept-border);
	}

	.unknown {
		background: var(--bg-muted);
		color: var(--text-tertiary);
		border-color: var(--border);
	}
</style>
