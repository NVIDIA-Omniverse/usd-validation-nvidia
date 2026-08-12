# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = [
    "LocalUriResolver",
    "UriResolver",
    "make_absolute_url_if_possible",
    "make_relative_url_if_possible",
    "normalize_url",
]

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import unquote, urlparse


@runtime_checkable
class UriResolver(Protocol):
    """Protocol for resolving URI operations.

    Implementations provide backend-specific URI operations used by
    :py:class:`ValidationEngine` for asset discovery and folder traversal.
    The standalone engine uses :py:class:`LocalUriResolver`; the Kit extension
    uses ``OmniUriResolver``.
    """

    def is_uri_found(self, uri: str) -> bool:
        """Return True if the asset at *uri* exists."""
        ...

    def is_uri_prefix(self, uri: str) -> bool:
        """Return True if *uri* is a container that may hold child assets."""
        ...

    def list_uris(self, uri: str) -> list[str]:
        """Return the direct children of the container at *uri*."""
        ...

    def parent_uri(self, uri: str) -> str:
        """Return the parent container of *uri*."""
        ...

    def join_uri(self, base_uri: str, child: str) -> str:
        """Return the URI formed by appending *child* to the container *base_uri*."""
        ...

    def basename(self, uri: str) -> str:
        """Return the last path component of *uri* (filename for a leaf, directory name for a container)."""
        ...

    def relative_uri(self, base_uri: str, child_uri: str) -> str:
        """Return *child_uri* as a path relative to the container *base_uri*."""
        ...


@dataclass(frozen=True)
class LocalUriResolver:
    """A :py:class:`UriResolver` backed by the local filesystem (``os.path``)."""

    def is_uri_found(self, uri: str) -> bool:
        return os.path.exists(uri)

    def is_uri_prefix(self, uri: str) -> bool:
        return os.path.isdir(uri)

    def list_uris(self, uri: str) -> list[str]:
        return [os.path.join(uri, entry) for entry in os.listdir(uri)]

    def parent_uri(self, uri: str) -> str:
        return os.path.dirname(uri)

    def join_uri(self, base_uri: str, child: str) -> str:
        return os.path.join(base_uri, child)

    def basename(self, uri: str) -> str:
        return os.path.basename(uri)

    def relative_uri(self, base_uri: str, child_uri: str) -> str:
        rel = os.path.relpath(child_uri, base_uri).replace("\\", "/")
        return rel if rel.startswith("..") else "./" + rel


def normalize_url(path_or_url: str) -> str:
    """
    Normalizes url to create uniform format of url, which can be used to compare
    with other normalized urls to check the equality between urls. It does the
    following normalization:
    1. It replaces backslashes into forward slashes.
    2. It capitalizes disk drive letter for windows paths.
    3. It simplifies parts of relative path.
    """

    url = urlparse(path_or_url)

    # Anonymous layer identifier
    if url.scheme == "anon":
        return path_or_url

    if url.scheme == "file":
        # If it has netloc like "file://netloc/c:/test.usd".
        if url.netloc:
            return path_or_url

        # Else converting it to local raw path
        url_path = url.path or ""

        if os.name == "nt":
            if len(url_path) >= 3 and url_path[0] == "/" and url_path[2] == ":":
                path_or_url = unquote(url_path[1:])
                # Ensure disk drive letter always capitalized.
                path_or_url = path_or_url[0].upper() + path_or_url[1:]
        else:
            path_or_url = unquote(url_path)
        path_or_url = os.path.normpath(path_or_url)
    elif len(url.scheme) == 1 and url.scheme.isalpha():
        # urlparse parses drive letter as scheme.
        path_or_url = unquote(path_or_url)
        path_or_url = path_or_url[0].upper() + path_or_url[1:]
        path_or_url = os.path.normpath(path_or_url)

    return path_or_url.replace("\\", "/")


def make_absolute_url_if_possible(path_or_url: str) -> str:
    """Return an absolute local path while preserving URIs and empty identifiers."""

    if not path_or_url:
        return path_or_url

    parsed_url = urlparse(path_or_url)
    if parsed_url.scheme and len(parsed_url.scheme) > 1:
        return path_or_url

    return os.path.abspath(path_or_url)


def make_relative_url_if_possible(base_url: str, path_or_url: str, base_url_is_directory=False) -> str:
    normalized_base_url = normalize_url(base_url)
    normalized_url = normalize_url(path_or_url)

    parsed_base_url = urlparse(normalized_base_url)
    parsed_url = urlparse(normalized_url)

    if parsed_base_url.scheme != parsed_url.scheme or parsed_base_url.netloc != parsed_url.netloc:
        return path_or_url

    # For url like "file:/c:/test.usd", parsed url will have path like "/c:/test.usd".
    # It needs pecial treatment so we don't compute relpath when they are on different drives.
    base_path: str = parsed_base_url.path
    path: str = parsed_url.path
    if os.name == "nt":
        base_path.removeprefix("/")
        path.removeprefix("/")

    try:
        # os.path.relpath accepts arg `start` as directory.
        if not base_url_is_directory:
            base_path = os.path.dirname(base_path)

        relative_path = os.path.relpath(path, base_path)
    except ValueError:
        # Failed to compute relative path, then we keep url untouched.
        relative_path = path_or_url

    return normalize_url(relative_path)
