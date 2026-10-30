from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import requests

from financial_data_agent.config import is_local, require_env
from financial_data_agent.constants import STORAGE_TIMEOUT_SECONDS


def default_data_dir() -> Path:
    """Return the repository-level data directory.

    Returns:
        Path to the data directory.
    """
    return Path(__file__).resolve().parents[3] / "data"


class BlobDownloader(Protocol):
    """Read the content of a downloaded blob."""

    def readall(self) -> str:
        """Return the whole blob content.

        Returns:
            The decoded blob content.
        """
        ...


class BlobContainerClient(Protocol):
    """Upload and download blobs in a single blob container."""

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

    def download_blob(self, blob: str, *, encoding: str) -> BlobDownloader:
        """Download a blob.

        Args:
            blob: Name of the blob.
            encoding: Text encoding used to decode the blob.

        Returns:
            A downloader for the blob content.
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

    def read_text(self, blob_name: str) -> str:
        """Read text content.

        Args:
            blob_name: Relative location of the file.

        Returns:
            The stored text content.

        Raises:
            FileNotFoundError: If the file does not exist.
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

    def read_text(self, blob_name: str) -> str:
        """Read text content from disk.

        Args:
            blob_name: Relative location of the file.

        Returns:
            The content of the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        file_path = self.data_dir / blob_name
        if not file_path.is_file():
            raise FileNotFoundError(f"{blob_name} was not found under {self.data_dir}")
        return file_path.read_text(encoding="utf-8")

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

    def read_text(self, blob_name: str) -> str:
        """Download a blob as UTF-8 text.

        Args:
            blob_name: Name of the blob.

        Returns:
            The content of the blob.

        Raises:
            FileNotFoundError: If the blob does not exist.
        """
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return self.container_client.download_blob(blob_name, encoding="UTF-8").readall()
        except ResourceNotFoundError as error:
            raise FileNotFoundError(f"{blob_name} was not found in the container") from error


class SupabaseDataStorage:
    """Store ingested data in a Supabase Storage bucket through its REST API."""

    def __init__(self, base_url: str, secret_key: str, bucket: str) -> None:
        """Initialize the storage.

        Args:
            base_url: Project URL, e.g. "https://<project_ref>.supabase.co".
            secret_key: Secret API key of the project, which bypasses row level security.
            bucket: Name of the bucket holding the ingested data.
        """
        self.object_url = f"{base_url.rstrip('/')}/storage/v1/object/{bucket}"
        self.headers = {"apikey": secret_key, "Authorization": f"Bearer {secret_key}"}

    def save_text(self, blob_name: str, content: str) -> str:
        """Upload text content as a UTF-8 encoded object.

        Args:
            blob_name: Name of the object.
            content: Text content.

        Returns:
            The name of the uploaded object.
        """
        return self.save_bytes(blob_name, content.encode("utf-8"))

    def save_bytes(self, blob_name: str, content: bytes) -> str:
        """Upload binary content as an object, replacing any existing one.

        Args:
            blob_name: Name of the object.
            content: Binary content.

        Returns:
            The name of the uploaded object.

        Raises:
            requests.HTTPError: If the upload is rejected.
        """
        response = requests.post(
            self._url(blob_name),
            data=content,
            headers={**self.headers, "x-upsert": "true"},
            timeout=STORAGE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return blob_name

    def read_text(self, blob_name: str) -> str:
        """Download an object as UTF-8 text.

        Args:
            blob_name: Name of the object.

        Returns:
            The content of the object.

        Raises:
            FileNotFoundError: If the object does not exist.
            requests.HTTPError: If the download fails for another reason.
        """
        response = requests.get(self._url(blob_name), headers=self.headers, timeout=STORAGE_TIMEOUT_SECONDS)
        if is_missing_object(response):
            raise FileNotFoundError(f"{blob_name} was not found in the bucket")
        response.raise_for_status()
        return response.content.decode("utf-8")

    def _url(self, blob_name: str) -> str:
        """Build the object URL, escaping characters such as "&" and "=" in the name.

        Args:
            blob_name: Name of the object.

        Returns:
            The object URL.
        """
        return f"{self.object_url}/{quote(blob_name)}"


def is_missing_object(response: requests.Response) -> bool:
    """Check whether a Supabase Storage response reports a missing object.

    Storage reports a missing object either as HTTP 404 or as HTTP 400 whose body carries
    `"statusCode": "404"`, depending on the server version.

    Args:
        response: Response of an object download.

    Returns:
        True when the object does not exist.
    """
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    try:
        return str(response.json().get("statusCode")) == "404"
    except ValueError:
        return False


def build_data_storage(data_dir: Path | None = None) -> DataStorage:
    """Build the ingestion storage backend for the current environment.

    `AzureBlobDataStorage` is kept from the retired Azure deployment but is no longer selected.

    Args:
        data_dir: Root directory used by the local storage backend.

    Returns:
        Local storage in the local environment, Supabase Storage otherwise.

    Raises:
        RuntimeError: If a required Supabase environment variable is not set.
    """
    if is_local():
        return LocalDataStorage(data_dir if data_dir is not None else default_data_dir())

    return SupabaseDataStorage(
        base_url=require_env("SUPABASE_URL"),
        secret_key=require_env("SUPABASE_SECRET"),
        bucket=require_env("FILINGS_BUCKET"),
    )
