"""The fetch-dependency data model — shared between config parsing and fetching.

Mirrors :mod:`agpack.patch`: :class:`DependencySource` is a domain type consumed both by parsing
(:mod:`agpack.config`) and by the fetch/deploy leaf modules (:mod:`agpack.fetcher`, :mod:`agpack.deployer`). Keeping
it in its own leaf module means neither parsing nor fetching has to import the other.
"""

from __future__ import annotations

from dataclasses import dataclass


def dependency_identity(url: str, path: str | None) -> str:
    """A unique key for a copy-kind dependency: ``url`` alone, or ``url::path`` when a subpath is set.

    Both :attr:`DependencySource.identity` and the lockfile's ``InstalledEntry.identity`` route through this one
    formula so copy-kind lockfile matching can't silently drift apart between the two modules.
    """
    return f"{url}::{path}" if path else url


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
    dest: str | None = None
    """If set, override the deployed item name (the leaf under a target's resource ``path``). E.g. ``dest: humanizer``
    on a skill deploys to ``<resource path>/humanizer/`` instead of using the name derived from ``url``/``path``. Only
    valid when the dependency resolves to a single item; expanding sources reject it."""

    @property
    def url(self) -> str:
        """The primary (first) URL."""
        return self.urls[0]

    @property
    def name(self) -> str:
        """Derive the resource name (last path segment, or url basename)."""
        if self.path:
            return self.path.rstrip("/").rsplit("/", 1)[-1]
        cleaned = self.url.rstrip("/").removesuffix(".git")
        return cleaned.rsplit("/", 1)[-1]

    @property
    def identity(self) -> str:
        """A unique key for this dependency (used for lockfile matching)."""
        return dependency_identity(self.url, self.path)
