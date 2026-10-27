# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field
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
        inline_content: Inline snippet content used while authoring specifications.
    """

    language: ExampleSnippetLanguage
    path: str | None = None
    inline_content: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.path is None and self.inline_content is None:
            raise ValueError("ExampleSnippet requires path or inline_content")

    @cached_property
    def content(self) -> str:
        if self.inline_content is not None:
            return self.inline_content
        if not __package__:
            raise ValueError("__package__ not found")
        package_name: str = __package__.rsplit(".", 1)[0]
        resource_files = files(package_name) / self.path
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
