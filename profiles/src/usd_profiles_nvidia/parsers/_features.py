# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from usd_profiles_nvidia.api import Feature
from usd_profiles_nvidia.json import JsonFeaturesParser
from usd_profiles_nvidia.markdown import MdFeaturesParser
from usd_profiles_nvidia.toml import TomlFeaturesParser

_FEATURE_PARSERS = {
    ".md": MdFeaturesParser,
    ".json": JsonFeaturesParser,
    ".toml": TomlFeaturesParser,
}


@dataclass
class FeaturesParser:
    """
    Format-agnostic parser for feature descriptors.

    Args:
        root_dir: Sphinx srcdir. Inferred from path when None.
        path: The path to a feature file or directory.
    """

    SUPPORTED_SUFFIXES: ClassVar[frozenset[str]] = frozenset(_FEATURE_PARSERS)

    root_dir: str | None
    path: str

    def parse(self) -> list[Feature]:
        """
        Parse all features from the configured file or directory.
        """
        path = Path(self.path)
        if path.is_file():
            return self._parse_file(path, self.root_dir or str(path.parent))
        if not path.is_dir():
            raise FileNotFoundError(f"Feature path does not exist: {path}")

        features: list[Feature] = []
        root_dir = self.root_dir or str(path)
        descriptor_paths = sorted(
            (
                descriptor_path
                for descriptor_path in path.rglob("*")
                if descriptor_path.is_file() and descriptor_path.suffix.lower() in self.SUPPORTED_SUFFIXES
            ),
            key=lambda descriptor_path: descriptor_path.relative_to(path).as_posix(),
        )
        for descriptor_path in descriptor_paths:
            features.extend(self._parse_file(descriptor_path, root_dir))
        return features

    @staticmethod
    def _parse_file(path: Path, root_dir: str) -> list[Feature]:
        try:
            parser_type = _FEATURE_PARSERS[path.suffix.lower()]
        except KeyError as error:
            raise ValueError(f"Unsupported feature descriptor format: {path}") from error
        return parser_type(root_dir=root_dir, path=str(path)).parse()
