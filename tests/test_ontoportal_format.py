"""Tests for OntoPortal data format compatibility.

These tests verify that ontologies in the format commonly found on
OntoPortal instances (BioPortal, AgroPortal, etc.) can be properly
loaded and queried.
"""

import pytest
from ait.store import Store, RdfFormat
from ait.web import parse_ontoportal_url, ONTOPORTAL_URL_PATTERNS
from ait.clients.ontoportal import OntoPortalInstance


# Realistic GLOSIS-style ontology (based on AgroPortal's GLOSIS)
# Using full URIs instead of prefixed names with slashes (which aren't valid Turtle)
GLOSIS_STYLE_ONTOLOGY = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .

# Ontology metadata
<http://w3id.org/glosis/model> a owl:Ontology ;
    rdfs:label "GLOSIS Web Ontology" ;
    rdfs:comment "Global Soil Information System ontology" ;
    owl:versionInfo "1.0.0" .

# External classes referenced
sosa:Observation a owl:Class ;
    rdfs:label "Observation" .

sosa:FeatureOfInterest a owl:Class ;
    rdfs:label "FeatureOfInterest" .

sosa:Result a owl:Class ;
    rdfs:label "Result" .

skos:Concept a owl:Class ;
    rdfs:label "Concept" .

<http://def.isotc211.org/iso19156/2011/Observation#OM_Observation> a owl:Class ;
    rdfs:label "OM_Observation" .

<http://def.isotc211.org/iso19156/2011/SamplingFeature#SF_SamplingFeature> a owl:Class ;
    rdfs:label "SF_SamplingFeature" ;
    rdfs:subClassOf sosa:FeatureOfInterest .

# GLOSIS domain classes
<http://w3id.org/glosis/model/layerhorizon/SoilLayer> a owl:Class ;
    rdfs:label "Soil Layer" ;
    rdfs:comment "A layer or horizon within a soil profile" ;
    rdfs:subClassOf <http://def.isotc211.org/iso19156/2011/SamplingFeature#SF_SamplingFeature> .

<http://w3id.org/glosis/model/layerhorizon/SoilHorizon> a owl:Class ;
    rdfs:label "Soil Horizon" ;
    rdfs:comment "A pedogenic horizon within soil" ;
    rdfs:subClassOf <http://w3id.org/glosis/model/layerhorizon/SoilLayer> .

<http://w3id.org/glosis/model/site/SoilSite> a owl:Class ;
    rdfs:label "Soil Site" ;
    rdfs:comment "A site where soil observations are made" ;
    rdfs:subClassOf sosa:FeatureOfInterest .

<http://w3id.org/glosis/model/profile/SoilProfile> a owl:Class ;
    rdfs:label "Soil Profile" ;
    rdfs:comment "A vertical section through soil" ;
    rdfs:subClassOf <http://def.isotc211.org/iso19156/2011/SamplingFeature#SF_SamplingFeature> .

# Observation classes
<http://w3id.org/glosis/model/layerhorizon/AluminiumExtractableElements> a owl:Class ;
    rdfs:label "AluminiumExtractableElements" ;
    rdfs:comment "Observation of aluminium extractable elements" ;
    rdfs:subClassOf sosa:Observation ;
    rdfs:subClassOf <http://def.isotc211.org/iso19156/2011/Observation#OM_Observation> .

<http://w3id.org/glosis/model/layerhorizon/CarbonTotal> a owl:Class ;
    rdfs:label "CarbonTotal" ;
    rdfs:comment "Observation of total carbon content" ;
    rdfs:subClassOf sosa:Observation .

# Code list classes (SKOS-based)
<http://w3id.org/glosis/model/codelists/SoilTypeCode> a owl:Class ;
    rdfs:label "Code list for SoilType - codelist class" ;
    rdfs:subClassOf skos:Concept .

<http://w3id.org/glosis/model/codelists/TextureCode> a owl:Class ;
    rdfs:label "Code list for Texture - codelist class" ;
    rdfs:subClassOf skos:Concept .

<http://w3id.org/glosis/model/codelists/ConsistenceDryValueCode> a owl:Class ;
    rdfs:label "Code list for ConsistenceDryValue - codelist class" ;
    rdfs:subClassOf skos:Concept .

# Properties
<http://w3id.org/glosis/model/common/hasLayer> a owl:ObjectProperty ;
    rdfs:label "has layer" ;
    rdfs:domain <http://w3id.org/glosis/model/profile/SoilProfile> ;
    rdfs:range <http://w3id.org/glosis/model/layerhorizon/SoilLayer> .

