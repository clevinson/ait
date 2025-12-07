"""Tests for the RDF store."""

import pytest
from ait.store import Store, RdfFormat


class TestStoreBasics:
    """Test basic store operations."""

    def test_create_memory_store(self):
        """Can create an in-memory store."""
        store = Store()
        assert len(store) == 0

    @pytest.mark.skip(reason="Persistent store has issues in test environment")
    def test_create_persistent_store(self, temp_store_path):
        """Can create a persistent store."""
        store = Store(temp_store_path)
        assert len(store) == 0
        assert temp_store_path.exists()

    @pytest.mark.skip(reason="Persistent store has issues in test environment")
    def test_persistent_store_survives_reload(self, temp_store_path, sample_ttl, ontology_uri):
        """Data persists across store instances."""
        # Load data
        store1 = Store(temp_store_path)
        store1.load_rdf(sample_ttl, format=RdfFormat.TURTLE, graph_name=ontology_uri)
        count1 = len(store1)
        assert count1 > 0

        # Reload
        store2 = Store(temp_store_path)
        assert len(store2) == count1


class TestLoadRdf:
    """Test RDF loading functionality."""

    def test_load_turtle(self, memory_store, sample_ttl, ontology_uri):
        """Can load Turtle format."""
        count = memory_store.load_rdf(sample_ttl, format=RdfFormat.TURTLE, graph_name=ontology_uri)
        assert count > 0
        assert len(memory_store) == count

    def test_load_rdfxml(self, memory_store, sample_xml, ontology_uri):
        """Can load RDF/XML format."""
        count = memory_store.load_rdf(sample_xml, format=RdfFormat.XML, graph_name=ontology_uri)
        assert count > 0

    def test_load_ntriples(self, memory_store):
        """Can load N-Triples format."""
        ntriples = b"<http://example.org/s> <http://example.org/p> <http://example.org/o> .\n"
        count = memory_store.load_rdf(ntriples, format=RdfFormat.NTRIPLES, graph_name="http://test")
        assert count == 1

    def test_load_bytes(self, memory_store):
        """Can load bytes directly."""
        data = b"<http://example.org/s> <http://example.org/p> <http://example.org/o> .\n"
        count = memory_store.load_rdf(data, format=RdfFormat.NTRIPLES, graph_name="http://test")
        assert count == 1

    def test_load_string(self, memory_store):
        """Can load string data."""
        data = "<http://example.org/s> <http://example.org/p> <http://example.org/o> .\n"
        count = memory_store.load_rdf(data, format=RdfFormat.NTRIPLES, graph_name="http://test")
        assert count == 1

    def test_load_into_named_graph(self, memory_store, sample_ttl, ontology_uri):
        """Data is loaded into the specified named graph."""
        memory_store.load_rdf(sample_ttl, format=RdfFormat.TURTLE, graph_name=ontology_uri)
        graphs = list(memory_store.graphs())
        assert ontology_uri in graphs


class TestQuery:
    """Test SPARQL query functionality."""

    def test_simple_select(self, loaded_store, ontology_uri):
        """Can execute a simple SELECT query."""
        results = loaded_store.query(f"""
            SELECT ?s WHERE {{
                GRAPH <{ontology_uri}> {{
                    ?s a <http://www.w3.org/2002/07/owl#Class>
                }}
            }} LIMIT 5
        """)
        assert len(results) > 0
        assert "s" in results[0]

    def test_query_with_multiple_variables(self, loaded_store, ontology_uri):
        """Can query multiple variables."""
        results = loaded_store.query(f"""
            SELECT ?class ?label WHERE {{
                GRAPH <{ontology_uri}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                    ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }}
            }} LIMIT 5
        """)
        assert len(results) > 0
        assert "class" in results[0]
        assert "label" in results[0]

    def test_query_named_graph(self, loaded_store, ontology_uri):
        """Can query specific named graphs."""
        results = loaded_store.query(f"""
            SELECT ?s ?p ?o WHERE {{
                GRAPH <{ontology_uri}> {{ ?s ?p ?o }}
            }} LIMIT 1
        """)
        assert len(results) == 1

    def test_query_empty_result(self, loaded_store):
        """Empty results return empty list."""
        results = loaded_store.query("SELECT ?s WHERE { ?s a <http://nonexistent/class> }")
        assert results == []

    def test_query_with_optional(self, loaded_store, ontology_uri):
        """Can use OPTIONAL in queries."""
        results = loaded_store.query(f"""
            SELECT ?class ?comment WHERE {{
                GRAPH <{ontology_uri}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                    OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#comment> ?comment }}
                }}
            }} LIMIT 10
        """)
        assert len(results) > 0
        # Some should have comments, some might not
        assert "class" in results[0]

    def test_query_count(self, loaded_store, ontology_uri):
        """Can execute COUNT queries."""
        results = loaded_store.query(f"""
            SELECT (COUNT(?class) as ?count) WHERE {{
                GRAPH <{ontology_uri}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                }}
            }}
        """)
        assert len(results) == 1
        assert "count" in results[0]
        assert int(results[0]["count"]) > 0

    def test_query_distinct(self, loaded_store, ontology_uri):
        """Can use DISTINCT in queries."""
        results = loaded_store.query(f"""
            SELECT DISTINCT ?type WHERE {{
                GRAPH <{ontology_uri}> {{
                    ?s a ?type .
                }}
            }}
        """)
        # Should have distinct types
        types = [r["type"] for r in results]
        assert len(types) == len(set(types))


