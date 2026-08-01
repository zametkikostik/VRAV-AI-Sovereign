"""CELLAR SPARQL client unit tests (offline structure)."""

from core.tools.cellar_sparql import CellarSPARQL


def test_sparql_query_builder_shape():
    c = CellarSPARQL()
    assert c.language == "eng"
    assert "sparql" in c.endpoint
