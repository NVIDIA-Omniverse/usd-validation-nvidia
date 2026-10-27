# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from collections.abc import Iterator

from usd_profiles_nvidia.api import Example, ExampleResult, Requirement


class ExampleStore:

    def __init__(self, requirements: list[Requirement]) -> None:
        self.examples: dict[tuple[str, ExampleResult], Example] = {}

        for requirement in requirements:
            for example in requirement.examples:
                key = (example.display_name, example.result)
                if key in self.examples:
                    if self.examples[key] == example:
                        continue
                    raise ValueError(f"Example with name {example.display_name} already exists")
                self.examples[key] = example

    def __len__(self) -> int:
        return len(self.examples)

    def __iter__(self) -> Iterator[Example]:
        return iter(self.examples.values())
