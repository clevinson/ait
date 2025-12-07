/**
 * Svelte store for ontology namespace prefixes.
 *
 * This allows IriLink and other components to resolve namespace URIs
 * to short prefixes using the prefixes stored in the meta graph.
 */

import { writable, get } from 'svelte/store';

export type PrefixMap = Record<string, string>;

/**
 * Writable store holding the current ontology's prefix map.
 * Updated by OntologyExplorer when an ontology is loaded.
 */
export const prefixStore = writable<PrefixMap>({});

/**
 * Get prefixed form of a URI if possible.
 * Returns { prefix, localName } or null if no matching prefix.
 */
export function getPrefixedForm(
	prefixes: PrefixMap,
	uri: string
): { prefix: string; localName: string } | null {
	for (const [namespace, prefix] of Object.entries(prefixes)) {
		if (uri.startsWith(namespace)) {
			return {
				prefix,
				localName: uri.slice(namespace.length)
			};
		}
	}
	return null;
}
