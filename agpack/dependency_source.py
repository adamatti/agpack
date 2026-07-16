"""The fetch-dependency data model — shared between config parsing and fetching.

Mirrors :mod:`agpack.patch`: :class:`DependencySource` is a domain type consumed both by parsing
(:mod:`agpack.config`) and by the fetch/deploy leaf modules (:mod:`agpack.fetcher`, :mod:`agpack.deployer`). Keeping
it in its own leaf module means neither parsing nor fetching has to import the other.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DependencySource:
    """A parsed skill, command, or agent dependency (copy-kind input).

    The ``urls`` list contains one or more git clone URLs. The first entry is the canonical (primary) URL used for
    identity and display. Remaining entries are fallback URLs tried in order when earlier ones fail.
    """

    urls: list[str]
    path: str | None = None
    ref: str | None = None
    targets: tuple[str, ...] | None = None
    """If set, deploy only to targets whose name is in this list. ``None`` means every target that declares this
    resource type (pre-existing behavior)."""

    @property
    def url(self) -> str:
        """The primary (first) URL."""
        return self.urls[0]

    @property
    def name(self) -> str:
        """Derive the resource name (last path segment, or url basename)."""
        if self.path:
            return self.path.rstrip("/").rsplit("/", 1)[-1]
        cleaned = self.url.rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        return cleaned.rsplit("/", 1)[-1]

    @property
    def identity(self) -> str:
        """A unique key for this dependency (used for lockfile matching)."""
        key = self.url
        if self.path:
            key = f"{key}::{self.path}"
        return key
