# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_profiles_nvidia.api import Feature, RequirementRef
from usd_profiles_nvidia.store import FeatureStore


class TestFeatureStore(unittest.TestCase):
    def test_resolve_requirements_deduplicates_by_code(self):
        feature = Feature(
            id="feature-id",
            version="1.0.0",
            path="features/feature-id",
            requirements=[
                RequirementRef("A", "1.0.0"),
                RequirementRef("B", "1.0.0"),
                RequirementRef("A", "1.1.0"),
            ],
        )
        store = FeatureStore([feature])

        resolved = store.resolve_requirements(feature)
        self.assertEqual(
            resolved,
            [
                RequirementRef("A", "1.1.0"),
                RequirementRef("B", "1.0.0"),
            ],
        )

    def test_resolve_requirements_returns_self_requirements(self):
        feature = Feature(
            id="feature-id",
            version="1.0.0",
            path="features/feature-id",
            requirements=[RequirementRef("A", "1.0.0")],
        )
        store = FeatureStore([feature])

        resolved = store.resolve_requirements(feature)
        self.assertEqual(resolved, feature.requirements)