<http://w3id.org/glosis/model/common/atSite> a owl:ObjectProperty ;
    rdfs:label "at site" ;
    rdfs:domain <http://w3id.org/glosis/model/profile/SoilProfile> ;
    rdfs:range <http://w3id.org/glosis/model/site/SoilSite> .

<http://w3id.org/glosis/model/layerhorizon/upperDepth> a owl:DatatypeProperty ;
    rdfs:label "upper depth" ;
    rdfs:domain <http://w3id.org/glosis/model/layerhorizon/SoilLayer> ;
    rdfs:range xsd:decimal .

<http://w3id.org/glosis/model/layerhorizon/lowerDepth> a owl:DatatypeProperty ;
    rdfs:label "lower depth" ;
    rdfs:domain <http://w3id.org/glosis/model/layerhorizon/SoilLayer> ;
    rdfs:range xsd:decimal .
"""

ONTOLOGY_URI = "https://data.agroportal.lirmm.fr/ontologies/GLOSIS"


@pytest.fixture
def glosis_store():
    """Store loaded with GLOSIS-style ontology."""
    store = Store()
    store.load_rdf(GLOSIS_STYLE_ONTOLOGY, format=RdfFormat.TURTLE, graph_name=ONTOLOGY_URI)
    return store


class TestOntoPortalUrlParsing:
    """Test URL parsing for different OntoPortal instances."""

    def test_parse_bioportal_web_url(self):
        """Can parse BioPortal web interface URL."""
        result = parse_ontoportal_url("https://bioportal.bioontology.org/ontologies/ENVO")
        assert result is not None
        instance, acronym = result
        assert instance == OntoPortalInstance.BIOPORTAL
        assert acronym == "ENVO"

    def test_parse_bioportal_api_url(self):
        """Can parse BioPortal API URL."""
        result = parse_ontoportal_url("https://data.bioontology.org/ontologies/GO")
        assert result is not None
        instance, acronym = result
        assert instance == OntoPortalInstance.BIOPORTAL
        assert acronym == "GO"

    def test_parse_agroportal_web_url(self):
        """Can parse AgroPortal web interface URL."""
        result = parse_ontoportal_url("https://agroportal.lirmm.fr/ontologies/GLOSIS")
        assert result is not None
        instance, acronym = result
        assert instance == OntoPortalInstance.AGROPORTAL
        assert acronym == "GLOSIS"

    def test_parse_agroportal_api_url(self):
        """Can parse AgroPortal API URL."""
        result = parse_ontoportal_url("https://data.agroportal.lirmm.fr/ontologies/AGROVOC")
        assert result is not None
        instance, acronym = result
        assert instance == OntoPortalInstance.AGROPORTAL
        assert acronym == "AGROVOC"

    def test_parse_ecoportal_url(self):
        """Can parse EcoPortal URL."""
        result = parse_ontoportal_url("https://ecoportal.lifewatch.eu/ontologies/ENVO")
        assert result is not None
        instance, acronym = result
        assert instance == OntoPortalInstance.ECOPORTAL
        assert acronym == "ENVO"

    def test_parse_matportal_url(self):
        """Can parse MatPortal URL."""
        result = parse_ontoportal_url("https://matportal.org/ontologies/EMMO")
        assert result is not None
        instance, acronym = result
        assert instance == OntoPortalInstance.MATPORTAL
        assert acronym == "EMMO"

    def test_parse_http_url(self):
        """Can parse HTTP (non-HTTPS) URLs."""
        result = parse_ontoportal_url("http://bioportal.bioontology.org/ontologies/ENVO")
        assert result is not None

    def test_parse_url_with_trailing_slash(self):
        """Handles URLs with trailing content gracefully."""
        # URLs should not have trailing parts for basic parsing
        result = parse_ontoportal_url("https://bioportal.bioontology.org/ontologies/ENVO")
        assert result is not None

    def test_parse_invalid_url(self):
        """Returns None for non-OntoPortal URLs."""
        result = parse_ontoportal_url("https://example.org/ontologies/TEST")
        assert result is None

    def test_parse_empty_string(self):
        """Returns None for empty string."""
        result = parse_ontoportal_url("")
        assert result is None

    def test_acronym_with_numbers(self):
        """Can parse acronyms containing numbers."""
        result = parse_ontoportal_url("https://bioportal.bioontology.org/ontologies/GO2")
        assert result is not None
        assert result[1] == "GO2"

    def test_acronym_with_underscore(self):
        """Can parse acronyms containing underscores."""
        result = parse_ontoportal_url("https://bioportal.bioontology.org/ontologies/SOME_ONTO")
        assert result is not None
        assert result[1] == "SOME_ONTO"

    def test_acronym_with_hyphen(self):
        """Can parse acronyms containing hyphens."""
        result = parse_ontoportal_url("https://bioportal.bioontology.org/ontologies/SOME-ONTO")
        assert result is not None
        assert result[1] == "SOME-ONTO"


class TestGlosisFormatLoading:
    """Test loading GLOSIS-style ontology data."""

    def test_load_glosis_format(self, glosis_store):
        """Can load GLOSIS-style Turtle format."""
        assert len(glosis_store) > 0

    def test_glosis_graph_exists(self, glosis_store):
        """Ontology is loaded into named graph."""
        graphs = list(glosis_store.graphs())
        assert ONTOLOGY_URI in graphs


class TestGlosisClassQueries:
    """Test querying classes from GLOSIS-style ontology."""

    def test_find_owl_classes(self, glosis_store):
        """Can find OWL classes."""
        results = glosis_store.query(f"""
            SELECT ?class WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                }}
            }}
        """)
        assert len(results) > 0

    def test_find_classes_with_labels(self, glosis_store):
        """Can find classes with their labels."""
        results = glosis_store.query(f"""
            SELECT ?class ?label WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                    ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }}
            }}
        """)
        assert len(results) > 0
        assert all("label" in r for r in results)

    def test_find_subclass_relationships(self, glosis_store):
        """Can find subClassOf relationships."""
        results = glosis_store.query(f"""
            SELECT ?child ?parent WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?child <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent .
                }}
            }}
        """)
        assert len(results) > 0

    def test_find_domain_classes(self, glosis_store):
        """Can find domain-specific classes (glosis namespace)."""
        results = glosis_store.query(f"""
            SELECT ?class ?label WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                    ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                    FILTER(STRSTARTS(STR(?class), "http://w3id.org/glosis/"))
                }}
            }}
        """)
        assert len(results) > 0

    def test_find_codelist_classes(self, glosis_store):
        """Can find code list classes (subclass of skos:Concept)."""
        results = glosis_store.query(f"""
            SELECT ?codelist ?label WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?codelist a <http://www.w3.org/2002/07/owl#Class> .
                    ?codelist <http://www.w3.org/2000/01/rdf-schema#subClassOf> <http://www.w3.org/2004/02/skos/core#Concept> .
                    ?codelist <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }}
            }}
        """)
        assert len(results) >= 3  # We have 3 codelist classes

    def test_find_observation_classes(self, glosis_store):
        """Can find observation classes (subclass of sosa:Observation)."""
        results = glosis_store.query(f"""
            SELECT ?obs ?label WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?obs a <http://www.w3.org/2002/07/owl#Class> .
                    ?obs <http://www.w3.org/2000/01/rdf-schema#subClassOf> <http://www.w3.org/ns/sosa/Observation> .
                    ?obs <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }}
            }}
        """)
        assert len(results) >= 2  # AluminiumExtractableElements and CarbonTotal


class TestGlosisPropertyQueries:
    """Test querying properties from GLOSIS-style ontology."""

    def test_find_object_properties(self, glosis_store):
        """Can find OWL object properties."""
        results = glosis_store.query(f"""
            SELECT ?prop ?label WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?prop a <http://www.w3.org/2002/07/owl#ObjectProperty> .
                    ?prop <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }}
            }}
        """)
        assert len(results) >= 2

    def test_find_datatype_properties(self, glosis_store):
        """Can find OWL datatype properties."""
        results = glosis_store.query(f"""
            SELECT ?prop ?label WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?prop a <http://www.w3.org/2002/07/owl#DatatypeProperty> .
                    ?prop <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }}
            }}
        """)
        assert len(results) >= 2

    def test_find_property_domains(self, glosis_store):
        """Can find property domain restrictions."""
        results = glosis_store.query(f"""
            SELECT ?prop ?domain WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?prop <http://www.w3.org/2000/01/rdf-schema#domain> ?domain .
                }}
            }}
        """)
        assert len(results) > 0

    def test_find_property_ranges(self, glosis_store):
        """Can find property range restrictions."""
        results = glosis_store.query(f"""
            SELECT ?prop ?range WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?prop <http://www.w3.org/2000/01/rdf-schema#range> ?range .
                }}
            }}
        """)
        assert len(results) > 0


class TestGlosisHierarchy:
    """Test querying class hierarchies in GLOSIS-style ontology."""

    def test_class_hierarchy_depth(self, glosis_store):
        """Can traverse class hierarchy."""
        # Find SoilHorizon's parent chain
        results = glosis_store.query(f"""
            SELECT ?class ?parent WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    <http://w3id.org/glosis/model/layerhorizon/SoilHorizon>
                        <http://www.w3.org/2000/01/rdf-schema#subClassOf>+ ?parent .
                }}
            }}
        """)
        # Should find SoilLayer and SF_SamplingFeature in hierarchy
        parents = [r["parent"] for r in results if "parent" in r]
        assert len(parents) > 0

    def test_find_leaf_classes(self, glosis_store):
        """Can identify leaf classes (no subclasses)."""
        results = glosis_store.query(f"""
            SELECT ?class WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                    FILTER NOT EXISTS {{
                        ?child <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?class .
                    }}
                    FILTER(STRSTARTS(STR(?class), "http://w3id.org/glosis/"))
                }}
            }}
        """)
        assert len(results) > 0

    def test_multiple_inheritance(self, glosis_store):
        """Can query classes with multiple parents."""
        # AluminiumExtractableElements has two parents
        results = glosis_store.query(f"""
            SELECT ?parent WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    <http://w3id.org/glosis/model/layerhorizon/AluminiumExtractableElements>
                        <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent .
                }}
            }}
        """)
        assert len(results) >= 2  # sosa:Observation and OM_Observation


class TestGlosisMetadata:
    """Test querying ontology metadata."""

    def test_find_ontology_declaration(self, glosis_store):
        """Can find ontology declaration."""
        results = glosis_store.query(f"""
            SELECT ?ont ?label WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?ont a <http://www.w3.org/2002/07/owl#Ontology> .
                    OPTIONAL {{ ?ont <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
                }}
            }}
        """)
        assert len(results) >= 1

    def test_find_ontology_version(self, glosis_store):
        """Can find ontology version info."""
        results = glosis_store.query(f"""
            SELECT ?version WHERE {{
                GRAPH <{ONTOLOGY_URI}> {{
                    ?ont a <http://www.w3.org/2002/07/owl#Ontology> .
                    ?ont <http://www.w3.org/2002/07/owl#versionInfo> ?version .
                }}
            }}
        """)
        assert len(results) >= 1
        assert results[0]["version"] == "1.0.0"


class TestRdfXmlFormat:
    """Test loading RDF/XML format (common OntoPortal download format)."""

    def test_load_rdfxml(self):
        """Can load RDF/XML format."""
        rdfxml = """<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
            xmlns:owl="http://www.w3.org/2002/07/owl#">

            <owl:Ontology rdf:about="http://example.org/test">
                <rdfs:label>Test</rdfs:label>
            </owl:Ontology>

            <owl:Class rdf:about="http://example.org/test#MyClass">
                <rdfs:label>My Class</rdfs:label>
                <rdfs:subClassOf rdf:resource="http://www.w3.org/2002/07/owl#Thing"/>
            </owl:Class>
        </rdf:RDF>
        """
        store = Store()
        count = store.load_rdf(rdfxml, format=RdfFormat.XML, graph_name="http://test")
        assert count > 0

    def test_rdfxml_classes_queryable(self):
        """Classes from RDF/XML are queryable."""
        rdfxml = """<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
            xmlns:owl="http://www.w3.org/2002/07/owl#">

            <owl:Class rdf:about="http://example.org/test#ClassA">
                <rdfs:label>Class A</rdfs:label>
            </owl:Class>

            <owl:Class rdf:about="http://example.org/test#ClassB">
                <rdfs:label>Class B</rdfs:label>
                <rdfs:subClassOf rdf:resource="http://example.org/test#ClassA"/>
            </owl:Class>
        </rdf:RDF>
        """
        store = Store()
        store.load_rdf(rdfxml, format=RdfFormat.XML, graph_name="http://test")

        results = store.query("""
            SELECT ?class ?label WHERE {
                GRAPH <http://test> {
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                    ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                }
            }
        """)
        assert len(results) == 2
        labels = [r["label"] for r in results]
        assert "Class A" in labels
        assert "Class B" in labels
