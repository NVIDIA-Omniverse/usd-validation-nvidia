# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from collections.abc import Iterator
from math import sqrt

from usd_profiles_nvidia.api import Requirement
from usd_profiles_nvidia.model import Example


class ExampleStore:

    def __init__(self, requirements: list[Requirement]) -> None:
        self.examples: dict[str, Example] = {}

        for requirement in requirements:
            for example in requirement.examples:
                if example.enum_name in self.examples:
                    if self.examples[example.enum_name] == example:
                        continue
                    raise ValueError(f"Example with name {example.enum_name} already exists")
                self.examples[example.enum_name] = example

    def __len__(self) -> int:
        return len(self.examples)

    def __iter__(self) -> Iterator[Example]:
        return iter(self.examples.values())

    def partition(self) -> Iterator[tuple[str, Example]]:
        partition_size: int = max(1, int(sqrt(len(self.examples))))
        examples: list[Example] = list(self.examples.values())
        for partition_index, start_index in enumerate(range(0, len(examples), partition_size)):
            for example in examples[start_index : start_index + partition_size]:
                yield (f"{partition_index:02x}", example)
