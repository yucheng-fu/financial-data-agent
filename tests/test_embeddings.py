from __future__ import annotations

import pytest

from financial_data_agent.constants import EMBEDDING_DIMENSIONS
from financial_data_agent.ingestion.embeddings import build_embedder

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def test_build_embedder_requires_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="EMBEDDING_MODEL"):
        build_embedder()


def test_embedder_produces_vectors_of_the_stored_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL", EMBEDDING_MODEL)

    embedder = build_embedder()
    vectors = embedder.embed_documents(["Revenue increased 12% year over year.", "Total assets were 352,583."])

    assert len(vectors) == 2
    assert all(len(vector) == EMBEDDING_DIMENSIONS for vector in vectors)
    assert all(isinstance(value, float) for value in vectors[0])
    assert len(embedder.embed_query("What was revenue?")) == EMBEDDING_DIMENSIONS
