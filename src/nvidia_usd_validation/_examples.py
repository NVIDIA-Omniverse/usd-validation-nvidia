# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from enum import Enum
from typing import Protocol, runtime_checkable

__all__ = [
    "Example",
    "ExampleResult",
    "ExampleSnippet",
    "ExampleSnippetLanguage",
]


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


@runtime_checkable
class ExampleSnippet(Protocol):
    """
    Args:
        language: The language of the example snippet.
        content: The content of the example snippet.
    """

    language: ExampleSnippetLanguage
    content: str


@runtime_checkable
class Example(Protocol):
    """
    Args:
        snippet: The snippet of code in a specific language.
        display_name: The name of the example.
        result: The result of the example.
    """

    snippet: ExampleSnippet
    display_name: str
    result: ExampleResult
