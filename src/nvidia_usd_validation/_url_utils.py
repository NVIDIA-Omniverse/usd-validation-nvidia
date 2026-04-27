# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["make_relative_url_if_possible", "normalize_url"]

import os
from urllib.parse import unquote, urlparse


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
