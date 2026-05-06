# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from unittest.mock import Mock

from usd_validation_nvidia import (
    Feature,
    FeatureRegistry,
    add_registry_feature_callback,
    register_feature,
    register_features,
    unregister_feature,
    unregister_features,
)


class FeaturesRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = FeatureRegistry()
        self.mock_feature = Mock(spec=Feature)
        self.mock_feature.id = "test_feature"
        self.mock_feature.version = "1.0.0"
        self.mock_feature.path = "/path/test_feature"
        self.mock_feature.requirements = []

    def tearDown(self):
        try:
            unregister_feature(self.mock_feature)
        except ValueError:
            pass

    def test_add(self):
        self.registry.add(self.mock_feature)

        self.assertIn(self.mock_feature, self.registry)

    def test_find(self):
        self.registry.add(self.mock_feature)

        self.assertEqual(self.registry.find("test_feature"), self.mock_feature)

    def test_find_nonexistent_feature(self):
        self.assertIsNone(self.registry.find("nonexistent"))

    def test_register_feature_ok(self):
        register_feature(self.mock_feature)

        try:
            self.assertIn(self.mock_feature, self.registry)
        finally:
            unregister_feature(self.mock_feature)

    def test_unregister_feature_ok(self):
        register_feature(self.mock_feature)
        unregister_feature(self.mock_feature)

        self.assertNotIn(self.mock_feature, self.registry)

    def test_register_features(self):
        register_features([self.mock_feature])
        try:
            self.assertIn(self.mock_feature, self.registry)
        finally:
            unregister_features([self.mock_feature])

    def test_unregister_features(self):
        register_features([self.mock_feature])
        unregister_features([self.mock_feature])
        self.assertNotIn(self.mock_feature, self.registry)

    def test_add_callback_ok(self):
        callback = unittest.mock.Mock()
        _subscription = add_registry_feature_callback(callback)
        register_feature(self.mock_feature)
        try:
            callback.assert_called_once()
        finally:
            unregister_feature(self.mock_feature)
