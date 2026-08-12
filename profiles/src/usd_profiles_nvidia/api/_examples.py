# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from importlib.resources import files


class ExampleResult(str, Enum):
    """
    Args:
        SUCCESS: The example succeeded.
        FAILURE: The example failed.
    """

    SUCCESS = "success"
    FAILURE = "failure"


class ExampleSnippetLanguage(str, Enum):
    """
    Args:
        PYTHON: The example snippet is in Python.
        USD: The example snippet is in USD.
    """

    PYTHON = "python"
    USD = "usd"


@dataclass(frozen=True)
class ExampleSnippet:
    """
    Args:
        language: The language of the example snippet.
        path: The generated resource path for the example snippet.
    """

    language: ExampleSnippetLanguage
    path: str

    @cached_property
    def content(self) -> str:
        if not __package__:
            raise ValueError("__package__ not found")
        package_name: str = __package__.rsplit(".", 1)[0]
        resource_files = files(package_name) / "resources" / "examples" / self.path
        return resource_files.read_text(encoding="utf-8")


@dataclass(frozen=True)
class Example:
    """
    Args:
        snippet: The snippet of code in a specific language.
        display_name: The display name of the example.
        result: The result of the example.
    """

    snippet: ExampleSnippet
    display_name: str
    result: ExampleResult
