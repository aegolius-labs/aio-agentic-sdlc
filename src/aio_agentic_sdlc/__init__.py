"""aio-agentic-sdlc: a framework where the backlog is the diff of two DAGs."""

from importlib import metadata


def _distribution_version() -> str:
    """The installed distribution version, or a marker when running from source."""

    try:
        return metadata.version("aio-agentic-sdlc")
    except metadata.PackageNotFoundError:
        return "0.0.0+unknown"


__version__ = _distribution_version()
