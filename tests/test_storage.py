from pathlib import Path

import pytest
import requests

from financial_data_agent.ingestion import storage as storage_module
from financial_data_agent.ingestion.storage import (
    AzureBlobDataStorage,
    LocalDataStorage,
    SupabaseDataStorage,
    build_data_storage,
    default_data_dir,
)

BLOB_NAME = "ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2/AAPL_2026_Q2.md"
SUPABASE_URL = "https://abc.supabase.co"
OBJECT_URL = f"{SUPABASE_URL}/storage/v1/object/filings/ticker%3DAAPL/year%3D2026/quarter%3DQ2/AAPL_2026_Q2/" + (
    "AAPL_2026_Q2.md"
)


class FakeResponse:
    """Stand in for a requests response from Supabase Storage."""

    def __init__(self, status_code: int, content: bytes = b"", body: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.content = content
        self.body = body

    def json(self) -> dict[str, str]:
        if self.body is None:
            raise ValueError("no JSON body")
        return self.body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


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


def test_supabase_data_storage_upserts_object_and_returns_blob_name(monkeypatch) -> None:
    calls: list[tuple[str, bytes, dict[str, str]]] = []

    def fake_post(url: str, data: bytes, headers: dict[str, str], timeout: int) -> FakeResponse:
        calls.append((url, data, headers))
        return FakeResponse(200)

    monkeypatch.setattr(storage_module.requests, "post", fake_post)
    storage = SupabaseDataStorage(SUPABASE_URL, "sb_secret_key", "filings")

    location = storage.save_text(BLOB_NAME, "# Filing")

    assert location == BLOB_NAME
    assert calls == [
        (
            OBJECT_URL,
            b"# Filing",
            {"apikey": "sb_secret_key", "Authorization": "Bearer sb_secret_key", "x-upsert": "true"},
        )
    ]


def test_supabase_data_storage_escapes_ampersand_in_object_name(monkeypatch) -> None:
    urls: list[str] = []

    def fake_post(url: str, data: bytes, headers: dict[str, str], timeout: int) -> FakeResponse:
        urls.append(url)
        return FakeResponse(200)

    monkeypatch.setattr(storage_module.requests, "post", fake_post)

    SupabaseDataStorage(SUPABASE_URL, "key", "filings").save_bytes("s&p500.parquet", b"PAR1")

    assert urls == [f"{SUPABASE_URL}/storage/v1/object/filings/s%26p500.parquet"]


def test_supabase_data_storage_raises_when_upload_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(storage_module.requests, "post", lambda *args, **kwargs: FakeResponse(403))

    with pytest.raises(requests.HTTPError):
        SupabaseDataStorage(SUPABASE_URL, "key", "filings").save_text(BLOB_NAME, "# Filing")


def test_supabase_data_storage_reads_text(monkeypatch) -> None:
    urls: list[str] = []

    def fake_get(url: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        urls.append(url)
        return FakeResponse(200, content="# Filing é".encode())

    monkeypatch.setattr(storage_module.requests, "get", fake_get)

    content = SupabaseDataStorage(SUPABASE_URL, "key", "filings").read_text(BLOB_NAME)

    assert content == "# Filing é"
    assert urls == [OBJECT_URL]


@pytest.mark.parametrize(
    "response",
    [FakeResponse(404), FakeResponse(400, body={"statusCode": "404", "error": "not_found"})],
)
def test_supabase_data_storage_read_text_raises_file_not_found_for_a_missing_object(
    monkeypatch, response: FakeResponse
) -> None:
    monkeypatch.setattr(storage_module.requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(FileNotFoundError, match=BLOB_NAME):
        SupabaseDataStorage(SUPABASE_URL, "key", "filings").read_text(BLOB_NAME)


def test_supabase_data_storage_read_text_raises_http_error_for_other_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        storage_module.requests, "get", lambda *args, **kwargs: FakeResponse(400, body={"statusCode": "403"})
    )

    with pytest.raises(requests.HTTPError):
        SupabaseDataStorage(SUPABASE_URL, "key", "filings").read_text(BLOB_NAME)


def test_build_data_storage_returns_supabase_when_environment_is_test(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SUPABASE_URL", f"{SUPABASE_URL}/")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_key")
    monkeypatch.setenv("FILINGS_BUCKET", "filings")

    storage = build_data_storage(tmp_path)

    assert isinstance(storage, SupabaseDataStorage)
    assert storage.object_url == f"{SUPABASE_URL}/storage/v1/object/filings"


def test_build_data_storage_requires_supabase_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        build_data_storage(tmp_path)
