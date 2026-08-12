# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
from dataclasses import dataclass, replace

from usd_profiles_nvidia.api import Feature
from usd_profiles_nvidia.descriptors._features import FeatureDescriptorDecoder, feature_descriptor_errors
from usd_profiles_nvidia.model import Metadata

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclass
class TomlFeaturesParser:
    """
    TOML parser for feature descriptors.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to a feature file or directory.
    """

    root_dir: str
    path: str

    def parse(self) -> list[Feature]:
        """Parse all TOML feature descriptors from the configured path."""
        if os.path.isfile(self.path):
            filepaths = [self.path] if self.path.lower().endswith(".toml") else []
        else:
            filepaths = [
                os.path.join(self.path, filename)
                for filename in sorted(os.listdir(self.path))
                if filename.lower().endswith(".toml")
            ]

        decoder = FeatureDescriptorDecoder()
        features: list[Feature] = []
        for filepath in filepaths:
            with feature_descriptor_errors(filepath):
                with open(filepath, "rb") as descriptor_file:
                    feature = decoder.decode(tomllib.load(descriptor_file))
            normalized_path = feature.path or Metadata(path=os.path.relpath(filepath, self.root_dir)).path
            features.append(replace(feature, path=normalized_path))
        return features
