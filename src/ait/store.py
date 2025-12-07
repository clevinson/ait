"""Local RDF store using pyoxigraph."""

from enum import StrEnum
from pathlib import Path
from typing import Iterator

import pyoxigraph as ox
from rdflib import Graph


class RdfFormat(StrEnum):
    """Supported RDF serialization formats."""

    TURTLE = "turtle"
    XML = "xml"
    NTRIPLES = "ntriples"
    NQUADS = "nquads"

    @property
    def mime_type(self) -> str:
        """Return the MIME type for this format."""
        mime_types = {
            RdfFormat.TURTLE: "text/turtle",
            RdfFormat.XML: "application/rdf+xml",
            RdfFormat.NTRIPLES: "application/n-triples",
            RdfFormat.NQUADS: "application/n-quads",
        }
        return mime_types[self]


class Store:
    """A local RDF store backed by pyoxigraph."""

    def __init__(self, path: Path | None = None):
        """Initialize the store.

        Args:
            path: Directory for persistent storage. If None, uses in-memory store.
        """
        if path:
            path.mkdir(parents=True, exist_ok=True)
            self._store = ox.Store(str(path))
        else:
            self._store = ox.Store()

    def load_rdf(
        self,
        data: str | bytes,
        format: RdfFormat = RdfFormat.TURTLE,
        graph_name: str | None = None,
    ) -> int:
        """Load RDF data into the store.

        Args:
            data: RDF data as string or bytes.
            format: RDF serialization format.
            graph_name: Optional named graph to load into.

        Returns:
            Number of triples loaded.
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        graph = ox.NamedNode(graph_name) if graph_name else ox.DefaultGraph()

        before = len(self._store)
        self._store.load(data, format.mime_type, to_graph=graph)
        return len(self._store) - before

    def query(self, sparql: str) -> list[dict[str, str]]:
        """Execute a SPARQL SELECT query.

        Args:
            sparql: SPARQL query string.

        Returns:
            List of result bindings as dictionaries.
        """
        results = self._store.query(sparql)
        variables = [v.value for v in results.variables]
        rows: list[dict[str, str]] = []
        for solution in results:
            row: dict[str, str] = {}
            for var_name in variables:
                value = solution[var_name]
                if value is not None:
                    if isinstance(value, ox.NamedNode):
                        row[var_name] = str(value.value)
                    elif isinstance(value, ox.Literal):
                        row[var_name] = str(value.value)
                    elif isinstance(value, ox.BlankNode):
                        row[var_name] = f"_:{value.value}"
            rows.append(row)
        return rows

    def construct(self, sparql: str) -> Graph:
        """Execute a SPARQL CONSTRUCT query.

        Args:
            sparql: SPARQL CONSTRUCT query string.

        Returns:
            rdflib Graph with constructed triples.
        """
        results = self._store.query(sparql)
        g = Graph()
        for triple in results:
            g.add(self._ox_triple_to_rdflib(triple))
        return g

    def _ox_triple_to_rdflib(self, triple: ox.Triple):
        """Convert an oxigraph triple to rdflib terms."""
        from rdflib import BNode, Literal, URIRef

        def convert(term: ox.NamedNode | ox.BlankNode | ox.Literal):
            if isinstance(term, ox.NamedNode):
                return URIRef(term.value)
            elif isinstance(term, ox.BlankNode):
                return BNode(term.value)
            elif isinstance(term, ox.Literal):
                return Literal(
                    term.value,
                    lang=term.language,
                    datatype=URIRef(term.datatype.value) if term.datatype else None,
                )
            return term

        return (convert(triple.subject), convert(triple.predicate), convert(triple.object))

    def graphs(self) -> Iterator[str]:
        """List all named graphs in the store."""
        sparql = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"
        for row in self.query(sparql):
            if "g" in row:
                yield row["g"]

    def __len__(self) -> int:
        return len(self._store)

    def update(self, sparql: str) -> None:
        """Execute a SPARQL UPDATE query (INSERT, DELETE, etc.).

        Args:
            sparql: SPARQL UPDATE query string.
        """
        self._store.update(sparql)

    def clear(self, graph_name: str | None = None) -> None:
        """Clear all triples, optionally from a specific graph."""
        if graph_name:
            self._store.update(f"CLEAR GRAPH <{graph_name}>")
        else:
            self._store.update("CLEAR ALL")
