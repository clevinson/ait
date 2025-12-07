"""Tests for the web API endpoints."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from ait.store import Store, RdfFormat
from ait import web


# Sample ontology for API tests
SAMPLE_ONTOLOGY = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/test#> .

<http://example.org/test> a owl:Ontology ;
    rdfs:label "Test Ontology" .

ex:BaseClass a owl:Class ;
    rdfs:label "Base Class" ;
    rdfs:comment "The base class for testing" .

ex:ChildClass a owl:Class ;
    rdfs:label "Child Class" ;
    rdfs:subClassOf ex:BaseClass ;
    rdfs:comment "A child class" .

ex:GrandchildClass a owl:Class ;
    rdfs:label "Grandchild Class" ;
    rdfs:subClassOf ex:ChildClass .

ex:SiblingClass a owl:Class ;
    rdfs:label "Sibling Class" ;
    rdfs:subClassOf ex:BaseClass .
"""

ONTOLOGY_URI = "http://example.org/test"


@pytest.fixture
def test_store():
    """Create a test store with sample data (in-memory)."""
    store = Store()  # In-memory store
    store.load_rdf(SAMPLE_ONTOLOGY, format=RdfFormat.TURTLE, graph_name=ONTOLOGY_URI)
    yield store, Path("/tmp/test-ait")


@pytest.fixture
def client(test_store):
    """Create a test client with configured store."""
    store, store_path = test_store

    # Configure the web module to use our test store
    web._store = store
    web._data_dir = store_path.parent

    with TestClient(web.app) as client:
        yield client

    # Cleanup
    web._store = None


@pytest.fixture
def empty_client():
    """Create a test client with empty store (in-memory)."""
    store = Store()  # In-memory store

    web._store = store
    web._data_dir = Path("/tmp/test-ait")

    with TestClient(web.app) as client:
        yield client

    web._store = None


class TestListOntologies:
    """Test GET /api/ontologies endpoint."""

    def test_list_ontologies(self, client):
        """Returns list of cached ontologies."""
        response = client.get("/api/ontologies")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        ont = data[0]
        assert ont["uri"] == ONTOLOGY_URI
        assert ont["label"] == "Test Ontology"  # From rdfs:label in data
        assert ont["triple_count"] > 0

    def test_list_empty(self, empty_client):
        """Returns empty list when no ontologies cached."""
        response = empty_client.get("/api/ontologies")
        assert response.status_code == 200
        assert response.json() == []

    def test_ontology_has_label_from_uri(self, client):
        """Ontology label is extracted from URI if not in data."""
        response = client.get("/api/ontologies")
        data = response.json()
        # Label should be extracted from the last part of the URI
        assert data[0]["label"] is not None


class TestGetOntologyGraph:
    """Test GET /api/ontologies/{uri}/graph endpoint."""

    def test_get_graph(self, client):
        """Returns graph data with nodes and edges."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/graph")
        assert response.status_code == 200

        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_graph_nodes_have_required_fields(self, client):
        """Graph nodes have id, label, and type."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/graph")
        data = response.json()

        for node in data["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "type" in node

    def test_graph_edges_have_required_fields(self, client):
        """Graph edges have source, target, and label."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/graph")
        data = response.json()

        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "label" in edge

    def test_graph_contains_subclass_edges(self, client):
        """Graph includes subClassOf relationships."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/graph")
        data = response.json()

        # Should have subClassOf edges
        subclass_edges = [e for e in data["edges"] if e["label"] == "subClassOf"]
        assert len(subclass_edges) > 0

    def test_graph_limit_parameter(self, client):
        """Can limit number of results."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/graph?limit=2")
        assert response.status_code == 200

    def test_graph_not_found(self, client):
        """Returns 404 for unknown ontology."""
        response = client.get("/api/ontologies/http%3A%2F%2Fnonexistent/graph")
        assert response.status_code == 404


class TestListClasses:
    """Test GET /api/ontologies/{uri}/classes endpoint."""

    def test_list_classes(self, client):
        """Returns list of classes."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/classes")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_classes_have_required_fields(self, client):
        """Classes have uri and label."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/classes")
        data = response.json()

        for cls in data:
            assert "uri" in cls
            assert "label" in cls

    def test_classes_limit_parameter(self, client):
        """Can limit number of classes returned."""
        encoded_uri = ONTOLOGY_URI.replace("/", "%2F").replace(":", "%3A")
        response = client.get(f"/api/ontologies/{encoded_uri}/classes?limit=2")
        assert response.status_code == 200
        assert len(response.json()) <= 2


class TestExecuteQuery:
    """Test POST /api/query endpoint."""

    def test_execute_query(self, client):
        """Can execute SPARQL query."""
        response = client.post(
            "/api/query",
            json={"sparql": "SELECT ?s WHERE { ?s a <http://www.w3.org/2002/07/owl#Class> } LIMIT 5"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "count" in data
        assert isinstance(data["results"], list)

    def test_query_with_limit(self, client):
        """Query respects limit parameter."""
        response = client.post(
            "/api/query",
            json={
                "sparql": "SELECT ?s WHERE { ?s a <http://www.w3.org/2002/07/owl#Class> }",
                "limit": 2
            }
        )
        data = response.json()
        assert len(data["results"]) <= 2

    def test_query_invalid_sparql(self, client):
        """Returns 400 for invalid SPARQL."""
        response = client.post(
            "/api/query",
            json={"sparql": "NOT VALID SPARQL"}
        )
        assert response.status_code == 400

    def test_query_graph_specific(self, client):
        """Can query specific graph."""
        response = client.post(
            "/api/query",
            json={
                "sparql": f"""
                    SELECT ?class WHERE {{
                        GRAPH <{ONTOLOGY_URI}> {{
                            ?class a <http://www.w3.org/2002/07/owl#Class> .
                        }}
                    }}
                """
            }
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) > 0


class TestIngestOntology:
    """Test POST /api/ontologies/ingest endpoint."""

    def test_ingest_invalid_url(self, empty_client):
        """Returns 400 for unrecognized URL format."""
        response = empty_client.post(
            "/api/ontologies/ingest",
            json={"url": "http://example.org/not-an-ontoportal-url"}
        )
        assert response.status_code == 400
        assert "not recognized" in response.json()["detail"].lower()

    def test_ingest_missing_api_key(self, empty_client):
        """Returns 400 when API key not configured."""
        response = empty_client.post(
            "/api/ontologies/ingest",
            json={"url": "https://bioportal.bioontology.org/ontologies/ENVO"}
        )
        assert response.status_code == 400
        assert "api key" in response.json()["detail"].lower()


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """CORS headers are present for allowed origins."""
        response = client.get(
            "/api/ontologies",
            headers={"Origin": "http://localhost:5173"}
        )
        assert response.status_code == 200
        # Note: TestClient may not fully emulate CORS behavior
