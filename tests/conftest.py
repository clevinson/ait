"""Pytest fixtures for ait tests."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from ait.store import Store, RdfFormat


# Sample OWL ontology in Turtle format (similar to AgroPortal/GLOSIS structure)
SAMPLE_ONTOLOGY_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix ex: <http://example.org/ontology#> .

# Ontology declaration
<http://example.org/ontology> a owl:Ontology ;
    rdfs:label "Example Ontology" ;
    rdfs:comment "A test ontology mimicking AgroPortal structure" .

# Top-level classes
ex:Feature a owl:Class ;
    rdfs:label "Feature" ;
    rdfs:comment "A spatial feature" .

ex:Observation a owl:Class ;
    rdfs:label "Observation" ;
    rdfs:comment "An observation of a property" .

ex:Concept a owl:Class ;
    rdfs:label "Concept" ;
    rdfs:comment "A SKOS-like concept" .

# Subclasses (hierarchy)
ex:SoilFeature a owl:Class ;
    rdfs:label "Soil Feature" ;
    rdfs:subClassOf ex:Feature ;
    rdfs:comment "A feature related to soil" .

ex:SoilObservation a owl:Class ;
    rdfs:label "Soil Observation" ;
    rdfs:subClassOf ex:Observation ;
    rdfs:comment "An observation of soil properties" .

ex:SoilProfile a owl:Class ;
    rdfs:label "Soil Profile" ;
    rdfs:subClassOf ex:SoilFeature ;
    rdfs:comment "A vertical section through soil" .

ex:SoilLayer a owl:Class ;
    rdfs:label "Soil Layer" ;
    rdfs:subClassOf ex:SoilFeature ;
    rdfs:comment "A horizontal layer in a soil profile" .

# Code list class (common in AgroPortal ontologies)
ex:SoilTypeCode a owl:Class ;
    rdfs:label "Code list for SoilType" ;
    rdfs:subClassOf ex:Concept ;
    rdfs:comment "Enumeration of soil types" .

ex:TextureCode a owl:Class ;
    rdfs:label "Code list for Texture" ;
    rdfs:subClassOf ex:Concept ;
    rdfs:comment "Enumeration of soil textures" .

# Properties
ex:hasLayer a owl:ObjectProperty ;
    rdfs:label "has layer" ;
    rdfs:domain ex:SoilProfile ;
    rdfs:range ex:SoilLayer .

ex:hasSoilType a owl:ObjectProperty ;
    rdfs:label "has soil type" ;
    rdfs:domain ex:SoilFeature ;
    rdfs:range ex:SoilTypeCode .

ex:depth a owl:DatatypeProperty ;
    rdfs:label "depth" ;
    rdfs:domain ex:SoilLayer ;
    rdfs:range xsd:decimal .
"""

# Sample RDF/XML format (common download format from OntoPortal)
SAMPLE_ONTOLOGY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:ex="http://example.org/ontology#">

    <owl:Ontology rdf:about="http://example.org/ontology">
        <rdfs:label>Example Ontology XML</rdfs:label>
    </owl:Ontology>

    <owl:Class rdf:about="http://example.org/ontology#Feature">
        <rdfs:label>Feature</rdfs:label>
        <rdfs:comment>A spatial feature</rdfs:comment>
    </owl:Class>

    <owl:Class rdf:about="http://example.org/ontology#SoilFeature">
        <rdfs:label>Soil Feature</rdfs:label>
        <rdfs:subClassOf rdf:resource="http://example.org/ontology#Feature"/>
    </owl:Class>

    <owl:Class rdf:about="http://example.org/ontology#SoilProfile">
        <rdfs:label>Soil Profile</rdfs:label>
        <rdfs:subClassOf rdf:resource="http://example.org/ontology#SoilFeature"/>
    </owl:Class>
</rdf:RDF>
"""

ONTOLOGY_URI = "http://example.org/ontology"


@pytest.fixture
def temp_store_path():
    """Provide a temporary directory for store persistence."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "store"


@pytest.fixture
def memory_store():
    """Provide an in-memory store."""
    return Store()


@pytest.fixture
def persistent_store(temp_store_path):
    """Provide a persistent store in a temp directory."""
    return Store(temp_store_path)


@pytest.fixture
def loaded_store(memory_store):
    """Provide a store pre-loaded with sample ontology."""
    memory_store.load_rdf(
        SAMPLE_ONTOLOGY_TTL,
        format=RdfFormat.TURTLE,
        graph_name=ONTOLOGY_URI,
    )
    return memory_store


@pytest.fixture
def sample_ttl():
    """Return sample Turtle ontology data."""
    return SAMPLE_ONTOLOGY_TTL


@pytest.fixture
def sample_xml():
    """Return sample RDF/XML ontology data."""
    return SAMPLE_ONTOLOGY_XML


@pytest.fixture
def ontology_uri():
    """Return the sample ontology URI."""
    return ONTOLOGY_URI
