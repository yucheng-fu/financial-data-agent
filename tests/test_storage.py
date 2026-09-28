from pathlib import Path

import pytest

from financial_data_agent.ingestion.storage import (
    AzureBlobDataStorage,
    LocalDataStorage,
    build_data_storage,
    default_data_dir,
)

BLOB_NAME = "ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2/AAPL_2026_Q2.md"


class FakeBlobDownloader:
    """Return canned blob content instead of streaming from Azure."""

    def __init__(self, content: str) -> None:
        self.content = content

    def readall(self) -> str:
        return self.content


class FakeContainerClient:
    """Record blob uploads and serve canned downloads instead of calling Azure."""

    def __init__(self, blobs: dict[str, str] | None = None) -> None:
        self.uploads: list[tuple[str, bytes, bool]] = []
        self.blobs = blobs if blobs is not None else {}
        self.downloads: list[tuple[str, str]] = []

    def upload_blob(self, name: str, data: bytes, overwrite: bool) -> object:
        self.uploads.append((name, data, overwrite))
        return object()

    def download_blob(self, blob: str, *, encoding: str) -> FakeBlobDownloader:
        from azure.core.exceptions import ResourceNotFoundError

        self.downloads.append((blob, encoding))
        if blob not in self.blobs:
            raise ResourceNotFoundError(f"{blob} does not exist")
        return FakeBlobDownloader(self.blobs[blob])


def test_local_data_storage_writes_text_and_returns_disk_path(tmp_path: Path) -> None:
    storage = LocalDataStorage(tmp_path)

    location = storage.save_text(BLOB_NAME, "# Filing")

    assert location == (tmp_path / BLOB_NAME).as_posix()
    assert (tmp_path / BLOB_NAME).read_text(encoding="utf-8") == "# Filing"


def test_local_data_storage_writes_bytes_and_returns_disk_path(tmp_path: Path) -> None:
    storage = LocalDataStorage(tmp_path)

    location = storage.save_bytes("s&p500.parquet", b"PAR1")

    assert location == (tmp_path / "s&p500.parquet").as_posix()
    assert (tmp_path / "s&p500.parquet").read_bytes() == b"PAR1"


def test_azure_blob_data_storage_uploads_text_and_returns_blob_name() -> None:
    container_client = FakeContainerClient()
    storage = AzureBlobDataStorage(container_client)

    location = storage.save_text(BLOB_NAME, "# Filing")

    assert location == BLOB_NAME
    assert container_client.uploads == [(BLOB_NAME, b"# Filing", True)]


def test_azure_blob_data_storage_uploads_bytes_and_returns_blob_name() -> None:
    container_client = FakeContainerClient()
    storage = AzureBlobDataStorage(container_client)

    location = storage.save_bytes("s&p500.parquet", b"PAR1")

    assert location == "s&p500.parquet"
    assert container_client.uploads == [("s&p500.parquet", b"PAR1", True)]


def test_local_data_storage_reads_back_written_text(tmp_path: Path) -> None:
    storage = LocalDataStorage(tmp_path)
    storage.save_text(BLOB_NAME, "# Filing")

    assert storage.read_text(BLOB_NAME) == "# Filing"


def test_local_data_storage_read_text_raises_when_the_file_is_missing(tmp_path: Path) -> None:
    storage = LocalDataStorage(tmp_path)

    with pytest.raises(FileNotFoundError, match=BLOB_NAME):
        storage.read_text(BLOB_NAME)


def test_azure_blob_data_storage_reads_text_through_the_container_client() -> None:
    container_client = FakeContainerClient({BLOB_NAME: "# Filing"})
    storage = AzureBlobDataStorage(container_client)

    content = storage.read_text(BLOB_NAME)

    assert content == "# Filing"
    assert container_client.downloads == [(BLOB_NAME, "UTF-8")]


def test_azure_blob_data_storage_read_text_raises_file_not_found_for_a_missing_blob() -> None:
    storage = AzureBlobDataStorage(FakeContainerClient())

    with pytest.raises(FileNotFoundError, match=BLOB_NAME):
        storage.read_text(BLOB_NAME)


def test_build_data_storage_returns_local_when_environment_is_local(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "local")

    storage = build_data_storage(tmp_path)

    assert isinstance(storage, LocalDataStorage)
    assert storage.data_dir == tmp_path


def test_build_data_storage_defaults_to_the_repository_data_directory(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "local")

    storage = build_data_storage()

    assert isinstance(storage, LocalDataStorage)
    assert storage.data_dir == default_data_dir()


def test_build_data_storage_returns_azure_when_environment_is_test(monkeypatch, tmp_path: Path) -> None:
    import azure.identity
    import azure.storage.blob

    recorded: dict[str, object] = {}

    class FakeBlobServiceClient:
        def __init__(self, account_url: str, credential: object) -> None:
            recorded["account_url"] = account_url
            recorded["credential"] = credential

        def get_container_client(self, container: str) -> FakeContainerClient:
            recorded["container"] = container
            return FakeContainerClient()

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "stfdatest")
    monkeypatch.setenv("FILINGS_CONTAINER", "filings")
    monkeypatch.setattr(azure.storage.blob, "BlobServiceClient", FakeBlobServiceClient)
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", lambda: "credential")

    storage = build_data_storage(tmp_path)

    assert isinstance(storage, AzureBlobDataStorage)
    assert recorded["account_url"] == "https://stfdatest.blob.core.windows.net"
    assert recorded["credential"] == "credential"
    assert recorded["container"] == "filings"


def test_build_data_storage_requires_storage_account_name(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("STORAGE_ACCOUNT_NAME", raising=False)

    with pytest.raises(RuntimeError, match="STORAGE_ACCOUNT_NAME"):
        build_data_storage(tmp_path)
