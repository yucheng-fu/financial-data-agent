from pathlib import Path
from typing import Protocol

from financial_data_agent.config import is_local, require_env


def default_data_dir() -> Path:
    """Return the repository-level data directory.

    Returns:
        Path to the data directory.
    """
    return Path(__file__).resolve().parents[3] / "data"


class BlobContainerClient(Protocol):
    """Upload blobs to a single blob container."""

    def upload_blob(self, name: str, data: bytes, overwrite: bool) -> object:
        """Upload a blob.

        Args:
            name: Name of the blob.
            data: Blob content.
            overwrite: Whether an existing blob is replaced.

        Returns:
            The client-specific upload result.
        """
        ...


class DataStorage(Protocol):
    """Persist ingested data files."""

    def save_text(self, blob_name: str, content: str) -> str:
        """Save text content.

        Args:
            blob_name: Relative location of the file.
            content: Text content.

        Returns:
            The stored location.
        """
        ...

    def save_bytes(self, blob_name: str, content: bytes) -> str:
        """Save binary content.

        Args:
            blob_name: Relative location of the file.
            content: Binary content.

        Returns:
            The stored location.
        """
        ...


class LocalDataStorage:
    """Store ingested data on the local filesystem."""

    def __init__(self, data_dir: Path) -> None:
        """Initialize the storage.

        Args:
            data_dir: Root directory used to store ingested data.
        """
        self.data_dir = data_dir

    def save_text(self, blob_name: str, content: str) -> str:
        """Write text content to disk.

        Args:
            blob_name: Relative location of the file.
            content: Text content.

        Returns:
            The path of the written file.
        """
        file_path = self._prepare_path(blob_name)
        file_path.write_text(content, encoding="utf-8")
        return file_path.as_posix()

    def save_bytes(self, blob_name: str, content: bytes) -> str:
        """Write binary content to disk.

        Args:
            blob_name: Relative location of the file.
            content: Binary content.

        Returns:
            The path of the written file.
        """
        file_path = self._prepare_path(blob_name)
        file_path.write_bytes(content)
        return file_path.as_posix()

    def _prepare_path(self, blob_name: str) -> Path:
        """Resolve a location under the data directory and create its parents.

        Args:
            blob_name: Relative location of the file.

        Returns:
            The absolute path to write to.
        """
        file_path = self.data_dir / blob_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path


class AzureBlobDataStorage:
    """Store ingested data in an Azure Blob Storage container."""

    def __init__(self, container_client: BlobContainerClient) -> None:
        """Initialize the storage.

        Args:
            container_client: Azure blob container client for the ingestion container.
        """
        self.container_client = container_client

    def save_text(self, blob_name: str, content: str) -> str:
        """Upload text content as a UTF-8 encoded blob.

        Args:
            blob_name: Name of the blob.
            content: Text content.

        Returns:
            The name of the uploaded blob.
        """
        return self.save_bytes(blob_name, content.encode("utf-8"))

    def save_bytes(self, blob_name: str, content: bytes) -> str:
        """Upload binary content as a blob.

        Args:
            blob_name: Name of the blob.
            content: Binary content.

        Returns:
            The name of the uploaded blob.
        """
        self.container_client.upload_blob(name=blob_name, data=content, overwrite=True)
        return blob_name


def build_data_storage(data_dir: Path | None = None) -> DataStorage:
    """Build the ingestion storage backend for the current environment.

    Args:
        data_dir: Root directory used by the local storage backend.

    Returns:
        Local storage in the local environment, Azure Blob storage otherwise.
    """
    if is_local():
        return LocalDataStorage(data_dir if data_dir is not None else default_data_dir())

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    account_url = f"https://{require_env('STORAGE_ACCOUNT_NAME')}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
    return AzureBlobDataStorage(service_client.get_container_client(require_env("FILINGS_CONTAINER")))
