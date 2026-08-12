# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import logging
import re
from dataclasses import dataclass
from typing import ClassVar

from usd_profiles_nvidia.model import (
    Example,
    ExampleResult,
    ExampleSnippet,
    ExampleSnippetLanguage,
)

from ._parser import Section

logger = logging.getLogger(__name__)


@dataclass
class ExamplesParser:
    VALID_REGEX: ClassVar[re.Pattern] = re.compile(r"^(?:Valid|Success|Recommended|Efficient):\s*(.*)", re.IGNORECASE)
    FAILURE_REGEX: ClassVar[re.Pattern] = re.compile(
        r"^(?:Failure|Invalid|Not Recommended|Inefficient):\s*(.*)", re.IGNORECASE
    )
    section: Section

    def _parse_result(self, result: str) -> ExampleResult:
        if self.VALID_REGEX.match(result):
            return ExampleResult.SUCCESS
        elif self.FAILURE_REGEX.match(result):
            return ExampleResult.FAILURE
        else:
            return ExampleResult.SUCCESS

    def _parse_name(self, name: str) -> str:
        if match := self.VALID_REGEX.match(name):
            return match.group(1).strip()
        elif match := self.FAILURE_REGEX.match(name):
            return match.group(1).strip()
        else:
            return name.strip()

    def _parse_snippet(self, subsection: Section) -> ExampleSnippet | None:
        for fence in subsection.fences:
            if fence.is_directive():
                continue
            match fence.info.lower():
                case "python" | "py":
                    language = ExampleSnippetLanguage.PYTHON
                case "usd" | "usda":
                    language = ExampleSnippetLanguage.USD
                case _:
                    continue
            return ExampleSnippet(language=language, content=fence.content.strip())
        return None

    def _parse_example(self, subsection: Section) -> Example | None:
        """ """
        result: ExampleResult | None = self._parse_result(subsection.title)
        name: str | None = self._parse_name(subsection.title)
        snippet: ExampleSnippet | None = self._parse_snippet(subsection)

        if snippet is None:
            return None
        if name is None:
            return None
        if result is None:
            return None
        return Example(
            snippet=snippet,
            display_name=name,
            result=result,
        )

    def parse(self) -> list[Example]:
        """ """
        examples: list[Example] = []
        for subsection in self.section.sections:
            example: Example | None = self._parse_example(subsection)
            if example is None:
                logger.warning(f'Skipping example with title "{subsection.title}"')
                continue
            examples.append(example)
        return examples
