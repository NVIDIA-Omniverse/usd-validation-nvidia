# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import os
from dataclasses import dataclass, replace

from usd_profiles_nvidia.api import Feature
from usd_profiles_nvidia.descriptors._features import FeatureDescriptorDecoder, feature_descriptor_errors
from usd_profiles_nvidia.model import Metadata


@dataclass
class JsonFeaturesParser:
    """
    JSON parser for feature descriptors.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to a feature file or directory.
    """

    root_dir: str
    path: str

    def parse(self) -> list[Feature]:
        """
        Parse all JSON feature descriptors from the configured path.
        """
        if os.path.isfile(self.path):
            filepaths = [self.path] if self.path.lower().endswith(".json") else []
        else:
            filepaths = [
                os.path.join(self.path, filename)
                for filename in sorted(os.listdir(self.path))
                if filename.lower().endswith(".json")
            ]

        decoder = FeatureDescriptorDecoder()
        features: list[Feature] = []
        for filepath in filepaths:
            with feature_descriptor_errors(filepath):
                with open(filepath, encoding="utf-8") as descriptor_file:
                    feature = decoder.decode(json.load(descriptor_file))
            normalized_path = feature.path or Metadata(path=os.path.relpath(filepath, self.root_dir)).path
            features.append(replace(feature, path=normalized_path))
        return features
