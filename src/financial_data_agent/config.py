import os

LOCAL_ENVIRONMENT = "local"


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
