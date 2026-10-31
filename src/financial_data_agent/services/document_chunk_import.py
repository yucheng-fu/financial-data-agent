from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from financial_data_agent.config import get_embedding_model
from financial_data_agent.constants import (
    CHUNK_FIELDS,
    CREATED_STATUS,
    EMBEDDING_DIMENSIONS,
    REPLACED_STATUS,
    SKIPPED_STATUS,
)
from financial_data_agent.db.DTO.document_chunk import DocumentChunkDTO
from financial_data_agent.db.models.document import Document
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.db.repositories.document_chunk import DocumentChunkRepository
from financial_data_agent.ingestion.embeddings import Embedder, get_embedder
from financial_data_agent.ingestion.markdown_chunking import chunk_markdown
from financial_data_agent.ingestion.storage import DataStorage, build_data_storage
from financial_data_agent.services.filing_import import CompanyNotFoundError
from financial_data_agent.services.financial_metrics_import import DocumentNotFoundError


class FilingContentNotFoundError(Exception):
    """Raised when the stored markdown of a filing cannot be read back."""


class EmbeddingDimensionError(Exception):
    """Raised when an embedding does not match the dimension of the vector column."""


@dataclass(frozen=True, slots=True)
class ImportedChunks:
    """The chunk import outcome of one filing."""

    document_type: str
    period_type: str
    chunk_count: int
    status: str


@dataclass(frozen=True, slots=True)
class DocumentChunkImportResult:
    """Outcome of a document chunk import."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    filings: list[ImportedChunks]


class DocumentChunkImportService:
    """Chunk and embed stored filings into the vector store."""

    def __init__(
        self,
        session: Session,
        storage: DataStorage | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Database session used for persistence.
            storage: Optional storage backend holding the filing markdown.
            embedder: Optional embedding backend.
        """
        self.company_repository = CompanyRepository(session)
        self.document_repository = DocumentRepository(session)
        self.chunk_repository = DocumentChunkRepository(session)
        self.storage = storage or build_data_storage()
        self.embedder = embedder
        self.embedding_model = get_embedding_model()

    def import_chunks(
        self, ticker: str, reporting_year: int, reporting_quarter: int, force: bool = False
    ) -> DocumentChunkImportResult:
        """Chunk, embed and persist the stored markdown of the filings reported in a calendar quarter.

        An already chunked document is skipped unless `force` is set, in which case its
        chunks are replaced.

        Args:
            ticker: Ticker symbol of the company.
            reporting_year: Calendar year the filings were reported in.
            reporting_quarter: Calendar quarter the filings were reported in, from 1 to 4.
            force: Whether to replace chunks that already exist.

        Returns:
            The normalized ticker, the reporting period, and each filing with its period type, the number of
            stored chunks, and what was done.

        Raises:
            CompanyNotFoundError: If the company does not exist in the database.
            DocumentNotFoundError: If the company has no filing in the database for the period.
            FilingContentNotFoundError: If the stored markdown of a filing is missing.
            EmbeddingDimensionError: If the embedder returns vectors of the wrong dimension.
        """
        normalized_ticker = ticker.upper()
        company = self.company_repository.get_by_ticker(normalized_ticker)
        if company is None:
            raise CompanyNotFoundError(f"Ticker {normalized_ticker} was not found in the database")
        documents = self.document_repository.list_by_period(company.id, reporting_year, reporting_quarter)
        if not documents:
            raise DocumentNotFoundError(
                f"Filing for {normalized_ticker} reported in {reporting_year} Q{reporting_quarter} "
                "was not found in the database"
            )
        return DocumentChunkImportResult(
            normalized_ticker,
            reporting_year,
            reporting_quarter,
            [self._import_document(document, force) for document in documents],
        )

    def _import_document(self, document: Document, force: bool) -> ImportedChunks:
        """Chunk, embed and persist the stored markdown of one filing.

        Args:
            document: The stored filing.
            force: Whether to replace chunks that already exist.

        Returns:
            The filing's type, the number of stored chunks, and what was done.

        Raises:
            FilingContentNotFoundError: If the stored markdown of the filing is missing.
            EmbeddingDimensionError: If the embedder returns vectors of the wrong dimension.
        """
        existing_count = self.chunk_repository.count_by_document_id(document.id)
        if existing_count and not force:
            return ImportedChunks(document.document_type, document.period_type, existing_count, SKIPPED_STATUS)

        blob_name = document.raw_document_path
        try:
            markdown = self.storage.read_text(blob_name)
        except FileNotFoundError as error:
            raise FilingContentNotFoundError(f"Stored filing {blob_name} could not be read") from error

        chunks = chunk_markdown(markdown)
        embeddings = self._embed([chunk.content for chunk in chunks])

        chunk_dtos = [
            DocumentChunkDTO(
                document_id=document.id,
                chunk_index=chunk.index,
                content=chunk.content,
                is_table=chunk.is_table,
                heading_path=chunk.heading_path,
                token_count=chunk.token_count,
                embedding_model=self.embedding_model,
                embedding=embedding,
                supplied_fields=frozenset(CHUNK_FIELDS),
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        if existing_count:
            self.chunk_repository.delete_by_document_id(document.id)
        self.chunk_repository.create_many(chunk_dtos)

        status = REPLACED_STATUS if existing_count else CREATED_STATUS
        return ImportedChunks(document.document_type, document.period_type, len(chunk_dtos), status)

    def _embed(self, contents: list[str]) -> list[list[float]]:
        """Embed chunk contents in one batched call and validate their dimension.

        Args:
            contents: Chunk contents in document order.

        Returns:
            One embedding per content, in the same order.

        Raises:
            EmbeddingDimensionError: If any embedding has the wrong dimension.
        """
        if not contents:
            return []
        embedder = self.embedder or get_embedder()
        embeddings = embedder.embed_documents(contents)
        for embedding in embeddings:
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise EmbeddingDimensionError(
                    f"Model {self.embedding_model} returned {len(embedding)} dimensions, "
                    f"but document_chunks.embedding holds {EMBEDDING_DIMENSIONS}"
                )
        return embeddings
