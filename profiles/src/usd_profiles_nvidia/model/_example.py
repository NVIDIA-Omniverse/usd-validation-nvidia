# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import hashlib
from dataclasses import dataclass

from usd_profiles_nvidia.api import ExampleResult, ExampleSnippetLanguage

from ._naming import Naming


@dataclass(frozen=True, slots=True)
class ExampleSnippet:
    """A snippet of code in a specific language."""

    language: ExampleSnippetLanguage
    content: str

    @property
    def filename(self) -> str:
        digest = hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:12]
        return f"{digest}.{self.language.value}"


@dataclass(frozen=True, slots=True)
class Example:
    """An example of a requirement."""

    snippet: ExampleSnippet
    display_name: str
    result: ExampleResult

    @property
    def enum_name(self) -> str:
        suffix: str = "_OK" if self.result is ExampleResult.SUCCESS else "_NOK"
        return Naming.enum_name(self.display_name) + suffix
