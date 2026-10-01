import re

LOCAL_ENVIRONMENT = "local"

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies#S&P_500_component_stocks"
SP500_PARQUET_NAME = "s&p500.parquet"
SEC_IDENTITY = "MyName my.email@domain.com"

EMBEDDING_DIMENSIONS = 384
EMBEDDING_INDEX_NAME = "ix_document_chunks_embedding_hnsw"

EMBEDDING_BATCH_SIZE = 16
EMBEDDING_THREADS = 1

DEFAULT_MAX_TOKENS = 1000
DEFAULT_OVERLAP_TOKENS = 200
CHARS_PER_TOKEN = 4
HEADING_SEPARATOR = " > "

TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
TABLE_DIVIDER_PATTERN = re.compile(r"^\s*\|[\s:|-]*-[\s:|-]*\|\s*$")

HEADERS_TO_SPLIT_ON: list[tuple[str, str]] = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
    ("#####", "h5"),
    ("######", "h6"),
]
HEADER_KEYS: tuple[str, ...] = tuple(key for _, key in HEADERS_TO_SPLIT_ON)

SQL_ROW_LIMIT = 200
SQL_STATEMENT_TIMEOUT_MS = 5000
SQL_WRITE_KEYWORDS: tuple[str, ...] = (
    "insert",
    "update",
    "delete",
    "merge",
    "upsert",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "copy",
    "call",
    "do",
    "execute",
    "prepare",
    "vacuum",
    "analyze",
    "reindex",
    "cluster",
    "refresh",
    "lock",
    "comment",
    "set",
    "reset",
    "into",
    "set_config",
)

CREATED_STATUS = "created"
REPLACED_STATUS = "replaced"
SKIPPED_STATUS = "skipped"

CHUNK_FIELDS: tuple[str, ...] = (
    "document_id",
    "chunk_index",
    "content",
    "is_table",
    "heading_path",
    "token_count",
    "embedding_model",
    "embedding",
)

METRIC_FIELDS: tuple[str, ...] = (
    "revenue",
    "operating_income",
    "net_income",
    "total_assets",
    "total_liabilities",
    "stockholders_equity",
    "current_assets",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "shares_outstanding",
    "shares_outstanding_diluted",
    "current_ratio",
    "debt_to_assets_ratio",
)

EDGAR_METRIC_KEYS: dict[str, str] = {
    "revenue": "revenue",
    "operating_income": "operating_income",
    "net_income": "net_income",
    "total_assets": "total_assets",
    "total_liabilities": "total_liabilities",
    "stockholders_equity": "stockholders_equity",
    "current_assets": "current_assets",
    "operating_cash_flow": "operating_cash_flow",
    "capital_expenditures": "capital_expenditures",
    "free_cash_flow": "free_cash_flow",
    "shares_outstanding": "shares_outstanding_basic",
    "shares_outstanding_diluted": "shares_outstanding_diluted",
    "current_ratio": "current_ratio",
    "debt_to_assets_ratio": "debt_to_assets",
}