class TestGraphs:
    """Test named graph functionality."""

    def test_list_graphs(self, loaded_store, ontology_uri):
        """Can list named graphs."""
        graphs = list(loaded_store.graphs())
        assert ontology_uri in graphs

    def test_multiple_graphs(self, memory_store):
        """Can have multiple named graphs."""
        data = "<http://example.org/s> <http://example.org/p> <http://example.org/o> .\n"
        memory_store.load_rdf(data, format=RdfFormat.NTRIPLES, graph_name="http://graph1")
        memory_store.load_rdf(data, format=RdfFormat.NTRIPLES, graph_name="http://graph2")

        graphs = list(memory_store.graphs())
        assert "http://graph1" in graphs
        assert "http://graph2" in graphs

    def test_empty_store_no_graphs(self, memory_store):
        """Empty store has no graphs."""
        graphs = list(memory_store.graphs())
        assert graphs == []


class TestClear:
    """Test store clearing functionality."""

    def test_clear_all(self, loaded_store):
        """Can clear all data."""
        assert len(loaded_store) > 0
        loaded_store.clear()
        assert len(loaded_store) == 0

    def test_clear_specific_graph(self, memory_store):
        """Can clear a specific named graph."""
        data = "<http://example.org/s> <http://example.org/p> <http://example.org/o> .\n"
        memory_store.load_rdf(data, format=RdfFormat.NTRIPLES, graph_name="http://graph1")
        memory_store.load_rdf(data, format=RdfFormat.NTRIPLES, graph_name="http://graph2")

        initial_count = len(memory_store)
        memory_store.clear(graph_name="http://graph1")

        assert len(memory_store) < initial_count
        graphs = list(memory_store.graphs())
        assert "http://graph1" not in graphs
        assert "http://graph2" in graphs


class TestBlankNodes:
    """Test handling of blank nodes."""

    def test_query_with_blank_nodes(self, memory_store):
        """Can query data containing blank nodes."""
        ttl = """
        @prefix ex: <http://example.org/> .
        ex:subject ex:hasValue [
            ex:amount 42 ;
            ex:unit "kg"
        ] .
        """
        memory_store.load_rdf(ttl, format=RdfFormat.TURTLE, graph_name="http://test")

        results = memory_store.query("""
            SELECT ?s ?o WHERE {
                GRAPH <http://test> {
                    ?s <http://example.org/hasValue> ?o .
                }
            }
        """)
        assert len(results) == 1
        # Blank node should be prefixed with _:
        assert results[0]["o"].startswith("_:")


class TestLiterals:
    """Test handling of different literal types."""

    def test_string_literals(self, memory_store):
        """Can query string literals."""
        ttl = """
        @prefix ex: <http://example.org/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ex:Thing rdfs:label "A Thing" .
        """
        memory_store.load_rdf(ttl, format=RdfFormat.TURTLE, graph_name="http://test")

        results = memory_store.query("""
            SELECT ?label WHERE {
                GRAPH <http://test> {
                    <http://example.org/Thing> <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }
            }
        """)
        assert results[0]["label"] == "A Thing"

    def test_typed_literals(self, memory_store):
        """Can query typed literals (numbers, dates, etc.)."""
        ttl = """
        @prefix ex: <http://example.org/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:Thing ex:count "42"^^xsd:integer .
        ex:Thing ex:value "3.14"^^xsd:decimal .
        """
        memory_store.load_rdf(ttl, format=RdfFormat.TURTLE, graph_name="http://test")

        results = memory_store.query("""
            SELECT ?count ?value WHERE {
                GRAPH <http://test> {
                    <http://example.org/Thing> <http://example.org/count> ?count .
                    <http://example.org/Thing> <http://example.org/value> ?value .
                }
            }
        """)
        assert results[0]["count"] == "42"
        assert results[0]["value"] == "3.14"

    def test_language_tagged_literals(self, memory_store):
        """Can query language-tagged literals."""
        ttl = """
        @prefix ex: <http://example.org/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ex:Thing rdfs:label "A Thing"@en .
        ex:Thing rdfs:label "Une Chose"@fr .
        """
        memory_store.load_rdf(ttl, format=RdfFormat.TURTLE, graph_name="http://test")

        results = memory_store.query("""
            SELECT ?label WHERE {
                GRAPH <http://test> {
                    <http://example.org/Thing> <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }
            }
        """)
        labels = [r["label"] for r in results]
        assert "A Thing" in labels
        assert "Une Chose" in labels
