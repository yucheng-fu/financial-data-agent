import os

from financial_data_agent.constants import LOCAL_ENVIRONMENT


def get_environment() -> str:
    """Return the deployment environment name.

    Returns:
        The normalized environment name, defaulting to "local".
    """
    return os.getenv("ENVIRONMENT", LOCAL_ENVIRONMENT).strip().lower()


def is_local() -> bool:
    """Check whether the application runs in the local environment.

    Returns:
        True when the environment is local.
    """
    return get_environment() == LOCAL_ENVIRONMENT


def require_env(name: str) -> str:
    """Read a required environment variable.

    Args:
        name: Name of the environment variable.

    Returns:
        The environment variable value.

    Raises:
        RuntimeError: If the variable is unset or empty.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} environment variable is not set")
    return value


def get_embedding_cache_dir() -> str | None:
    """Return the directory holding downloaded embedding models.

    Returns:
        The configured cache directory, or None to use the backend's default.
    """
    return os.getenv("EMBEDDING_CACHE_DIR", "").strip() or None


def get_embedding_model() -> str:
    """Return the configured embedding model name.

    Returns:
        The embedding model name.

    Raises:
        RuntimeError: If `EMBEDDING_MODEL` is not set.
    """
    return require_env("EMBEDDING_MODEL")
