# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_profiles_nvidia.api import Feature


class TestFeature(unittest.TestCase):

    def test_feature_fields(self):
        feature = Feature(
            id="semantic_labels",
            version="1.0.0",
            path="docs/features/semantic_labels",
            requirements=[],
        )

        self.assertEqual(feature.id, "semantic_labels")
        self.assertEqual(feature.version, "1.0.0")
        self.assertEqual(feature.path, "docs/features/semantic_labels")
        self.assertEqual(feature.requirements, [])
        self.assertEqual(feature.dependencies, [])
        self.assertEqual(feature.custom_data, {})
