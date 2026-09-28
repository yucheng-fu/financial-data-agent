from __future__ import annotations

from typing import Protocol

from fastembed import TextEmbedding

from financial_data_agent.config import get_embedding_cache_dir, get_embedding_model


class Embedder(Protocol):
    """Embed text into a shared vector space."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed several documents.

        Args:
            texts: Documents to embed.

        Returns:
            One embedding per document, in the same order.
        """
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query.

        Args:
            text: Query to embed.

        Returns:
            The query embedding.
        """
        ...


class OnnxEmbedder:
    """Embeddings computed in process by a quantized ONNX model."""

    def __init__(self, model: str, cache_dir: str | None = None) -> None:
        """Initialize the backend and load the model.

        Args:
            model: Name of the model, such as "BAAI/bge-small-en-v1.5".
            cache_dir: Directory holding the downloaded model, or None for the default.
        """
        self.model_name = model
        self.model = TextEmbedding(model_name=model, cache_dir=cache_dir)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed several documents.

        Args:
            texts: Documents to embed.

        Returns:
            One embedding per document, in the same order.
        """
        return [vector.tolist() for vector in self.model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query.

        Args:
            text: Query to embed.

        Returns:
            The query embedding.
        """
        return self.embed_documents([text])[0]


def build_embedder() -> Embedder:
    """Build the embedding backend for the current configuration.

    Returns:
        An embedding backend for the configured model.

    Raises:
        RuntimeError: If `EMBEDDING_MODEL` is not set.
    """
    return OnnxEmbedder(model=get_embedding_model(), cache_dir=get_embedding_cache_dir())
