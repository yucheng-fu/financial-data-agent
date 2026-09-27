from pathlib import Path
from typing import Protocol

from financial_data_agent.config import is_local, require_env


def filing_blob_name(ticker: str, year: int, quarter: int) -> str:
    """Build the partitioned location of a filing markdown file.

    Args:
        ticker: Public company ticker symbol.
        year: Filing year.
        quarter: Calendar quarter, from 1 to 4.

    Returns:
        The relative filing location, using forward slashes.
    """
    symbol = ticker.upper()
    file_stem = f"{symbol}_{year}_Q{quarter}"
    return f"ticker={symbol}/year={year}/quarter=Q{quarter}/{file_stem}.md"


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


class FilingsStorage(Protocol):
    """Persist filing markdown content."""

    def save(self, blob_name: str, content: str) -> str:
        """Save filing content.

        Args:
            blob_name: Relative location of the filing.
            content: Filing markdown content.

        Returns:
            The stored filing location.
        """
        ...


class LocalFilingsStorage:
    """Store filings on the local filesystem."""

    def __init__(self, data_dir: Path) -> None:
        """Initialize the storage.

        Args:
            data_dir: Root directory used to store downloaded filings.
        """
        self.data_dir = data_dir

    def save(self, blob_name: str, content: str) -> str:
        """Write filing content to disk.

        Args:
            blob_name: Relative location of the filing.
            content: Filing markdown content.

        Returns:
            The path of the written file.
        """
        file_path = self.data_dir / blob_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path.as_posix()


class AzureBlobFilingsStorage:
    """Store filings in an Azure Blob Storage container."""

    def __init__(self, container_client: BlobContainerClient) -> None:
        """Initialize the storage.

        Args:
            container_client: Azure blob container client for the filings container.
        """
        self.container_client = container_client

    def save(self, blob_name: str, content: str) -> str:
        """Upload filing content to the filings container.

        Args:
            blob_name: Name of the blob holding the filing.
            content: Filing markdown content.

        Returns:
            The name of the uploaded blob.
        """
        self.container_client.upload_blob(
            name=blob_name, data=content.encode("utf-8"), overwrite=True
        )
        return blob_name


def build_filings_storage(data_dir: Path) -> FilingsStorage:
    """Build the filings storage backend for the current environment.

    Args:
        data_dir: Root directory used by the local storage backend.

    Returns:
        Local storage in the local environment, Azure Blob storage otherwise.
    """
    if is_local():
        return LocalFilingsStorage(data_dir)

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    account_url = f"https://{require_env('STORAGE_ACCOUNT_NAME')}.blob.core.windows.net"
    service_client = BlobServiceClient(
        account_url=account_url, credential=DefaultAzureCredential()
    )
    return AzureBlobFilingsStorage(
        service_client.get_container_client(require_env("FILINGS_CONTAINER"))
    )
